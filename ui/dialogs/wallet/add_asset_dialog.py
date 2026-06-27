"""
Dialog para adicionar ativo a uma carteira via busca por ticker ou nome.

AddAssetDialog:
- TextField de busca com on_change que filtra catálogo em tempo real
- ListView com resultados clicaveis (max 10)
- Ao clicar num resultado, abre AddWalletDialog para escolher carteira + preco
"""
import flet as ft
from core.catalog import carregar_catalogo
from ui.dialogs.wallet.add_wallet import AddWalletDialog
import ui.flet_patches  # noqa: F401


class AddAssetDialog:
    """Dialog para buscar e adicionar ativo a carteira.

    Fluxo:
    1. Usuario digita ticker ou nome da empresa
    2. Lista filtra em tempo real (max 10 resultados)
    3. Usuario clica num resultado
    4. Abre AddWalletDialog para selecionar carteira + preco + quantidade

    Args:
        page: ft.Page
        state: state global (com 'carteiras')
        save_carteiras: callback para persistir state['carteiras']
        update_sort_pills_callback: callback para atualizar pills
        render_list: callback para re-renderizar lista
    """

    def __init__(self, page: ft.Page, state: dict, save_carteiras,
                 update_sort_pills_callback, render_list):
        self.page = page
        self.state = state
        self.save_carteiras = save_carteiras
        self.update_sort_pills_callback = update_sort_pills_callback
        self.render_list = render_list

        # Cache do catalogo (carregado uma vez)
        self._catalogo = carregar_catalogo()

        # AddWalletDialog para o passo 2 (selecionar carteira + preco)
        self._add_wallet_dialog = AddWalletDialog(
            page=page,
            state=state,
            save_carteiras=save_carteiras,
            update_sort_pills_callback=update_sort_pills_callback,
            render_list=render_list,
        )

        # TextField de busca
        self.tf_busca = ft.TextField(
            hint_text="Digite o ticker (ex: PETR4) ou nome da empresa...",
            prefix_icon=ft.Icons.SEARCH,
            autofocus=True,
            expand=True,
            on_change=self._on_busca_change,
            text_size=14,
        )

        # ListView com resultados
        self.lv_resultados = ft.ListView(
            spacing=4,
            expand=True,
            height=300,
        )

        # Dialog principal
        self.dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.BLUE_400),
                    ft.Text("Adicionar Ativo", weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        self.tf_busca,
                        ft.Divider(height=1),
                        self.lv_resultados,
                    ],
                    spacing=10,
                    tight=True,
                ),
                width=500,
                height=400,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self._fechar,
                ),
            ],
        )

    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros."""
        try:
            self.page.update()
        except Exception:
            pass

    def _on_busca_change(self, e):
        """Filtra catalogo conforme usuario digita."""
        query = (self.tf_busca.value or "").strip().lower()
        self.lv_resultados.controls.clear()

        if not query:
            self.lv_resultados.controls.append(
                ft.Text(
                    "Digite para buscar ativos...",
                    size=12,
                    color=ft.Colors.BLUE_GREY_400,
                    italic=True,
                )
            )
            self._safe_page_update()
            return

        # Filtra por codigo OU nome (case-insensitive)
        resultados = []
        for ativo in self._catalogo:
            codigo = str(ativo.get("codigo", "")).lower()
            nome = str(ativo.get("nome", "")).lower()
            ticker = str(ativo.get("ticker", "")).lower()
            if query in codigo or query in nome or query in ticker:
                resultados.append(ativo)
                if len(resultados) >= 10:  # Limita a 10 resultados
                    break

        if not resultados:
            self.lv_resultados.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.SEARCH_OFF,
                                size=32,
                                color=ft.Colors.BLUE_GREY_600,
                            ),
                            ft.Text(
                                "Nenhum ativo encontrado",
                                size=13,
                                color=ft.Colors.BLUE_GREY_400,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )
        else:
            for ativo in resultados:
                self.lv_resultados.controls.append(
                    self._build_result_item(ativo)
                )

        self._safe_page_update()

    def _build_result_item(self, ativo: dict) -> ft.Container:
        """Constroi item clicavel de resultado de busca."""
        codigo = ativo.get("codigo", "")
        nome = ativo.get("nome", "")
        ticker = ativo.get("ticker", "")
        setor = ativo.get("setor", "")
        tipo = ativo.get("tipo", "")

        # Cor do badge por tipo
        tipo_cor = ft.Colors.BLUE_300
        tipo_label = "ACAO"
        if tipo == "fiis":
            tipo_cor = ft.Colors.INDIGO_300
            tipo_label = "FII"
        elif tipo == "bdrs":
            tipo_cor = ft.Colors.TEAL_300
            tipo_label = "BDR"

        def on_click_result(e, t=ticker):
            self._selecionar_ativo(t)

        return ft.Container(
            content=ft.Row(
                [
                    # Badge do codigo
                    ft.Container(
                        content=ft.Text(
                            codigo,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_700),
                        padding=ft.Padding(8, 4, 8, 4),
                        border_radius=6,
                        border=ft.border.all(
                            1, ft.Colors.with_opacity(0.2, ft.Colors.BLUE_GREY_600)
                        ),
                    ),
                    # Nome da empresa
                    ft.Column(
                        [
                            ft.Text(
                                nome,
                                size=12,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(
                                f"{setor} • {ticker}" if setor else ticker,
                                size=10,
                                color=ft.Colors.BLUE_GREY_400,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    # Badge do tipo
                    ft.Container(
                        content=ft.Text(
                            tipo_label,
                            size=9,
                            weight=ft.FontWeight.BOLD,
                            color=tipo_cor,
                        ),
                        bgcolor=ft.Colors.with_opacity(0.1, tipo_cor),
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=4,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.2, tipo_cor)),
                    ),
                    # Icon de adicionar
                    ft.Icon(
                        ft.Icons.ADD_CIRCLE,
                        color=ft.Colors.GREEN_400,
                        size=20,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_700),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_600)),
            on_click=on_click_result,
            ink=True,
        )

    def _selecionar_ativo(self, ticker: str):
        """Fecha dialog de busca e abre AddWalletDialog para o ticker."""
        # Fecha dialog de busca
        self.dlg.open = False
        self._safe_page_update()
        # Abre dialog de adicionar a carteira (passo 2)
        self._add_wallet_dialog.open(ticker, preco_atual=0.0)

    def _fechar(self, e):
        self.dlg.open = False
        self._safe_page_update()

    def open(self):
        """Abre dialog de busca de ativos."""
        self.tf_busca.value = ""
        self.lv_resultados.controls.clear()
        self.lv_resultados.controls.append(
            ft.Text(
                "Digite para buscar ativos...",
                size=12,
                color=ft.Colors.BLUE_GREY_400,
                italic=True,
            )
        )
        if self.dlg not in self.page.overlay:
            self.page.overlay.append(self.dlg)
        self.dlg.open = True
        self._safe_page_update()
