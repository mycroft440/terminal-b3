"""
Geradores de chunks de ativos para renderizacao progressiva na UI.

gerar_b3_chunks: baixa dados em lotes de 50, avalia, entrega em sub-lotes de 25
gerar_chunks_ativos: orquestra por mercado (acoes/fiis/bdrs/todos) ou carteira

Estes generators sao consumidos pela UI (main_page.py) que faz yield de
resultados parciais para renderizar cards progressivamente sem travar.
"""
import logging

from core import catalog
from core.config import get_yfinance_params
from providers.brapi import fetch_brapi_assets, get_brapi_market_caps
from providers.yfinance_provider import fetch_market_data

from services.scanner.classification import merge_por_codigo
from services.scanner.catalog_builder import (
    montar_catalogo_acoes,
    montar_catalogo_bdrs,
    montar_catalogo_fiis,
)
from services.scanner.evaluator import (
    montar_resultado_sem_dados,
    avaliar_ativo_com_candles,
)

# Micro-lotes para permitir renderizacao progressiva na UI.
# Antes o app esperava baixar 50 tickers antes de exibir qualquer card.
B3_STREAM_LOTE_SIZE = 25

# Tamanho do lote de download do yfinance (otimizacao de I/O)
DOWNLOAD_LOTE_SIZE = 50


def gerar_b3_chunks(ativos_filtrados, timeframe, mms_periodos, rsi_ativo, stoch_ativo):
    """Baixa dados de ativos em lotes e avalia com indicadores.

    Generator que yield listas de resultados parciais (chunks) para permitir
    renderizacao progressiva na UI sem travar.

    Args:
        ativos_filtrados: lista de dicts de ativos (com ticker, codigo, etc)
        timeframe: '1d', '1s', etc
        mms_periodos: lista de periodos MMS (vazio = desativado)
        rsi_ativo: bool se RSI deve ser calculado
        stoch_ativo: bool se Stoch deve ser calculado

    Yields:
        list[dict]: resultados avaliados em sub-lotes de B3_STREAM_LOTE_SIZE
    """
    from services.cache import get_ttl

    tickers = [a["ticker"] for a in ativos_filtrados]
    sem_filtro = not mms_periodos and not rsi_ativo and not stoch_ativo
    period, interval = get_yfinance_params(timeframe, sem_filtro)

    render_lote_size = B3_STREAM_LOTE_SIZE
    market_caps = get_brapi_market_caps()
    ttl = get_ttl(timeframe)

    for i in range(0, len(tickers), DOWNLOAD_LOTE_SIZE):
        lote_tickers = tickers[i : i + DOWNLOAD_LOTE_SIZE]
        lote_ativos = ativos_filtrados[i : i + DOWNLOAD_LOTE_SIZE]
        lote_data = fetch_market_data(" ".join(lote_tickers), period, interval, ttl=ttl)

        if lote_data is None or lote_data.empty:
            logging.warning(
                f"[YFINANCE API] Lote com {len(lote_tickers)} ativos falhou e retornou vazio. "
                f"Ativos afetados (ex: {lote_tickers[0]}) marcados como SEM DADOS."
            )
            resultados = []
            for ativo in lote_ativos:
                ticker_base = ativo["ticker"].replace(".SA", "")
                mc = market_caps.get(ticker_base, 0) or 0
                resultados.append(montar_resultado_sem_dados(ativo, mc, sem_filtro))

                if len(resultados) >= render_lote_size:
                    yield resultados
                    resultados = []
            if resultados:
                yield resultados
            continue

        resultados = []
        for ativo in lote_ativos:
            ticker = ativo["ticker"]
            ticker_base = ticker.replace(".SA", "")
            mc = market_caps.get(ticker_base, 0) or 0

            essential_cols = ["Open", "High", "Low", "Close", "Volume"]
            if len(lote_tickers) == 1:
                # yfinance com group_by='ticker' para 1 ticker pode retornar MultiIndex
                if hasattr(lote_data.columns, "levels"):
                    try:
                        ticker_slice = lote_data[ticker]
                        avail_cols = [
                            c for c in essential_cols if c in ticker_slice.columns
                        ]
                        df_ativo = (
                            ticker_slice[avail_cols].copy() if avail_cols else None
                        )
                    except (KeyError, TypeError):
                        df_ativo = None
                elif all(c in lote_data.columns for c in essential_cols):
                    df_ativo = lote_data[essential_cols].copy()
                else:
                    df_ativo = lote_data.copy()
            else:
                if (
                    hasattr(lote_data.columns, "levels")
                    and ticker in lote_data.columns.levels[0]
                ):
                    ticker_slice = lote_data[ticker]
                    avail_cols = [
                        c for c in essential_cols if c in ticker_slice.columns
                    ]
                    df_ativo = ticker_slice[avail_cols].copy() if avail_cols else None
                elif all(c in lote_data.columns for c in essential_cols):
                    df_ativo = lote_data[essential_cols].copy()
                else:
                    df_ativo = None

            if df_ativo is None or df_ativo.empty:
                resultados.append(montar_resultado_sem_dados(ativo, mc, sem_filtro))
            else:
                resultados.append(
                    avaliar_ativo_com_candles(
                        ativo,
                        df_ativo,
                        timeframe,
                        mms_periodos,
                        rsi_ativo,
                        stoch_ativo,
                        mc=mc,
                        mercado="b3",
                    )
                )

            if len(resultados) >= render_lote_size:
                yield resultados
                resultados = []

        if resultados:
            yield resultados


