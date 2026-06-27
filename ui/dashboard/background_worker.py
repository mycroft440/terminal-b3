"""
BackgroundScannerWorker - thread que coleta e avalia ativos em background.

Encapsula o loop que antes era uma closure de 200 linhas em main_page.py.
Mantem a mesma logica, mas com:
- Dependencias explicitas no __init__ (state, app_cache, locks, etc)
- Metodo run() executavel em threading.Thread
- Metodo _prefetch_other_configs() extraido para clareza
- Estado mutavel (bg_worker_running) via atributo da classe
"""
import time
import logging
import threading

from services.scanner import gerar_chunks_ativos


class BackgroundScannerWorker:
    """Thread worker que coleta e avalia ativos em background.

    Responsabilidades:
    1. Loop principal: baixa e avalia ativos para a config atual
    2. Persiste cache em disco periodicamente (a cada 6 chunks)
    3. Pre-fetch: aquece cache de outros mercados/timeframes
    4. Aguarda mudanca de config para recomecar loop

    Atributos:
        state: state global do app (UI + carteiras + ocultos)
        app_cache: dict com 'evaluated_assets' (cache em memoria por hash)
        app_cache_lock: threading.Lock para acessar app_cache
        state_manager: StateManager (para save_evaluated_cache)
        status_text: ft.Text para atualizar status na UI
        page: ft.Page (para pubsub.send_all)
        config_changed_event: threading.Event sinalizando mudanca de config
        bg_worker_running: list[bool] mutable container para controle de loop
        get_config_hash: callback que retorna hash atual da config
    """

    def __init__(
        self,
        state: dict,
        app_cache: dict,
        app_cache_lock: threading.Lock,
        state_manager,
        status_text,
        page,
        config_changed_event: threading.Event,
        bg_worker_running,
        get_config_hash,
    ):
        self.state = state
        self.app_cache = app_cache
        self.app_cache_lock = app_cache_lock
        self.state_manager = state_manager
        self.status_text = status_text
        self.page = page
        self.config_changed_event = config_changed_event
        self.bg_worker_running = bg_worker_running
        self.get_config_hash = get_config_hash

    def run(self):
        """Loop principal do worker. Roda em thread daemon.

        Loop:
        1. Verifica se bg_worker_running[0] e True
        2. Coleta e avalia ativos para config atual (gerar_chunks_ativos)
        3. Persiste cache em disco a cada 6 chunks
        4. Ao terminar naturalmente: faz pre-fetch de outras configs
        5. Aguarda config_changed_event ser setado para recomecar
        """
        while self.bg_worker_running[0]:
            current_hash = self.get_config_hash()
            exclude_tickers = set()
            with self.app_cache_lock:
                if current_hash not in self.app_cache["evaluated_assets"]:
                    self.app_cache["evaluated_assets"][current_hash] = []
                exclude_tickers = {
                    d["ativo"]["ticker"]
                    for d in self.app_cache["evaluated_assets"][current_hash]
                }

            wallet_tickers = self._get_wallet_tickers()

            # EARLY EXIT: so pular carregamento se for CARTEIRA e todos os
            # tickers da carteira ja estao no cache. Para MERCADO GERAL,
            # nunca pular — o generator usa exclude_tickers para so baixar
            # o que falta, entao e rapido se cache ja esta quente.
            if (
                wallet_tickers is not None
                and wallet_tickers
                and all(t in exclude_tickers for t in wallet_tickers)
            ):
                # Carteira: todos os tickers ja estao no cache — pular
                self.state["is_loading"] = False
                self.status_text.value = f"✓ {len(exclude_tickers)} ativos carregados"
                self._safe_update(self.status_text)
                self.page.pubsub.send_all({"type": "render_list"})

                # Faz prefetch apenas se nao foi interrompido
                if not self.config_changed_event.is_set() and self.bg_worker_running[0]:
                    self._prefetch_other_configs(current_hash)

                if not self.config_changed_event.is_set() and self.bg_worker_running[0]:
                    self.config_changed_event.wait()
                # BUG 14: clear() pode perder sinal setado entre wait() retornar
                # e clear(). Solução: usar wait(timeout=1) em loop em vez de
                # clear() — mas isso consome CPU. Alternativa: aceitar o risco
                # (probabilidade muito baixa) e manter clear().
                if self.bg_worker_running[0]:
                    self.config_changed_event.clear()
                continue

            # BUG 16: carteira vazia — wallet_tickers é lista vazia, não None.
            # Sem isso, worker entra em loop: acorda, não há tickers, termina,
            # espera, acorda de novo...
            if wallet_tickers is not None and not wallet_tickers:
                self.state["is_loading"] = False
                self.status_text.value = "Carteira vazia"
                self._safe_update(self.status_text)
                self.page.pubsub.send_all({"type": "render_list"})
                if not self.config_changed_event.is_set() and self.bg_worker_running[0]:
                    self.config_changed_event.wait()
                if self.bg_worker_running[0]:
                    self.config_changed_event.clear()
                continue

            self.state["is_loading"] = True

            try:
                # Status inicial
                if not exclude_tickers:
                    self.status_text.value = "Conectando ao mercado..."
                    self._safe_update(self.status_text)
                else:
                    self.status_text.value = (
                        f"Retomando leitura... ({len(exclude_tickers)})"
                    )
                    self._safe_update(self.status_text)

                # wallet_tickers ja foi calculado no early-exit check acima
                generator = gerar_chunks_ativos(
                    self.state["timeframe"],
                    self.state["market"],
                    "all",  # Busca todos os setores
                    self.state["mms_periodos"] if self.state["mms_active"] else [],
                    self.state["rsi_active"],
                    self.state["stoch_active"],
                    False,
                    exclude_tickers=exclude_tickers,
                    wallet_tickers=wallet_tickers,
                )

                finished_naturally = self._process_chunks(generator, current_hash)

                if finished_naturally:
                    self._finalize_loading(current_hash)
                    self._prefetch_other_configs(current_hash)

                    if (
                        not self.config_changed_event.is_set()
                        and self.bg_worker_running[0]
                    ):
                        with self.app_cache_lock:
                            total_loaded = len(
                                self.app_cache["evaluated_assets"][current_hash]
                            )
                        self.status_text.value = f"✓ {total_loaded} ativos carregados"
                        self._safe_update(self.status_text)
                        # Aguarda ate que a configuracao mude para nao consumir CPU
                        self.config_changed_event.wait()

                    if self.bg_worker_running[0]:
                        self.config_changed_event.clear()
                else:
                    # Foi interrompido para trocar de config ou fechar app
                    if self.bg_worker_running[0]:
                        self.config_changed_event.clear()

            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                self.status_text.value = f"✗ Erro: {str(e)}"
                logging.error(f"Erro no background scanner worker: {e}\n{tb}")
                self.state["is_loading"] = False
                self.page.pubsub.send_all({"type": "render_list"})
                time.sleep(5)  # Evita loop rapido de erros

    def _process_chunks(self, generator, current_hash: str) -> bool:
        """Processa chunks do generator, renderizando progressivamente.

        Returns:
            True se o generator terminou naturalmente, False se foi interrompido.
        """
        finished_naturally = True
        chunk_counter = 0

        for chunk in generator:
            if not self.bg_worker_running[0] or self.config_changed_event.is_set():
                finished_naturally = False
                break

            with self.app_cache_lock:
                self.app_cache["evaluated_assets"][current_hash].extend(chunk)
                total_so_far = len(self.app_cache["evaluated_assets"][current_hash])
            chunk_counter += 1

            self.status_text.value = f"Lendo ativos... ({total_so_far})"
            # Renderiza a cada 3 chunks
            if chunk_counter % 3 == 1:
                self.page.pubsub.send_all({"type": "render_list"})
            else:
                self._safe_update(self.status_text)

            # Persiste cache em disco a cada 6 chunks (~150 ativos)
            if chunk_counter % 6 == 0:
                self._persist_evaluated_cache()

        return finished_naturally

    def _finalize_loading(self, current_hash: str) -> None:
        """Finaliza carregamento: status final + persistencia + render."""
        with self.app_cache_lock:
            total_loaded = len(self.app_cache["evaluated_assets"][current_hash])
        # Snapshot final para persistencia em disco
        self._persist_evaluated_cache()
        self.status_text.value = f"✓ {total_loaded} ativos carregados"
        self.state["is_loading"] = False
        self.page.pubsub.send_all({"type": "render_list"})

    def _prefetch_other_configs(self, current_hash: str) -> None:
        """Aquece cache de outros mercados/timeframes para troca instantanea.

        Ordem de prefetch:
        - Mercado atual + outros timeframes (1d, 1s)
        - Outros mercados (acoes, fiis, bdrs) + timeframe atual
        """
        current_tf = self.state["timeframe"]
        current_market = self.state["market"]

        market_order = [current_market]
        for m in ["acoes", "fiis", "bdrs"]:
            if m not in market_order:
                market_order.append(m)

        tf_order = [current_tf]
        for tf in ["1d", "1s"]:
            if tf not in tf_order:
                tf_order.append(tf)

        for prefetch_market in market_order:
            for prefetch_tf in tf_order:
                # Ignora se for o mercado e tempo grafico que acabaram de ser carregados
                if prefetch_market == current_market and prefetch_tf == current_tf:
                    continue

                if (
                    self.config_changed_event.is_set()
                    or not self.bg_worker_running[0]
                ):
                    break

                self.status_text.value = (
                    f"Pré-carregando cache: {prefetch_market.upper()} "
                    f"({prefetch_tf})..."
                )
                self._safe_update(self.status_text)

                p = self.state["mms_periodos"][0] if self.state["mms_periodos"] else 0
                prefetch_hash = (
                    f"{prefetch_market}_{prefetch_tf}_"
                    f"{self.state['mms_active']}_{p}_"
                    f"{self.state['rsi_active']}_{self.state['stoch_active']}"
                )

                # BUG 18: acessar evaluated_assets sem lock pode causar race
                # condition com _do_render que le o mesmo dict
                with self.app_cache_lock:
                    if prefetch_hash not in self.app_cache["evaluated_assets"]:
                        self.app_cache["evaluated_assets"][prefetch_hash] = []
                    prefetch_exclude = {
                        d["ativo"]["ticker"]
                        for d in self.app_cache["evaluated_assets"][prefetch_hash]
                    }

                try:
                    # Prefetch NAO usa wallet_tickers — deve carregar TODOS
                    # ativos do mercado, nao so os da carteira atual.
                    # (wallet_tickers do prefetch seria None ja que sort='all'
                    # durante prefetch, mas garantimos explicitamente)
                    prefetch_gen = gerar_chunks_ativos(
                        prefetch_tf,
                        prefetch_market,
                        "all",
                        self.state["mms_periodos"] if self.state["mms_active"] else [],
                        self.state["rsi_active"],
                        self.state["stoch_active"],
                        False,
                        exclude_tickers=prefetch_exclude,
                        wallet_tickers=None,
                    )
                    for chunk in prefetch_gen:
                        if (
                            self.config_changed_event.is_set()
                            or not self.bg_worker_running[0]
                        ):
                            break
                        with self.app_cache_lock:
                            self.app_cache["evaluated_assets"][prefetch_hash].extend(
                                chunk
                            )
                except Exception as e:
                    import traceback

                    tb = traceback.format_exc()
                    logging.error(
                        f"Erro no prefetch ({prefetch_market} {prefetch_tf}): {e}\n{tb}"
                    )

            if self.config_changed_event.is_set() or not self.bg_worker_running[0]:
                break

    def _get_wallet_tickers(self):
        """Extrai lista de tickers da carteira ativa, se state['sort']
        comecar com 'cart_'."""
        is_wallet = str(self.state.get("sort", "")).startswith("cart_")
        if not is_wallet:
            return None

        cart_nome = self.state["sort"][5:] if len(self.state["sort"]) > 5 else ""
        if cart_nome in self.state.get("carteiras", {}):
            return list(self.state["carteiras"][cart_nome].keys())
        return None

    def _persist_evaluated_cache(self) -> None:
        """Salva snapshot do cache avaliado em disco."""
        with self.app_cache_lock:
            snapshot = {
                k: list(v) for k, v in self.app_cache["evaluated_assets"].items()
            }
        self.state_manager.save_evaluated_cache(snapshot)

    def _safe_update(self, ctrl) -> None:
        """Atualiza controle Flet ignorando excecoes (UI pode ter fechado)."""
        try:
            ctrl.update()
        except Exception:
            pass
