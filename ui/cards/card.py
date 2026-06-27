"""Orquestrador do card de ativo.

Reune sub-componentes (trend, actions, indicator_tags, badges, variation,
note_preview) em um ft.Container final com gradient baseado na tendencia.
"""
import flet as ft
from core.config import formatar_market_cap
from ui.theme import AppColors
from ui.cards.trend import compute_trend_style
from ui.cards.actions import build_actions
from ui.cards.indicator_tags import build_indicator_tags
from ui.cards.badges import build_badges
from ui.cards.variation import build_variation_col
from ui.cards.note_preview import build_note_preview
import ui.flet_patches  # noqa: F401


def create_card(
    dado,
    state,
    page,
    render_list,
    open_add_carteira_dialog,
    open_remove_carteira_dialog,
    open_notes_dialog,
    save_ocultos,
    active_wallet=None,
):
    """Cria card de ativo para exibicao na lista principal.

    Args:
        dado: dict do ativo avaliado (gerado por services.scanner.avaliar_ativo_com_candles)
        state: state global do app (carteiras, ocultos, anotacoes)
        page: instancia de ft.Page
        render_list: callback para re-renderizar lista apos mutacoes de state
        open_add_carteira_dialog: callback(ticker, preco) para abrir dialog de add carteira
        open_remove_carteira_dialog: callback(ticker, carteiras) para remover de carteira
        open_notes_dialog: callback(ticker) para abrir bloco de notas
        save_ocultos: callback para persistir state['ocultos']
        active_wallet: nome da carteira ativa (None se nenhuma)

    Returns:
        ft.Container com o card completo (3 colunas: info + nota + variacao)
    """
    # Computa estilo de tendencia (cor, icone, status)
    trend = compute_trend_style(dado)

    # Identificadores do ativo
    codigo_ativo = dado["ativo"].get("codigo") or dado["ativo"].get("ticker") or ""
    is_fav = any(codigo_ativo in lst for lst in state["carteiras"].values())
    is_oculto = codigo_ativo in state.get("ocultos", [])

    # Dados formatados
    mc_data = formatar_market_cap(dado.get("marketCap", 0))
    valor_texto = mc_data["texto"]
    valor_label = "Market Cap"

    try:
        preco_atual = float(dado.get("fechamento") or 0.0)
    except (ValueError, TypeError):
        preco_atual = 0.0

    # Constroi sub-componentes via funcoes especializadas
    actions_col = build_actions(
        codigo_ativo, is_fav, is_oculto, preco_atual, state,
        active_wallet, open_add_carteira_dialog, open_remove_carteira_dialog,
        save_ocultos, render_list,
    )
    tags_row = build_indicator_tags(dado)
    badges_row = build_badges(dado, state, active_wallet, mc_data, codigo_ativo, preco_atual)
    right_col = build_variation_col(dado, trend)
    middle_col = build_note_preview(state, codigo_ativo, open_notes_dialog)

    # Coluna esquerda: acoes + info principal (nome, badges, mc, tags)
    left_col = ft.Row(
        [
            actions_col,
            ft.Column(
                [
                    ft.Text(
                        dado["ativo"].get("nome", ""),
                        size=15,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    badges_row,
                    ft.Text(
                        f"{valor_label}: {valor_texto}",
                        size=10,
                        color=ft.Colors.BLUE_GREY_500,
                        weight=ft.FontWeight.W_400,
                    ),
                    tags_row,
                ],
                spacing=3,
                expand=True,
            ),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    # Container final do card
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(content=left_col, expand=10),
                ft.Container(content=middle_col, expand=6, padding=ft.Padding(left=10, right=10)),
                ft.Container(content=right_col, width=140),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(left=12, top=12, right=16, bottom=12),
        border_radius=12,
        bgcolor=AppColors.BG_CARD,
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.BLUE_GREY_600)),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[ft.Colors.with_opacity(0.06, trend.cor_texto), ft.Colors.TRANSPARENT],
        ),
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )
