"""
Builders de catalogo de ativos por mercado (acoes, fiis, bdrs).

Funcao unificada montar_catalogo(cat, catalogo_brapi, market) substitui
3 funcoes duplicadas (montar_catalogo_acoes, _fiis, _bdrs) que tinham
logica identica exceto pelo criterio de classificacao.
"""
from typing import Literal

from services.scanner.classification import (
    classificar_por_codigo,
    codigo,
    normalizar_ativo,
    merge_por_codigo,
)

# Mapeamento: market (UI) -> (classificacao, tipo)
# market: valor do state["market"] (acoes, fiis, bdrs)
# classificacao: retorno de classificar_por_codigo (acao, fii, bdr)
# tipo: valor do campo "tipo" no dict do ativo (acoes, fiis, bdrs)
_MARKET_MAP = {
    "acoes": ("acao", "acoes"),
    "fiis": ("fii", "fiis"),
    "bdrs": ("bdr", "bdrs"),
}

MarketType = Literal["acoes", "fiis", "bdrs"]


def montar_catalogo(cat: list, catalogo_brapi: list, market: MarketType) -> list:
    """Monta o universo de ativos para um mercado especifico.

    Args:
        cat: lista de ativos do catalogo local (ativos.json)
        catalogo_brapi: lista de ativos vindos da API Brapi
        market: 'acoes', 'fiis' ou 'bdrs'

    Returns:
        Lista de ativos normalizados e deduplicados por codigo.
    """
    if market not in _MARKET_MAP:
        raise ValueError(
            f"market deve ser um de {list(_MARKET_MAP.keys())}, recebido: {market!r}"
        )

    classificacao, tipo = _MARKET_MAP[market]

    filtrados_catalogo = [
        normalizar_ativo(a, tipo)
        for a in cat
        if classificar_por_codigo(codigo(a)) == classificacao
    ]

    filtrados_brapi = [
        normalizar_ativo(a, tipo)
        for a in catalogo_brapi
        if classificar_por_codigo(codigo(a)) == classificacao
    ]

    return merge_por_codigo(filtrados_catalogo, filtrados_brapi)


# ─── Wrappers retrocompativeis ──────────────────────────────────────────────
# Mantem API antiga (montar_catalogo_acoes, etc) para nao quebrar codigo
# existente. Apenas delegam para a funcao unificada.

def montar_catalogo_acoes(cat: list, catalogo_brapi: list) -> list:
    """Monta o universo de acoes: codigos terminados em 3, 4, 5, 6, 7 ou 8.

    Wrapper retrocompativel para montar_catalogo(cat, catalogo_brapi, 'acoes').
    """
    return montar_catalogo(cat, catalogo_brapi, "acoes")


def montar_catalogo_fiis(cat: list, catalogo_brapi: list) -> list:
    """Monta o universo de FIIs/Units/ETFs: codigos terminados em 11.

    Wrapper retrocompativel para montar_catalogo(cat, catalogo_brapi, 'fiis').
    """
    return montar_catalogo(cat, catalogo_brapi, "fiis")


def montar_catalogo_bdrs(cat: list, catalogo_brapi: list) -> list:
    """Monta o universo de BDRs: codigos terminados em 31, 32, 33, 34, 35 ou 39.

    Wrapper retrocompativel para montar_catalogo(cat, catalogo_brapi, 'bdrs').
    """
    return montar_catalogo(cat, catalogo_brapi, "bdrs")
