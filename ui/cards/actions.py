"""Coluna de acoes do card: favorito + ocultar/exibir."""
import logging
import flet as ft
import ui.flet_patches  # noqa: F401


def build_actions(
    codigo_ativo: str,
    is_fav: bool,
    is_oculto: bool,
    preco_atual: float,
    state: dict,
    active_wallet,
    open_add_carteira_dialog,
    open_remove_carteira_dialog,
    save_ocultos,
    render_list,
) -> ft.Column:
    """Constroi coluna de acoes com IconButton de favorito e ocultar.

    Args:
        codigo_ativo: codigo do ativo (ex: 'PETR4')
        is_fav: True se ativo esta em alguma carteira
        is_oculto: True se ativo esta oculto
        preco_atual: preco atual do ativo (para dialog de adicionar carteira)
        state: state global do app
        active_wallet: nome da carteira ativa ou None
        open_add_carteira_dialog: callback(ticker, preco)
        open_remove_carteira_dialog: callback(ticker, carteiras)
        save_ocultos: callback para persistir state['ocultos']
        render_list: callback para re-renderizar lista apos mutacao

    Returns:
        ft.Column com 2 IconButton (favorito + ocultar)
    """
    def on_fav_click(e):
        carteiras_presentes = [
            c for c, ativos in state["carteiras"].items() if codigo_ativo in ativos or any(codigo_ativo == t.replace(".SA","") for t in ativos)
        ]
        if not carteiras_presentes:
            open_add_carteira_dialog(codigo_ativo, preco_atual)
        else:
            if active_wallet and active_wallet in carteiras_presentes:
                open_remove_carteira_dialog(codigo_ativo, [active_wallet])
            else:
                open_remove_carteira_dialog(codigo_ativo, carteiras_presentes)

    fav_icon = ft.IconButton(
        icon=ft.Icons.STAR_ROUNDED if is_fav else ft.Icons.STAR_OUTLINE_ROUNDED,
        icon_color=ft.Colors.AMBER_400 if is_fav else ft.Colors.BLUE_GREY_700,
        icon_size=20,
        on_click=on_fav_click,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_900)
        if is_fav
        else ft.Colors.TRANSPARENT,
    )

    def on_hide_click(e):
        if codigo_ativo in state.get("ocultos", []) or any(codigo_ativo == t.replace(".SA","") for t in state.get("ocultos", [])):
            logging.info(f"Usuário re-exibiu ativo oculto: {codigo_ativo}")
            state["ocultos"].remove(codigo_ativo)
        else:
            logging.info(f"Usuário ocultou ativo: {codigo_ativo}")
            state.setdefault("ocultos", []).append(codigo_ativo)
        save_ocultos()
        render_list()

    hide_icon = ft.IconButton(
        icon=ft.Icons.VISIBILITY_OFF if is_oculto else ft.Icons.VISIBILITY_ROUNDED,
        icon_color=ft.Colors.RED_400 if is_oculto else ft.Colors.BLUE_GREY_700,
        icon_size=18,
        tooltip="Ocultar/Exibir",
        on_click=on_hide_click,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.RED_900)
        if is_oculto
        else ft.Colors.TRANSPARENT,
    )

    return ft.Column([fav_icon, hide_icon], spacing=2)
