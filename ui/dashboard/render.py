"""
DashboardRenderer - renderiza lista de cards na UI.

Encapsula a funcao render_list que antes era uma closure de 275 linhas em
main_page.py. Mantem a mesma logica:
1. Filtra ativos por setor, confluencia, carteira/ocultos
2. Ordena por custom_sort_key (has_data, fav, alta, peso_mc, qtd, vol, mc)
3. Filtra por termo de busca
4. Calcula estatisticas de portfolio (se carteira ativa)
5. Reusa card_controls em cache (data_hash) para evitar re-render
6. Atualiza contadores (altas/baixas/total)
7. Mostra empty state ou loading state se lista vazia
"""
import math
import threading
import flet as ft

from ui.cards import create_card
import ui.flet_patches  # noqa: F401


class DashboardRenderer:
    """Renderiza lista de cards na UI com cache de controles.

    Thread-safe: usa _render_lock para evitar que multiplas chamadas
    concorrentes a render() (ex: worker thread + UI thread) causem
    travamento por page.update() simultaneo.

    Atributos:
        state: state global (sort, sector, search, carteiras, ocultos, ...)
        app_cache: dict com 'evaluated_assets' e 'card_controls'
        app_cache_lock: threading.Lock para acessar app_cache
        list_view: ft.ListView onde cards sao adicionados
        page: ft.Page (para page.update())
        get_config_hash: callback que retorna hash da config atual
        portfolio_stats_container: ft.Container para stats de carteira
        txt_ativos_count, txt_alta_count, txt_baixa_count: ft.Text contadores
        open_add_carteira_dialog, open_remove_carteira_dialog: callbacks
        open_notes_dialog: callback para abrir bloco de notas
        save_ocultos: callback para persistir ocultos
    """

    def __init__(
        self,
        state: dict,
        app_cache: dict,
        app_cache_lock,
        list_view: ft.ListView,
        page: ft.Page,
        get_config_hash,
        portfolio_stats_container: ft.Container,
        txt_ativos_count: ft.Text,
        txt_alta_count: ft.Text,
        txt_baixa_count: ft.Text,
        open_add_carteira_dialog,
        open_remove_carteira_dialog,
        open_notes_dialog,
        save_ocultos,
        on_voltar=None,
    ):
        self.state = state
        self.app_cache = app_cache
        self.app_cache_lock = app_cache_lock
        self.list_view = list_view
        self.page = page
        self.get_config_hash = get_config_hash
        self.portfolio_stats_container = portfolio_stats_container
        self.txt_ativos_count = txt_ativos_count
        self.txt_alta_count = txt_alta_count
        self.txt_baixa_count = txt_baixa_count
        self.open_add_carteira_dialog = open_add_carteira_dialog
        self.open_remove_carteira_dialog = open_remove_carteira_dialog
        self.open_notes_dialog = open_notes_dialog
        self.save_ocultos = save_ocultos
        self.on_voltar = on_voltar
        # Lock de renderizacao: evita que multiplas chamadas concorrentes
        # a render() causem travamento por page.update() simultaneo.
        # Lock simples (nao reentrante) - se a mesma thread tentar reentrar,
        # e um bug que deve ser corrigido, nao silenciado.
        self._render_lock = threading.Lock()

    def render(self):
        """Renderiza lista de cards. Chamado apos mudancas de state ou cache.

        Thread-safe: usa _render_lock para evitar que multiplas chamadas
        concorrentes (ex: worker pubsub + UI click) causem travamento.
        Se o lock ja estiver ocupado, a chamada e ignorada (skip) — a
        renderizacao em andamento ja vai refletir o estado mais recente.
        """
        if not self._render_lock.acquire(blocking=False):
            # Outra renderizacao em andamento — skip (a atual ja refletira
            # o estado mais recente quando terminar)
            return
        try:
            self._do_render()
        finally:
            self._render_lock.release()

    def _do_render(self):
        """Executa a renderizacao real (sem protecao de lock)."""
        current_hash = self.get_config_hash()
        with self.app_cache_lock:
            res = list(self.app_cache["evaluated_assets"].get(current_hash, []))

        res = self._filter_by_sector(res)
        res = self._filter_by_confluence(res)
        res = self._filter_by_sort(res)
        res.sort(key=self._custom_sort_key, reverse=True)
        res = self._filter_by_search(res)

        self._update_portfolio_stats(res)
        new_controls = self._build_card_controls(res)
        self._update_counters(res)

        # Insere botao Voltar no topo quando estiver na view de ocultos
        if self.state.get("sort") == "ocultos" and self.on_voltar:
            new_controls.insert(0, self._build_voltar_row_ocultos())

        self.list_view.controls = new_controls
        self._show_empty_or_loading_state(res)

        # NAO usar page.update() — envia arvore inteira (900+ cards = lento).
        # Usar list_view.update() para so atualizar a lista, e ctrl.update()
        # para contadores e stats individualmente.
        try:
            self.list_view.update()
        except Exception:
            pass
        # Atualiza contadores e portfolio individualmente (rapido)
        for ctrl in (self.txt_ativos_count, self.txt_alta_count,
                     self.txt_baixa_count, self.portfolio_stats_container):
            try:
                ctrl.update()
            except Exception:
                pass

    # ─── Botao Voltar (ocultos) ───────────────────────────────────────────────

    def _build_voltar_row_ocultos(self) -> ft.Container:
        """Botão Voltar estilizado no topo da área de conteúdo dos ocultos."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.TextButton(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ARROW_BACK_ROUNDED,
                                    size=18,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    "Voltar ao Painel",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE,
                                ),
                            ],
                            spacing=6,
                            tight=True,
                        ),
                        on_click=lambda e: self.on_voltar() if self.on_voltar else None,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_600,
                            padding=ft.Padding(16, 8, 16, 8),
                            shape=ft.RoundedRectangleBorder(radius=20),
                            side=ft.BorderSide(1, ft.Colors.BLUE_500),
                            overlay_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                        ),
                    ),
                    ft.Text(
                        "👁️ Ativos Ocultos",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_GREY_400,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(0, 4, 0, 8),
        )

    # ─── Filtros ────────────────────────────────────────────────────────────

    def _filter_by_sector(self, res: list) -> list:
        if self.state["sector"] != "all":
            return [d for d in res if d["ativo"].get("setor") == self.state["sector"]]
        return res

    def _filter_by_confluence(self, res: list) -> list:
        sem_filtro = (
            not self.state["mms_active"]
            and not self.state["rsi_active"]
            and not self.state["stoch_active"]
        )
        is_carteira = str(self.state.get("sort", "")).startswith("cart_")
        is_ocultos = self.state.get("sort") == "ocultos"

        # Ignora filtro de confluencia se pesquisando, em carteira ou ocultos
        if (
            not sem_filtro
            and not self.state["search"]
            and not is_carteira
            and not is_ocultos
        ):
            return [d for d in res if not d.get("semConfluencia")]
        return res

    def _filter_by_sort(self, res: list) -> list:
        if self.state["sort"] == "ocultos":
            return [
                d
                for d in res
                if (d["ativo"].get("codigo") or d["ativo"].get("ticker"))
                in self.state.get("ocultos", [])
            ]
        if str(self.state["sort"]).startswith("cart_"):
            cart_nome = self.state["sort"][5:]
            if cart_nome in self.state["carteiras"]:
                # BUG 15/20: carteiras armazenam tickers (ex: "PETR4.SA")
                # mas filtro verificava codigo (ex: "PETR4").
                # Agora verifica AMBOS ticker e codigo para cobrir ambos os formatos.
                carteira_keys = set(self.state["carteiras"][cart_nome].keys())
                return [
                    d
                    for d in res
                    if (d["ativo"].get("ticker") in carteira_keys
                        or (d["ativo"].get("codigo") or d["ativo"].get("ticker")) in carteira_keys)
                ]
            return []
        # Default: exclui ocultos
        return [
            d
            for d in res
            if (d["ativo"].get("codigo") or d["ativo"].get("ticker"))
            not in self.state.get("ocultos", [])
        ]

    def _filter_by_search(self, res: list) -> list:
        if not self.state["search"]:
            return res
        q = self.state["search"].lower()
        return [
            d
            for d in res
            if q in d["ativo"].get("nome", "").lower()
            or q in d["ativo"].get("ticker", "").lower()
            or q in d["ativo"].get("codigo", "").lower()
        ]

    # ─── Ordenacao ──────────────────────────────────────────────────────────

    def _custom_sort_key(self, d: dict) -> tuple:
        """Chave de ordenacao para sort(reverse=True).

        Ordem de prioridade (decrescente):
        1. has_data (1 = com dados, 0 = sem dados)
        2. is_fav (1 = em carteira, 0 = nao)
        3. is_alta (1 = alta, 0 = baixa)
        4. peso_mc (1=Blue Chip, 2=Mid, 3=Small, 4=Micro)
        5. qtd_candles (mais candles de confluencia primeiro)
        6. volume (liquidez)
        7. market_cap (fallback)
        """
        codigo = d["ativo"].get("codigo") or d["ativo"].get("ticker")
        is_fav = 1 if any(codigo in lst for lst in self.state["carteiras"].values()) else 0
        is_alta = 1 if d["isAlta"] else 0
        has_data = 0 if d.get("semDados") else 1

        mc = d.get("marketCap", 0) or 0
        vol = d["ativo"].get("volume") or d["ativo"].get("volume24h") or 0

        is_fii = d["ativo"].get("tipo") == "fiis"
        if is_fii:
            peso_mc = 3
        elif mc >= 10e9:
            peso_mc = 1  # Blue Chip
        elif mc >= 2e9:
            peso_mc = 2  # Mid Cap
        elif mc >= 500e6:
            peso_mc = 3  # Small Cap
        else:
            peso_mc = 4  # Micro Cap

        qtd = d.get("qtdCandles", 0) or 0
        return (has_data, is_fav, is_alta, peso_mc, qtd, vol, mc)

    # ─── Portfolio stats (carteira ativa) ───────────────────────────────────

    def _update_portfolio_stats(self, res: list) -> None:
        if not str(self.state.get("sort", "")).startswith("cart_"):
            self.portfolio_stats_container.visible = False
            return

        cart_nome = self.state["sort"].replace("cart_", "", 1)

        def safe_avg(key):
            valid = [
                d.get(key, 0)
                for d in res
                if d.get(key) is not None and not math.isnan(d.get(key, 0))
            ]
            return sum(valid) / len(valid) if valid else 0

        avg_1d = safe_avg("variacao")
        avg_7d = safe_avg("variacao_7d")
        avg_30d = safe_avg("variacao_30d")

        def fmt_var(val):
            return f"{'+' if val > 0 else ''}{val:.2f}%"

        def cor_var(val):
            if val > 0:
                return ft.Colors.GREEN_400
            if val < 0:
                return ft.Colors.RED_400
            return ft.Colors.BLUE_GREY_300

        self.portfolio_stats_container.content = ft.Row(
            [
                ft.Icon(ft.Icons.PIE_CHART_ROUNDED, size=20, color=ft.Colors.AMBER_500),
                ft.Text(
                    f"Variação Média ({cart_nome}):",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_GREY_300,
                ),
                ft.Text(
                    f"1D: {fmt_var(avg_1d)}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=cor_var(avg_1d),
                ),
                ft.Text(" • ", color=ft.Colors.BLUE_GREY_600),
                ft.Text(
                    f"7D: {fmt_var(avg_7d)}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=cor_var(avg_7d),
                ),
                ft.Text(" • ", color=ft.Colors.BLUE_GREY_600),
                ft.Text(
                    f"30D: {fmt_var(avg_30d)}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=cor_var(avg_30d),
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.portfolio_stats_container.visible = True

    # ─── Construcao de card controls (com cache) ────────────────────────────

    def _build_card_controls(self, res: list) -> list:
        new_controls = []
        # Snapshot de card_controls sob lock para evitar race condition (BUG 13)
        with self.app_cache_lock:
            card_controls = dict(self.app_cache["card_controls"])

        for d in res:
            ticker = d["ativo"]["ticker"]
            codigo = d["ativo"].get("codigo") or ticker
            is_fav = any(codigo in lst for lst in self.state["carteiras"].values())
            is_oculto = codigo in self.state.get("ocultos", [])
            tem_nota = codigo in self.state.get("anotacoes", {})

            active_wallet = (
                self.state["sort"].replace("cart_", "", 1)
                if self.state.get("sort", "").startswith("cart_")
                else None
            )
            pnl_hash = ""
            if active_wallet and active_wallet in self.state["carteiras"]:
                _td = self.state["carteiras"][active_wallet].get(codigo)
                if isinstance(_td, dict):
                    pnl_hash = f"{_td.get('preco_entrada', 0)}_{_td.get('quantidade', 0)}"

            # Assinatura de estado visual. Reusa card_controls se nao mudou
            data_hash = (
                f"{d.get('variacao')}_{d.get('tempoTendencia')}_"
                f"{d.get('volumeSpike')}_{str(d.get('indicadores', []))}_"
                f"{is_fav}_{is_oculto}_{tem_nota}_{pnl_hash}"
            )

            cached = card_controls.get(ticker)
            if cached is None or cached[0] != data_hash:
                new_card = create_card(
                    d,
                    self.state,
                    self.page,
                    self.render,
                    self.open_add_carteira_dialog,
                    self.open_remove_carteira_dialog,
                    self.open_notes_dialog,
                    self.save_ocultos,
                    active_wallet=active_wallet,
                )
                # Salva no cache original sob lock
                with self.app_cache_lock:
                    self.app_cache["card_controls"][ticker] = (data_hash, new_card)
                new_controls.append(new_card)
            else:
                new_controls.append(cached[1])
        return new_controls

    # ─── Contadores ─────────────────────────────────────────────────────────

    def _update_counters(self, res: list) -> None:
        alta_count = sum(
            1
            for d in res
            if not (d.get("semDados") or d.get("tendencia") == "neutra")
            and d.get("isAlta")
        )
        baixa_count = sum(
            1
            for d in res
            if not (d.get("semDados") or d.get("tendencia") == "neutra")
            and not d.get("isAlta")
        )

        self.txt_ativos_count.value = f"{len(res)} na tela"
        self.txt_alta_count.value = f"↑ {alta_count} em alta"
        self.txt_baixa_count.value = f"↓ {baixa_count} em baixa"

    # ─── Empty / loading state ──────────────────────────────────────────────

    def _show_empty_or_loading_state(self, res: list) -> None:
        if res:
            return

        if not self.state.get("is_loading", False):
            # Sem resultados
            self.list_view.controls.clear()
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.SEARCH_OFF_ROUNDED,
                                size=48,
                                color=ft.Colors.BLUE_GREY_700,
                            ),
                            ft.Text(
                                "Sem Resultados",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_400,
                            ),
                            ft.Text(
                                "Nenhum ativo corresponde aos filtros atuais.",
                                size=13,
                                color=ft.Colors.BLUE_GREY_600,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.center,
                    padding=60,
                )
            )
        else:
            # Loading state
            self.list_view.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.ProgressRing(
                                color=ft.Colors.BLUE_400,
                                stroke_width=3,
                                width=36,
                                height=36,
                            ),
                            ft.Text(
                                "Sincronizando Mercado...",
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.BLUE_GREY_400,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    alignment=ft.alignment.center,
                    padding=60,
                )
            ]