def gerar_chunks_ativos(
    timeframe,
    market,
    sector,
    mms_periodos,
    rsi_ativo,
    stoch_ativo,
    bdr_ativo=False,
    exclude_tickers=None,
    wallet_tickers=None,
):
    """Orquestra geracao de chunks por mercado ou carteira.

    Args:
        timeframe: '1d', '1s', etc
        market: 'todos', 'acoes', 'fiis', 'bdrs'
        sector: 'all' ou setor especifico
        mms_periodos: lista de periodos MMS (vazio = desativado)
        rsi_ativo: bool se RSI deve ser calculado
        stoch_ativo: bool se Stoch deve ser calculado
        bdr_ativo: reservado para uso futuro
        exclude_tickers: set de tickers a excluir (ja carregados)
        wallet_tickers: lista de tickers de carteira (sobrepoe market/sector)

    Yields:
        list[dict]: resultados avaliados em chunks
    """
    # `bdr_ativo` reservado para uso futuro (filtros especificos de BDR)
    _ = bdr_ativo
    cat = catalog.carregar_catalogo()
    # Se uma carteira foi pedida, nao precisamos respeitar filtros de market e sector.
    catalogo_brapi = (
        fetch_brapi_assets()
        if market in {"todos", "acoes", "fiis", "bdrs"} or wallet_tickers
        else []
    )

    if exclude_tickers is None:
        exclude_tickers = set()

    if wallet_tickers is not None:
        # Puxa tudo junto
        todos = merge_por_codigo(
            montar_catalogo_acoes(cat, catalogo_brapi),
            montar_catalogo_bdrs(cat, catalogo_brapi),
            montar_catalogo_fiis(cat, catalogo_brapi),
        )
        # Filtra apenas os tickers exatos que o usuario quer na carteira
        ativos_filtrados = [
            a
            for a in todos
            if a["ticker"] in wallet_tickers or a.get("codigo") in wallet_tickers
        ]
        if ativos_filtrados:
            yield from gerar_b3_chunks(
                ativos_filtrados, timeframe, mms_periodos, rsi_ativo, stoch_ativo
            )
        return

    if market == "todos":
        catalogo = merge_por_codigo(
            montar_catalogo_acoes(cat, catalogo_brapi),
            montar_catalogo_bdrs(cat, catalogo_brapi),
            montar_catalogo_fiis(cat, catalogo_brapi),
        )
    elif market == "acoes":
        catalogo = montar_catalogo_acoes(cat, catalogo_brapi)
    elif market == "bdrs":
        catalogo = montar_catalogo_bdrs(cat, catalogo_brapi)
    elif market == "fiis":
        catalogo = montar_catalogo_fiis(cat, catalogo_brapi)
    else:
        catalogo = []  # market desconhecido - nao gera chunks

    # Filtragem por setor + exclusao de tickers + yield de chunks
    ativos_filtrados = [
        a
        for a in catalogo
        if (sector == "all" or a.get("setor") == sector)
        and a["ticker"] not in exclude_tickers
    ]
    if ativos_filtrados:
        yield from gerar_b3_chunks(
            ativos_filtrados, timeframe, mms_periodos, rsi_ativo, stoch_ativo
        )
