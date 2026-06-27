"""
Componentes reutilizaveis de UI Flet.

Funcoes helper para construir widgets comuns (dropdown options,
pill buttons, etc). Funcoes puras - sem estado, sem side effects.
"""
import flet as ft
import ui.flet_patches  # noqa: F401  # garante patches de Flet >= 0.80 aplicados


def dropdown_options(opcoes):
    """Converte lista de (key, label) em lista de ft.dropdown.Option."""
    return [ft.dropdown.Option(key, label) for key, label in opcoes]


def pill_button(
    text, selected=False, on_click=None, color_sel=ft.Colors.BLUE_500, icon=None
):
    """Cria botao estilo pill para filtros (market, sort, etc).

    Args:
        text: texto do botao
        selected: se True, aplica estilo de selecionado
        on_click: callback chamado no clique
        color_sel: cor quando selecionado
        icon: nome do icone flet (opcional)
    """
    return ft.Container(
        content=ft.Row(
            [
                *(
                    [
                        ft.Icon(
                            icon,
                            size=14,
                            color=ft.Colors.WHITE
                            if selected
                            else ft.Colors.BLUE_GREY_400,
                        )
                    ]
                    if icon
                    else []
                ),
                ft.Text(
                    text,
                    size=12,
                    weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                    color=ft.Colors.WHITE if selected else ft.Colors.BLUE_GREY_300,
                ),
            ],
            spacing=4,
            tight=True,
        ),
        bgcolor=color_sel
        if selected
        else ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_700),
        border=ft.border.all(
            1,
            color_sel
            if selected
            else ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_600),
        ),
        border_radius=20,
        padding=ft.Padding(left=14, top=7, right=14, bottom=7),
        on_click=on_click,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )
