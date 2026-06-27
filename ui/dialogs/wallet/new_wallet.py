"""
Dialog para criar nova carteira.

Classe NewWalletDialog encapsula:
- TextField para nome da carteira
- Dialog com botoes Criar/Cancelar
- Funcao open_nova_carteira_dialog()
"""
import flet as ft
import ui.flet_patches  # noqa: F401


class NewWalletDialog:
    """Dialog para criar nova carteira.

    Args:
        page: ft.Page
        state: state global (com 'carteiras')
        save_carteiras: callback para persistir state['carteiras']
        save_ui_state: callback para persistir state['sort']
        update_sort_pills_callback: callback para atualizar pills de ordenacao
        render_list: callback para re-renderizar lista de cards
    """

    def __init__(self, page: ft.Page, state: dict, save_carteiras, save_ui_state,
                 update_sort_pills_callback, render_list):
        self.page = page
        self.state = state
        self.save_carteiras = save_carteiras
        self.save_ui_state = save_ui_state
        self.update_sort_pills_callback = update_sort_pills_callback
        self.render_list = render_list

        self.tf_nova_cart = ft.TextField(label="Nome da Nova Carteira", width=300)
        self.dlg_nova_cart = self._build_dialog()

    def _build_dialog(self) -> ft.AlertDialog:
        return ft.AlertDialog(
            title=ft.Text("Criar Nova Carteira"),
            content=self.tf_nova_cart,
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self._fechar,
                ),
                ft.Button(
                    "Criar",
                    on_click=self._salvar,
                    bgcolor=ft.Colors.GREEN_600,
                    color=ft.Colors.WHITE,
                ),
            ],
        )

    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            self.page.update()
        except Exception:
            pass

    def _salvar(self, e):
        """Salva nova carteira se nome for valido e unico."""
        nome = self.tf_nova_cart.value.strip()
        self.dlg_nova_cart.open = False
        if nome and nome not in self.state["carteiras"]:
            self.state["carteiras"][nome] = {}
            self.save_carteiras()
            self.state["sort"] = f"cart_{nome}"
            self.save_ui_state()
            self.update_sort_pills_callback()
            self.render_list()
        else:
            self.page.update()

    def _fechar(self, e):
        self.dlg_nova_cart.open = False
        self._safe_page_update()

    def open(self):
        """Abre dialog para criar nova carteira."""
        self.tf_nova_cart.value = ""
        if self.dlg_nova_cart not in self.page.overlay:
            self.page.overlay.append(self.dlg_nova_cart)
        self.dlg_nova_cart.open = True
        self._safe_page_update()
