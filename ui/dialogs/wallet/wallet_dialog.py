"""
Orquestrador dos dialogs de carteira.

Reune NewWalletDialog, AddWalletDialog, RemoveWalletDialog e expoe
create_wallet_dialogs() que retorna dict com 3 openers (API retrocompativel).
"""
import flet as ft
from ui.dialogs.wallet.new_wallet import NewWalletDialog
from ui.dialogs.wallet.add_wallet import AddWalletDialog
from ui.dialogs.wallet.remove_wallet import RemoveWalletDialog
import ui.flet_patches  # noqa: F401


def create_wallet_dialogs(
    page: ft.Page,
    state: dict,
    save_carteiras,
    save_ui_state,
    render_list,
    update_sort_pills_callback,
):
    """Cria os 3 dialogs de carteira e retorna dict com openers.

    Args:
        page: ft.Page
        state: state global (com 'carteiras', 'sort')
        save_carteiras: callback para persistir state['carteiras']
        save_ui_state: callback para persistir state['sort']
        render_list: callback para re-renderizar lista
        update_sort_pills_callback: callback para atualizar pills de ordenacao

    Returns:
        dict com 3 openers (API retrocompativel com main_page.py):
        - 'open_nova_carteira_dialog': () -> None
        - 'open_add_carteira_dialog': (ticker, preco_atual=0.0) -> None
        - 'open_remove_carteira_dialog': (ticker, carteiras_presentes: list) -> None
    """
    new_wallet = NewWalletDialog(
        page=page,
        state=state,
        save_carteiras=save_carteiras,
        save_ui_state=save_ui_state,
        update_sort_pills_callback=update_sort_pills_callback,
        render_list=render_list,
    )

    add_wallet = AddWalletDialog(
        page=page,
        state=state,
        save_carteiras=save_carteiras,
        update_sort_pills_callback=update_sort_pills_callback,
        render_list=render_list,
    )

    remove_wallet = RemoveWalletDialog(
        page=page,
        state=state,
        save_carteiras=save_carteiras,
        render_list=render_list,
    )

    return {
        "open_nova_carteira_dialog": new_wallet.open,
        "open_add_carteira_dialog": add_wallet.open,
        "open_remove_carteira_dialog": remove_wallet.open,
    }
