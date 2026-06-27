"""Services module - scanner, cache e background service.

API publica:
    from services import (
        # Scanner
        gerar_chunks_ativos, gerar_b3_chunks,
        montar_catalogo_acoes, montar_catalogo_fiis, montar_catalogo_bdrs,
        # Cache
        cache, get_ttl, cache_is_fresh, cache_set_with_ts,
    )
"""
from services.scanner import (
    gerar_chunks_ativos,
    gerar_b3_chunks,
    montar_catalogo_acoes,
    montar_catalogo_fiis,
    montar_catalogo_bdrs,
)
from services.cache import cache, get_ttl, cache_is_fresh, cache_set_with_ts

__all__ = [
    # Scanner
    "gerar_chunks_ativos",
    "gerar_b3_chunks",
    "montar_catalogo_acoes",
    "montar_catalogo_fiis",
    "montar_catalogo_bdrs",
    # Cache
    "cache",
    "get_ttl",
    "cache_is_fresh",
    "cache_set_with_ts",
]
