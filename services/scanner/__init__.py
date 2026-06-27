"""Package services.scanner - motor de coleta e avaliacao de ativos.

API publica:
    from services.scanner import (
        # Classificacao
        classificar_por_codigo, codigo, normalizar_ativo, merge_por_codigo,
        BDR_SUFFIXES, EXCLUDED_SUFFIXES,
        # Catalogo (unificado)
        montar_catalogo, montar_catalogo_acoes, montar_catalogo_fiis, montar_catalogo_bdrs,
        # Volume
        calcular_volume_anomalo_semanal, VOLUME_SPIKE_MULTIPLIER, VOLUME_WEEK_CANDLES_B3,
        # Evaluator
        montar_resultado_sem_dados, avaliar_ativo_com_candles, calcular_qtd_candles_confluencia,
        # Chunks
        gerar_chunks_ativos, gerar_b3_chunks, B3_STREAM_LOTE_SIZE,
    )

Retrocompatibilidade:
    # Aliases com _prefix ainda funcionam:
    from services.scanner import (
        _classificar_por_codigo, _codigo, _normalizar_ativo, _merge_por_codigo,
        _montar_resultado_sem_dados, _avaliar_ativo_com_candles,
        _calcular_qtd_candles_confluencia,
    )

Arquitetura final (apos Fase 3):
- classification.py: classificacao por sufixo B3 (97 linhas)
- catalog_builder.py: montar_catalogo unificado (88 linhas)
- volume.py: deteccao de volume anomalo (61 linhas)
- evaluator.py: avaliacao de ativos com candles (276 linhas)
- chunks.py: geradores para UI progressiva (215 linhas)
"""
from services.scanner.classification import (
    classificar_por_codigo,
    codigo,
    normalizar_ativo,
    merge_por_codigo,
    BDR_SUFFIXES,
    EXCLUDED_SUFFIXES,
)
from services.scanner.catalog_builder import (
    montar_catalogo,
    montar_catalogo_acoes,
    montar_catalogo_fiis,
    montar_catalogo_bdrs,
)
from services.scanner.volume import (
    calcular_volume_anomalo_semanal,
    VOLUME_SPIKE_MULTIPLIER,
    VOLUME_WEEK_CANDLES_B3,
)
from services.scanner.evaluator import (
    montar_resultado_sem_dados,
    avaliar_ativo_com_candles,
    calcular_qtd_candles_confluencia,
)
from services.scanner.chunks import (
    gerar_chunks_ativos,
    gerar_b3_chunks,
    B3_STREAM_LOTE_SIZE,
)

# Retrocompatibilidade: codigos antigos usavam _prefix
# (services.scanner._classificar_por_codigo, etc)
_classificar_por_codigo = classificar_por_codigo
_codigo = codigo
_normalizar_ativo = normalizar_ativo
_merge_por_codigo = merge_por_codigo
_montar_resultado_sem_dados = montar_resultado_sem_dados
_avaliar_ativo_com_candles = avaliar_ativo_com_candles
_calcular_qtd_candles_confluencia = calcular_qtd_candles_confluencia

__all__ = [
    # Classificacao
    "classificar_por_codigo",
    "codigo",
    "normalizar_ativo",
    "merge_por_codigo",
    "BDR_SUFFIXES",
    "EXCLUDED_SUFFIXES",
    # Catalogo
    "montar_catalogo",
    "montar_catalogo_acoes",
    "montar_catalogo_fiis",
    "montar_catalogo_bdrs",
    # Volume
    "calcular_volume_anomalo_semanal",
    "VOLUME_SPIKE_MULTIPLIER",
    "VOLUME_WEEK_CANDLES_B3",
    # Evaluator
    "montar_resultado_sem_dados",
    "avaliar_ativo_com_candles",
    "calcular_qtd_candles_confluencia",
    # Chunks
    "gerar_chunks_ativos",
    "gerar_b3_chunks",
    "B3_STREAM_LOTE_SIZE",
    # Retrocompatibilidade
    "_classificar_por_codigo",
    "_codigo",
    "_normalizar_ativo",
    "_merge_por_codigo",
    "_montar_resultado_sem_dados",
    "_avaliar_ativo_com_candles",
    "_calcular_qtd_candles_confluencia",
]
