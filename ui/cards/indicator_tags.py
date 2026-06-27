"""Tags de indicadores tecnicos no card (MMS, RSI, STOCH, etc)."""
import flet as ft
import ui.flet_patches  # noqa: F401


def build_indicator_tags(dado: dict) -> ft.Row:
    """Constroi linha de tags de indicadores.

    Tags incluidas:
    - Uma tag por indicador ativo em dado['indicadores'] (MMS, RSI, STOCH)
    - 'Sem Confluência' se dado['semConfluencia']
    - 'Vol. Anômalo' se dado['volumeSpike']

    Args:
        dado: dict do ativo avaliado

    Returns:
        ft.Row com Container por tag
    """
    tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)

    if not dado.get("semFiltro"):
        for ind in dado.get("indicadores", []):
            ct = ft.Colors.BLUE_GREY_300
            if ind["nome"] == "MMS":
                ct = ft.Colors.BLUE_400
            if ind["nome"] == "RSI":
                ct = ft.Colors.GREEN_400
            if ind["nome"] == "STOCH":
                ct = ft.Colors.PURPLE_400
            is_up = ind["sinal"] == 1
            bg_ind = ft.Colors.with_opacity(
                0.08, ft.Colors.GREEN_500 if is_up else ft.Colors.RED_500
            )
            border_c = ft.Colors.with_opacity(
                0.2, ft.Colors.GREEN_500 if is_up else ft.Colors.RED_500
            )
            setinha = "▲" if is_up else "▼"
            tags_row.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(ind["nome"], color=ct, size=9, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                setinha,
                                color=ft.Colors.GREEN_400 if is_up else ft.Colors.RED_400,
                                size=9,
                            ),
                        ],
                        spacing=2,
                        tight=True,
                    ),
                    bgcolor=bg_ind,
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                    border_radius=6,
                    border=ft.border.all(1, border_c),
                )
            )

    if dado.get("semConfluencia"):
        tags_row.controls.append(
            ft.Container(
                content=ft.Text(
                    "Sem Confluência",
                    color=ft.Colors.BLUE_GREY_400,
                    size=9,
                    weight=ft.FontWeight.W_500,
                ),
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.BLUE_GREY_500),
                padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                border_radius=6,
                border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.BLUE_GREY_500)),
            )
        )

    if dado.get("volumeSpike"):
        tags_row.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE_400, size=11),
                        ft.Text(
                            "Vol. Anômalo",
                            color=ft.Colors.ORANGE_400,
                            size=9,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                ),
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ORANGE_500),
                padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                border_radius=6,
                border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ORANGE_500)),
            )
        )

    return tags_row
