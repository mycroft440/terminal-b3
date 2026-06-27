"""
WalletView - aba exclusiva da carteira com tabela de variacoes.

Mostra tabela com colunas:
- Ativo (codigo + nome)
- Preco atual
- Variacao 1D
- Variacao 7D
- Variacao 30D
- Variacao desde entrada (PnL %)
- PnL R$ (valor monetario)
- Data entrada
- Acoes (remover, nota)

Substitui a lista de cards quando o usuario esta visualizando uma carteira,
dando visao tabular completa do portfolio.
"""
import flet as ft
import threading
from datetime import datetime
import ui.flet_patches  # noqa: F401


class WalletView:
    """View tabular para visualizar carteira com variacoes completas.

    Thread-safe: usa _render_lock para evitar renders concorrentes.

    Args:
        page: ft.Page
        state: state global (com 'carteiras', 'anotacoes')
        app_cache: dict com 'evaluated_assets'
        app_cache_lock: threading.Lock
        get_config_hash: callback que retorna hash da config atual
        open_remove_carteira_dialog: callback(ticker, carteiras_presentes)
        open_notes_dialog: callback(ticker)
        render_list: callback para re-renderizar
    """

    def __init__(
        self,
        page: ft.Page,
        state: dict,
        app_cache: dict,
        app_cache_lock,
        get_config_hash,
        open_remove_carteira_dialog,
        open_notes_dialog,
        render_list,
        on_voltar=None,
    ):
        self.page = page
        self.state = state
        self.app_cache = app_cache
        self.app_cache_lock = app_cache_lock
        self.get_config_hash = get_config_hash
        self.open_remove_carteira_dialog = open_remove_carteira_dialog
        self.open_notes_dialog = open_notes_dialog
        self.render_list = render_list
        self.on_voltar = on_voltar
        # Lock de renderizacao: evita renders concorrentes (BUG 11)
        self._render_lock = threading.Lock()

        # ListView que contera a tabela
        self.list_view = ft.ListView(
            expand=True,
            spacing=2,
            padding=ft.Padding(left=16, top=8, right=16, bottom=16),
        )

    def _safe_page_update(self):
        """Atualiza apenas a list_view (nao a pagina inteira)."""
        try:
            self.list_view.update()
        except Exception:
            pass

    def render(self):
        """Renderiza a tabela da carteira ativa.

        Thread-safe: se lock estiver ocupado, skip (BUG 11).
        """
        if not str(self.state.get("sort", "")).startswith("cart_"):
            return

        if not self._render_lock.acquire(blocking=False):
            return  # Outra renderizacao em andamento — skip
        try:
            self._do_render()
        finally:
            self._render_lock.release()

    def _do_render(self):
        """Executa a renderizacao real."""
        cart_nome = self.state["sort"].replace("cart_", "", 1)
        carteira = self.state["carteiras"].get(cart_nome, {})

        if not carteira:
            self._show_empty_state(cart_nome)
            self._safe_page_update()
            return

        # Obtem dados avaliados do cache
        current_hash = self.get_config_hash()
        with self.app_cache_lock:
            evaluated = list(self.app_cache["evaluated_assets"].get(current_hash, []))

        # Mapa ticker -> dado avaliado para lookup rapido
        dados_map = {}
        for d in evaluated:
            ticker = d.get("ativo", {}).get("ticker", "")
            if ticker:
                dados_map[ticker] = d

        # Constroi lista de ativos da carteira com dados + posicao
        ativos_data = []
        for ticker, posicao in carteira.items():
            dado = dados_map.get(ticker)
            if dado is None:
                # Ticker nao tem dados de mercado ainda
                codigo = ticker.replace(".SA", "")
                ativos_data.append({
                    "ticker": ticker,
                    "codigo": codigo,
                    "nome": codigo,
                    "fechamento": 0.0,
                    "variacao": 0.0,
                    "variacao_7d": 0.0,
                    "variacao_30d": 0.0,
                    "semDados": True,
                    "posicao": posicao if isinstance(posicao, dict) else {},
                })
            else:
                ativo = dado.get("ativo", {})
                ativos_data.append({
                    "ticker": ticker,
                    "codigo": ativo.get("codigo", ticker.replace(".SA", "")),
                    "nome": ativo.get("nome", ""),
                    "fechamento": float(dado.get("fechamento", 0) or 0),
                    "variacao": float(dado.get("variacao", 0) or 0),
                    "variacao_7d": float(dado.get("variacao_7d", 0) or 0),
                    "variacao_30d": float(dado.get("variacao_30d", 0) or 0),
                    "semDados": dado.get("semDados", False),
                    "posicao": posicao if isinstance(posicao, dict) else {},
                })

        # Renderiza tabela
        self.list_view.controls.clear()
        # Botao Voltar no topo da area de conteudo
        self.list_view.controls.append(self._build_voltar_row(cart_nome))
        self.list_view.controls.append(self._build_header_row())
        self.list_view.controls.append(
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.2, ft.Colors.BLUE_GREY_600))
        )

        for ativo in ativos_data:
            self.list_view.controls.append(self._build_ativo_row(ativo, cart_nome))

        self._safe_page_update()

    def _build_voltar_row(self, cart_nome: str) -> ft.Container:
        """Botão Voltar estilizado no topo da área de conteúdo da carteira."""
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
                        f"📂 {cart_nome}",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.AMBER_400,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(0, 4, 0, 8),
        )

    def _build_header_row(self) -> ft.Container:
        """Linha de cabecalho da tabela."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text("ATIVO", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=140),
                    ft.Text("PREÇO", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=80,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("1D", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("7D", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("30D", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("ENTRADA", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=80,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("PnL %", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=80,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("PnL R$", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=90,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("QTD", size=10, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400, width=60,
                            text_align=ft.TextAlign.RIGHT),
                    ft.Text("", width=50),  # espaco para acoes
                ],
                spacing=4,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_800),
            border_radius=8,
        )

    def _build_ativo_row(self, ativo: dict, cart_nome: str) -> ft.Container:
        """Linha de um ativo na tabela."""
        ticker = ativo["ticker"]
        codigo = ativo["codigo"]
        nome = ativo["nome"]
        preco = ativo["fechamento"]
        var_1d = ativo["variacao"]
        var_7d = ativo["variacao_7d"]
        var_30d = ativo["variacao_30d"]
        sem_dados = ativo.get("semDados", False)

        posicao = ativo["posicao"]
        preco_entrada = float(posicao.get("preco_entrada", 0) or 0)
        quantidade = float(posicao.get("quantidade", 0) or 0)
        data_entrada = posicao.get("data", "")

        # Calcula PnL
        pnl_pct = 0.0
        pnl_valor = 0.0
        if preco_entrada > 0 and preco > 0:
            pnl_pct = ((preco / preco_entrada) - 1) * 100
            pnl_valor = (preco - preco_entrada) * quantidade

        # Cores para variacoes
        def cor_var(v):
            if sem_dados or v == 0:
                return ft.Colors.BLUE_GREY_400
            return ft.Colors.GREEN_400 if v > 0 else ft.Colors.RED_400

        def fmt_var(v):
            if sem_dados:
                return "—"
            sinal = "+" if v > 0 else ""
            return f"{sinal}{v:.2f}%"

        def fmt_preco(v):
            if sem_dados:
                return "—"
            return f"R$ {v:.2f}"

        # Formata data de entrada (ISO -> DD/MM/AA)
        data_fmt = ""
        if data_entrada:
            try:
                dt = datetime.fromisoformat(data_entrada)
                data_fmt = dt.strftime("%d/%m/%y")
            except (ValueError, TypeError):
                data_fmt = data_entrada[:10] if len(data_entrada) >= 10 else data_entrada

        # Cor do PnL
        cor_pnl = ft.Colors.BLUE_GREY_400
        if pnl_pct > 0:
            cor_pnl = ft.Colors.GREEN_400
        elif pnl_pct < 0:
            cor_pnl = ft.Colors.RED_400

        sinal_pnl = "+" if pnl_pct > 0 else ""

        # Botoes de acao
        def on_remover(e, t=ticker, c=cart_nome):
            self.open_remove_carteira_dialog(t, [c])

        def on_nota(e, t=ticker.replace(".SA", "")):
            self.open_notes_dialog(t)

        btn_remover = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            icon_size=16,
            icon_color=ft.Colors.RED_400,
            tooltip="Remover da carteira",
            on_click=on_remover,
            style=ft.ButtonStyle(padding=0),
        )
        btn_nota = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE,
            icon_size=16,
            icon_color=ft.Colors.BLUE_400 if ticker in self.state.get("anotacoes", {}) else ft.Colors.BLUE_GREY_600,
            tooltip="Ver/editar nota",
            on_click=on_nota,
            style=ft.ButtonStyle(padding=0),
        )

        # Nome curto (primeiras 20 chars)
        nome_curto = nome[:20] + "..." if len(nome) > 20 else nome

        return ft.Container(
            content=ft.Row(
                [
                    # Ativo
                    ft.Column(
                        [
                            ft.Text(codigo, size=12, weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE),
                            ft.Text(nome_curto, size=9, color=ft.Colors.BLUE_GREY_400,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=0,
                        width=140,
                    ),
                    # Preco
                    ft.Text(fmt_preco(preco), size=11, color=ft.Colors.WHITE,
                            width=80, text_align=ft.TextAlign.RIGHT),
                    # 1D
                    ft.Text(fmt_var(var_1d), size=11, color=cor_var(var_1d),
                            weight=ft.FontWeight.W_600, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    # 7D
                    ft.Text(fmt_var(var_7d), size=11, color=cor_var(var_7d),
                            weight=ft.FontWeight.W_600, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    # 30D
                    ft.Text(fmt_var(var_30d), size=11, color=cor_var(var_30d),
                            weight=ft.FontWeight.W_600, width=70,
                            text_align=ft.TextAlign.RIGHT),
                    # Entrada (data)
                    ft.Text(data_fmt if data_fmt else "—",
                            size=11, color=ft.Colors.BLUE_GREY_300,
                            width=80, text_align=ft.TextAlign.RIGHT),
                    # PnL %
                    ft.Text(
                        f"{sinal_pnl}{pnl_pct:.2f}%" if preco_entrada > 0 else "—",
                        size=11, color=cor_pnl, weight=ft.FontWeight.BOLD,
                        width=80, text_align=ft.TextAlign.RIGHT,
                    ),
                    # PnL R$
                    ft.Text(
                        f"R$ {pnl_valor:+.2f}" if preco_entrada > 0 and quantidade > 0 else "—",
                        size=11, color=cor_pnl, weight=ft.FontWeight.W_600,
                        width=90, text_align=ft.TextAlign.RIGHT,
                    ),
                    # Qtd
                    ft.Text(
                        f"{quantidade:.0f}" if quantidade > 0 else "—",
                        size=11, color=ft.Colors.BLUE_GREY_300,
                        width=60, text_align=ft.TextAlign.RIGHT,
                    ),
                    # Acoes
                    ft.Row([btn_nota, btn_remover], spacing=0, width=50),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.BLUE_GREY_700),
            border=ft.border.all(1, ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_700)),
            ink=True,
        )

    def _show_empty_state(self, cart_nome: str):
        """Mostra estado vazio quando carteira nao tem ativos."""
        self.list_view.controls.clear()
        # Botao Voltar mesmo no estado vazio
        self.list_view.controls.append(self._build_voltar_row(cart_nome))
        self.list_view.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.FOLDER_OPEN,
                            size=48,
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        ft.Text(
                            f"Carteira '{cart_nome}' está vazia",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_GREY_400,
                        ),
                        ft.Text(
                            "Clique em 'Adicionar Ativo' para começar",
                            size=12,
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
