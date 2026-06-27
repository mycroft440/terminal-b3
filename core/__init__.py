"""Core module - configuracoes, catalogo, indicadores, modelos e paths.

API publica:
    from core import (
        # Config
        SETORES_ACOES, SETORES_FIIS, nomes_setores,
        formatar_market_cap, get_yfinance_params, formatar_tendencia_recente,
        # Catalog
        carregar_catalogo,
        # Indicators
        calcular_indicadores, verificar_confluencia,
        # Models (tipados)
        Ativo, ResultadoAvaliacao, PosicaoCarteira, Anotacao,
        MarketCapInfo, UIState, IndicadorSinal,
        MarketType, Timeframe, AssetType, TrendDirection, IndicatorName,
        # Paths
        BASE_DIR, DADOS_DIR, CARTEIRAS_DIR, ANOTACOES_DIR,
        IMAGES_DIR, ASSETS_DIR, ATIVOS_PATH, ensure_data_dirs,
    )
"""
from core.config import (
    SETORES_ACOES,
    SETORES_FIIS,
    nomes_setores,
    formatar_market_cap,
    get_yfinance_params,
    formatar_tendencia_recente,
)
from core.catalog import carregar_catalogo
from core.indicators import calcular_indicadores, verificar_confluencia
from core.models import (
    Ativo,
    ResultadoAvaliacao,
    PosicaoCarteira,
    Anotacao,
    MarketCapInfo,
    UIState,
    IndicadorSinal,
    MarketType,
    Timeframe,
    AssetType,
    TrendDirection,
    IndicatorName,
)
from core.paths import (
    BASE_DIR,
    DADOS_DIR,
    CARTEIRAS_DIR,
    ANOTACOES_DIR,
    IMAGES_DIR,
    ASSETS_DIR,
    ATIVOS_PATH,
    ensure_data_dirs,
)

__all__ = [
    # Config
    "SETORES_ACOES",
    "SETORES_FIIS",
    "nomes_setores",
    "formatar_market_cap",
    "get_yfinance_params",
    "formatar_tendencia_recente",
    # Catalog
    "carregar_catalogo",
    # Indicators
    "calcular_indicadores",
    "verificar_confluencia",
    # Models
    "Ativo",
    "ResultadoAvaliacao",
    "PosicaoCarteira",
    "Anotacao",
    "MarketCapInfo",
    "UIState",
    "IndicadorSinal",
    "MarketType",
    "Timeframe",
    "AssetType",
    "TrendDirection",
    "IndicatorName",
    # Paths
    "BASE_DIR",
    "DADOS_DIR",
    "CARTEIRAS_DIR",
    "ANOTACOES_DIR",
    "IMAGES_DIR",
    "ASSETS_DIR",
    "ATIVOS_PATH",
    "ensure_data_dirs",
]
