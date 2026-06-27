"""
Dialog para adicionar/remover ativo em carteiras existentes.

Classe AddWalletDialog encapsula:
- TextField para criar carteira rapida (quick add)
- TextField para preco de entrada e quantidade
- Chips toggle para selecionar carteiras
- Dialog com botoes Salvar/Cancelar
- Funcao open_add_carteira_dialog(ticker, preco_atual)
"""
import datetime
import flet as ft
import ui.flet_patches  # noqa: F401


class AddWalletDialog:
    """Dialog para organizar ativo em carteiras.

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

        self.current_add_ticker = [None]
        self.carteiras_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=8)

        self.tf_preco_entrada = self._build_preco_field()
        self.tf_quantidade = self._build_quantidade_field()
        self.tf_quick_cart = self._build_quick_cart_field()

        self.dlg_add_cart = self._build_dialog()

    # ─── Construtores de campos ─────────────────────────────────────────

    def _build_preco_field(self) -> ft.TextField:
        return ft.TextField(
            label="Preco de Entrada (R$)",
            value="",
            expand=True,
            height=45,
            text_size=13,
            border_color=ft.Colors.BLUE_GREY_700,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        )

    def _build_quantidade_field(self) -> ft.TextField:
        return ft.TextField(
            label="Qtd",
            value="100",
            width=100,
            height=45,
            text_size=13,
            border_color=ft.Colors.BLUE_GREY_700,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        )

    def _build_quick_cart_field(self) -> ft.TextField:
        return ft.TextField(
            hint_text="Nome da nova carteira...",
            height=40,
            expand=True,
            text_size=13,
            border_color=ft.Colors.BLUE_GREY_700,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            border_radius=8,
            content_padding=10,
        )

    def _build_dialog(self) -> ft.AlertDialog:
        return ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_SPECIAL, color=ft.Colors.AMBER_500),
                    ft.Text("Organizar Ativo", weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                self.tf_quick_cart,
                                ft.IconButton(
                                    ft.Icons.ADD_CIRCLE,
                                    icon_color=ft.Colors.BLUE_400,
                                    on_click=self._quick_add_carteira,
                                    tooltip="Criar carteira e adicionar",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(
                            height=20,
                            color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                        ),
                        ft.Text(
                            "Selecione as carteiras para adicionar/remover o ativo:",
                            size=12,
                            color=ft.Colors.BLUE_GREY_300,
                        ),
                        self.carteiras_chips_row,
                    ],
                    tight=True,
                    spacing=15,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self._fechar,
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                ),
                ft.Button(
                    "Salvar Alteracoes",
                    on_click=self._salvar_ativos_carteiras,
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                ),
            ],
        )

    # ─── Helpers de dados ───────────────────────────────────────────────

    def _get_dict_ativo(self) -> dict:
        """Constroi dict com data, preco_entrada e quantidade."""
        hoje_str = datetime.date.today().isoformat()
        try:
            preco_val = (
                float(self.tf_preco_entrada.value.replace(",", "."))
                if self.tf_preco_entrada.value
                else 0.0
            )
        except ValueError:
            preco_val = 0.0

        try:
            qtd_val = (
                float(self.tf_quantidade.value.replace(",", "."))
                if self.tf_quantidade.value
                else 1.0
            )
            if qtd_val <= 0:
                qtd_val = 1.0
        except (ValueError, AttributeError):
            qtd_val = 1.0

        return {
            "data": hoje_str,
            "preco_entrada": preco_val,
            "quantidade": qtd_val,
        }

    # ─── Callbacks ──────────────────────────────────────────────────────

    def _quick_add_carteira(self, e):
        """Cria carteira rapidamente e adiciona o ativo nela."""
        nome = self.tf_quick_cart.value.strip()
        ticker = self.current_add_ticker[0]
        if nome and ticker and nome not in self.state["carteiras"]:
            self.state["carteiras"][nome] = {ticker: self._get_dict_ativo()}
            self.save_carteiras()
            self.tf_quick_cart.value = ""
            self.update_sort_pills_callback()
            # Retorna valor anterior para o reload visual
            try:
                preco_atual = (
                    float(self.tf_preco_entrada.value.replace(",", "."))
                    if self.tf_preco_entrada.value
                    else 0.0
                )
            except (ValueError, AttributeError):
                preco_atual = 0.0
            self.open(ticker, preco_atual)
        else:
            self.page.update()

    def _salvar_ativos_carteiras(self, e):
        """Salva selecoes de chips: adiciona em selecionadas, remove de nao-selecionadas."""
        ticker = self.current_add_ticker[0]
        if ticker:
            dict_ativo = self._get_dict_ativo()

            nome = self.tf_quick_cart.value.strip()
            if nome and nome not in self.state["carteiras"]:
                self.state["carteiras"][nome] = {ticker: dict_ativo}
                self.update_sort_pills_callback()

            for c in self.carteiras_chips_row.controls:
                c_nome = c.data["nome"]
                is_selected = c.data["selected"]
                if is_selected:
                    self.state["carteiras"][c_nome][ticker] = dict_ativo
                elif not is_selected and ticker in self.state["carteiras"][c_nome]:
                    del self.state["carteiras"][c_nome][ticker]
            self.dlg_add_cart.open = False
            self.save_carteiras()
            self.render_list()
        else:
            self.page.update()

    def _fechar(self, e):
        self.dlg_add_cart.open = False
        self._safe_page_update()

    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            self.page.update()
        except Exception:
            pass

    # ─── Construcao de chips ────────────────────────────────────────────

    def _toggle_cart_selection(self, e):
        """Alterna selecao de um chip de carteira."""
        c = e.control
        c.data["selected"] = not c.data["selected"]
        is_sel = c.data["selected"]
        c.bgcolor = (
            ft.Colors.with_opacity(0.15, ft.Colors.BLUE_400)
            if is_sel
            else ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
        )
        c.border = ft.border.all(
            1,
            ft.Colors.BLUE_400
            if is_sel
            else ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        )
        c.content.controls[0].name = (
            ft.Icons.CHECK_CIRCLE if is_sel else ft.Icons.FOLDER_OPEN
        )
        c.content.controls[0].color = (
            ft.Colors.BLUE_400 if is_sel else ft.Colors.BLUE_GREY_400
        )
        c.content.controls[1].color = (
            ft.Colors.WHITE if is_sel else ft.Colors.BLUE_GREY_300
        )
        c.update()

    def _build_chip(self, c_nome: str, is_sel: bool, ticker: str) -> ft.Container:
        """Constroi um chip de carteira para selecao."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if is_sel else ft.Icons.FOLDER_OPEN,
                        size=14,
                        color=ft.Colors.BLUE_400
                        if is_sel
                        else ft.Colors.BLUE_GREY_400,
                    ),
                    ft.Text(
                        c_nome,
                        size=12,
                        color=ft.Colors.WHITE
                        if is_sel
                        else ft.Colors.BLUE_GREY_300,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                tight=True,
                spacing=6,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_400)
            if is_sel
            else ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border=ft.border.all(
                1,
                ft.Colors.BLUE_400
                if is_sel
                else ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            ),
            on_click=self._toggle_cart_selection,
            data={"nome": c_nome, "selected": is_sel},
        )

    # ─── API publica ────────────────────────────────────────────────────

    def open(self, ticker: str, preco_atual: float = 0.0):
        """Abre dialog para organizar ativo em carteiras.

        Args:
            ticker: codigo do ativo (ex: 'PETR4')
            preco_atual: preco atual do ativo para preencher campo de entrada
        """
        self.current_add_ticker[0] = ticker
        self.dlg_add_cart.title.controls[1].value = f"Organizar: {ticker}"

        self.tf_preco_entrada.value = (
            f"{preco_atual:.2f}".replace(".", ",") if preco_atual > 0 else ""
        )
        self.tf_quantidade.value = "100"

        self.carteiras_chips_row.controls.clear()

        for c_nome in sorted(self.state["carteiras"].keys()):
            ativos = self.state["carteiras"][c_nome]
            is_sel = ticker in ativos
            chip = self._build_chip(c_nome, is_sel, ticker)
            self.carteiras_chips_row.controls.append(chip)

        self.tf_quick_cart.value = ""
        if self.dlg_add_cart not in self.page.overlay:
            self.page.overlay.append(self.dlg_add_cart)
        self.dlg_add_cart.open = True
        self._safe_page_update()
