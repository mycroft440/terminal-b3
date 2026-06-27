"""Badges do card: codigo, PnL (carteira), setor, market cap."""
import flet as ft
from core.config import nomes_setores
import ui.flet_patches  # noqa: F401


def build_badges(
    dado: dict,
    state: dict,
    active_wallet,
    mc_data,
    codigo_ativo: str,
    preco_atual: float,
) -> ft.Row:
    """Constroi linha de badges do card.

    Badges incluidos:
    - Codigo do ativo (sempre)
    - PnL da carteira (se active_wallet tem preco_entrada e quantidade)
    - Setor (se ativo tem setor)
    - Categoria de market cap (Blue Chip, Mid Cap, etc) se mc_data['categoria']

    Args:
        dado: dict do ativo avaliado
        state: state global (com carteiras)
        active_wallet: nome da carteira ativa ou None
        mc_data: MarketCapInfo retornado por formatar_market_cap()
        codigo_ativo: codigo do ativo
        preco_atual: preco atual do ativo

    Returns:
        ft.Row com Container por badge
    """
    setor = dado["ativo"].get("setor")
    setor_nome = nomes_setores.get(setor, setor) if setor else ""
    badge_color = ft.Colors.BLUE_300
    if dado["ativo"].get("tipo") == "fiis":
        badge_color = ft.Colors.INDIGO_300

    badges_row = ft.Row(spacing=4, tight=True)

    # Codigo badge
    badges_row.controls.append(
        ft.Container(
            content=ft.Text(
                codigo_ativo, size=10, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_300
            ),
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_700),
            padding=ft.Padding(left=6, top=2, right=6, bottom=2),
            border_radius=6,
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.BLUE_GREY_600)),
        )
    )

    # PnL Badge (se carteira ativa com preco de entrada)
    if active_wallet and active_wallet in state["carteiras"]:
        ticker_data = state["carteiras"][active_wallet].get(codigo_ativo)
        if isinstance(ticker_data, dict):
            try:
                preco_entrada = float(ticker_data.get("preco_entrada") or 0.0)
            except (ValueError, TypeError):
                preco_entrada = 0.0

            if preco_entrada > 0 and preco_atual > 0:
                pnl_pct = ((preco_atual / preco_entrada) - 1) * 100
                pnl_cor = (
                    ft.Colors.GREEN_400
                    if pnl_pct > 0
                    else (ft.Colors.RED_400 if pnl_pct < 0 else ft.Colors.BLUE_GREY_400)
                )
                sinal_pnl = "+" if pnl_pct > 0 else ""

                try:
                    qtd = float(ticker_data.get("quantidade") or 0.0)
                except (ValueError, TypeError):
                    qtd = 0.0

                if qtd > 0:
                    pnl_valor = (preco_atual - preco_entrada) * qtd
                    txt_pnl = f"PnL: {sinal_pnl}{pnl_pct:.2f}% (R$ {pnl_valor:.2f})"
                else:
                    txt_pnl = f"PnL: {sinal_pnl}{pnl_pct:.2f}%"

                badges_row.controls.append(
                    ft.Container(
                        content=ft.Text(txt_pnl, size=9, weight=ft.FontWeight.BOLD, color=pnl_cor),
                        bgcolor=ft.Colors.with_opacity(0.1, pnl_cor),
                        padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                        border_radius=6,
                        border=ft.border.all(1, ft.Colors.with_opacity(0.2, pnl_cor)),
                    )
                )

    if setor:
        badges_row.controls.append(
            ft.Container(
                content=ft.Text(
                    setor_nome.upper(), size=9, color=badge_color, weight=ft.FontWeight.W_600
                ),
                bgcolor=ft.Colors.with_opacity(0.1, badge_color),
                border=ft.border.all(1, ft.Colors.with_opacity(0.2, badge_color)),
                padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                border_radius=6,
            )
        )

    if mc_data["categoria"]:
        badges_row.controls.append(
            ft.Container(
                content=ft.Text(
                    mc_data["categoria"], size=9, weight=ft.FontWeight.W_600, color=mc_data["color"]
                ),
                bgcolor=mc_data["bg"],
                padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                border_radius=6,
                border=ft.border.all(1, ft.Colors.with_opacity(0.2, mc_data["color"])),
            )
        )

    return badges_row
