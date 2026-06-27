"""Package ui.cards - cards de ativos para a lista principal.

API publica:
    from ui.cards import create_card
    from ui.cards import compute_trend_style, TrendStyle  # uso avancado

Arquitetura (apos Fase 4.2):
- trend.py: computa TrendStyle (cor, icone, status) baseado em tendencia
- actions.py: coluna de acoes (favorito + ocultar/exibir)
- indicator_tags.py: tags MMS/RSI/STOCH/SemConfluencia/VolAnomalo
- badges.py: badges codigo/PnL/setor/market_cap
- variation.py: coluna direita (variacao %, status, tempo)
- note_preview.py: preview de nota tecnica (filled ou empty state)
- card.py: orquestrador create_card

Antes (Fase 4.1): cards.py monolitico de 579 linhas
Agora: 7 modulos com responsabilidade unica cada
"""
from ui.cards.trend import compute_trend_style, TrendStyle
from ui.cards.actions import build_actions
from ui.cards.indicator_tags import build_indicator_tags
from ui.cards.badges import build_badges
from ui.cards.variation import build_variation_col
from ui.cards.note_preview import build_note_preview
from ui.cards.card import create_card

__all__ = [
    # API principal
    "create_card",
    # Sub-componentes (uso avancado)
    "compute_trend_style",
    "TrendStyle",
    "build_actions",
    "build_indicator_tags",
    "build_badges",
    "build_variation_col",
    "build_note_preview",
]
