"""Coluna direita do card: variacao %, status tendencia, tempo."""
import flet as ft
from ui.cards.trend import TrendStyle
import ui.flet_patches  # noqa: F401


def build_variation_col(dado: dict, trend: TrendStyle) -> ft.Column:
    """Constroi coluna direita do card com variacao e status.

    Elementos:
    - Variacao % grande (22pt) colorida por sinal
    - Texto 'atualizado DD-MM-YY' se dado['dataVariacao']
    - Container com icone + status (TEND ALTA, DIÁRIO, SEM DADOS, etc)
    - Texto com tempo de tendencia (ex: '3 dias')

    Args:
        dado: dict do ativo avaliado
        trend: TrendStyle retornado por compute_trend_style()

    Returns:
        ft.Column alinhada a direita (CrossAxisAlignment.END)
    """
    variacao_val = dado.get("variacao", 0)
    var_sinal_str = "+" if variacao_val > 0 else ""
    cor_variacao = (
        ft.Colors.GREEN_400
        if variacao_val > 0
        else (ft.Colors.RED_400 if variacao_val < 0 else ft.Colors.BLUE_GREY_300)
    )

    return ft.Column(
        [
            ft.Text(
                f"{var_sinal_str}{variacao_val:.2f}%",
                size=22,
                weight=ft.FontWeight.W_800,
                color=cor_variacao,
            ),
            ft.Text(
                f"atualizado {dado.get('dataVariacao', '')}",
                size=9,
                color=ft.Colors.BLUE_GREY_600,
                italic=True,
            )
            if dado.get("dataVariacao")
            else ft.Container(height=0, width=0, padding=0, margin=0),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(trend.icone_seta, size=9, color=trend.cor_texto),
                        ft.Text(
                            trend.texto_status,
                            size=9,
                            weight=ft.FontWeight.W_700,
                            color=trend.cor_texto,
                        ),
                    ],
                    spacing=3,
                    tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                border=ft.border.all(1, ft.Colors.with_opacity(0.25, trend.cor_texto)),
                bgcolor=ft.Colors.with_opacity(0.12, trend.cor_gradiente),
                padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                border_radius=6,
            ),
            ft.Text(
                dado.get("tempoTendencia", ""),
                size=10,
                color=ft.Colors.BLUE_GREY_600,
                weight=ft.FontWeight.W_500,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        spacing=4,
    )
