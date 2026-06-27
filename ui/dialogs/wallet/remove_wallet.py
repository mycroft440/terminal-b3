"""
Dialog para confirmar remocao de ativo de carteiras.

Classe RemoveWalletDialog encapsula:
- Title e subtitle dinamicos (1 carteira vs multiplas)
- Chips toggle para selecionar quais carteiras remover
- Dialog com botoes Remover/Cancelar
- Funcao open_remove_carteira_dialog(ticker, carteiras_presentes)
"""
import flet as ft
import ui.flet_patches  # noqa: F401


class RemoveWalletDialog:
    """Dialog para confirmar remocao de ativo de uma ou mais carteiras.

    Args:
        page: ft.Page
        state: state global (com 'carteiras')
        save_carteiras: callback para persistir state['carteiras']
        render_list: callback para re-renderizar lista
    """

    def __init__(self, page: ft.Page, state: dict, save_carteiras, render_list):
        self.page = page
        self.state = state
        self.save_carteiras = save_carteiras
        self.render_list = render_list

        self.current_remove_ticker = [None]
        self.carteiras_remove_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=8)
        self.dlg_remove_cart_title = ft.Text("", weight=ft.FontWeight.BOLD)
        self.dlg_remove_cart_subtitle = ft.Text(
            "", size=12, color=ft.Colors.BLUE_GREY_300
        )

        self.dlg_remove_cart = self._build_dialog()

    def _build_dialog(self) -> ft.AlertDialog:
        return ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_400),
                    self.dlg_remove_cart_title,
                ]
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        self.dlg_remove_cart_subtitle,
                        self.carteiras_remove_chips_row,
                    ],
                    tight=True,
                    spacing=10,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self._fechar,
                ),
                ft.Button(
                    "Remover",
                    on_click=self._confirmar_remocao,
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                ),
            ],
        )

    # ─── Callbacks ──────────────────────────────────────────────────────

    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            self.page.update()
        except Exception:
            pass

    def _confirmar_remocao(self, e):
        """Confirma remocao: deleta ativo das carteiras selecionadas."""
        ticker = self.current_remove_ticker[0]
        self.dlg_remove_cart.open = False
        removidas = False
        if ticker:
            for c in self.carteiras_remove_chips_row.controls:
                if c.data.get("selected"):
                    c_nome = c.data["nome"]
                    if ticker in self.state["carteiras"][c_nome]:
                        del self.state["carteiras"][c_nome][ticker]
                        removidas = True
            if removidas:
                self.save_carteiras()
                self.render_list()
                return  # render_list() chama page.update() internamente
        self._safe_page_update()

    def _fechar(self, e):
        self.dlg_remove_cart.open = False
        self._safe_page_update()

    # ─── Construcao de chips ────────────────────────────────────────────

    def _toggle_remove_selection(self, e):
        """Alterna selecao de um chip de carteira para remocao."""
        c = e.control
        c.data["selected"] = not c.data["selected"]
        is_sel = c.data["selected"]
        c.bgcolor = (
            ft.Colors.with_opacity(0.15, ft.Colors.RED_400)
            if is_sel
            else ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
        )
        c.border = ft.border.all(
            1,
            ft.Colors.RED_400
            if is_sel
            else ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        )
        c.content.controls[0].name = (
            ft.Icons.DELETE if is_sel else ft.Icons.FOLDER
        )
        c.content.controls[0].color = (
            ft.Colors.RED_400 if is_sel else ft.Colors.BLUE_GREY_400
        )
        c.content.controls[1].color = (
            ft.Colors.WHITE if is_sel else ft.Colors.BLUE_GREY_300
        )
        c.update()

    def _build_chip(self, c_nome: str) -> ft.Container:
        """Constroi chip de carteira para selecao de remocao."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.FOLDER, size=14, color=ft.Colors.BLUE_GREY_400
                    ),
                    ft.Text(
                        c_nome,
                        size=12,
                        color=ft.Colors.BLUE_GREY_300,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                tight=True,
                spacing=6,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
            on_click=self._toggle_remove_selection,
            data={"nome": c_nome, "selected": False},
        )

    # ─── API publica ────────────────────────────────────────────────────

    def open(self, ticker: str, carteiras_presentes: list):
        """Abre dialog para remover ativo de carteiras.

        Args:
            ticker: codigo do ativo (ex: 'PETR4')
            carteiras_presentes: lista de nomes de carteiras que contem o ticker

        Comportamento:
        - 1 carteira: mostra mensagem de confirmacao direta (chip oculto)
        - Multiplas: mostra chips para selecionar quais remover
        """
        self.current_remove_ticker[0] = ticker
        self.carteiras_remove_chips_row.controls.clear()

        if len(carteiras_presentes) == 1:
            nome_cart = carteiras_presentes[0]
            self.dlg_remove_cart_title.value = "Remover da Carteira?"
            self.dlg_remove_cart_subtitle.value = (
                f"Tem certeza que deseja remover o ativo {ticker} "
                f"da carteira '{nome_cart}'?"
            )

            # Chip oculto marcado como selecionado (para confirmar remocao)
            c = ft.Container(data={"nome": nome_cart, "selected": True}, visible=False)
            self.carteiras_remove_chips_row.controls.append(c)
        else:
            self.dlg_remove_cart_title.value = "Remover de quais carteiras?"
            self.dlg_remove_cart_subtitle.value = (
                f"O ativo {ticker} esta salvo em {len(carteiras_presentes)} "
                f"carteiras. Selecione de onde deseja remover:"
            )

            for c_nome in carteiras_presentes:
                chip = self._build_chip(c_nome)
                self.carteiras_remove_chips_row.controls.append(chip)

        if self.dlg_remove_cart not in self.page.overlay:
            self.page.overlay.append(self.dlg_remove_cart)
        self.dlg_remove_cart.open = True
        self._safe_page_update()
