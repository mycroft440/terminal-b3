"""
Avaliacao de ativos com candles OHLCV.

Funcoes:
- montar_resultado_sem_dados: cria dict padrao para ativos sem dados
- calcular_qtd_candles_confluencia: conta candles consecutivos alinhados
- avaliar_ativo_com_candles: avaliacao completa (variacao, indicadores,
  tendencia, confluencia, volume spike, qtd candles)

Retornam dicts em formato compativel com b3_evaluated_cache.json (camelCase):
isAlta, qtdCandles, semFiltro, semDados, semConfluencia, tempoTendencia,
marketCap, volumeSpike, dataVariacao.
"""
import math
import pandas as pd

from core.config import formatar_tendencia_recente
from core.indicators import calcular_indicadores, verificar_confluencia
from services.scanner.volume import calcular_volume_anomalo_semanal


def montar_resultado_sem_dados(ativo: dict, mc: float = 0, sem_filtro: bool = False) -> dict:
    """Cria dict padrao para ativo sem dados de mercado.

    Formato compativel com cache b3_evaluated_cache.json (camelCase).
    """
    return {
        "ativo": ativo,
        "fechamento": 0.0,
        "variacao": 0.0,
        "variacao_7d": 0.0,
        "variacao_30d": 0.0,
        "isAlta": True,
        "indicadores": [],
        "semFiltro": sem_filtro,
        "semDados": True,
        "qtdCandles": 0,
        "tempoTendencia": "Sem dados de mercado",
        "tendencia": "neutra",
        "marketCap": mc,
        "volumeSpike": False,
        "dataVariacao": "",
    }


def calcular_qtd_candles_confluencia(
    df_ativo, timeframe, tendencia, mms_periodos, rsi_ativo, stoch_ativo
) -> int:
    """Conta candles consecutivos alinhados com a tendencia atual.

    Limita busca a 60 candles para tras (performance).
    """
    qtd_candles = 1
    max_lookback = 60
    n = len(df_ativo)
    start_j = n - 2
    end_j = max(start_j - max_lookback, -1)

    for j in range(start_j, end_j, -1):
        row = df_ativo.iloc[j]
        c_p = float(row["Close"])
        s_mms, s_rsi, s_stoch = verificar_confluencia(
            row, mms_periodos, rsi_ativo, stoch_ativo, c_p
        )
        if mms_periodos:
            c_alta = s_mms == 1
            c_baixa = s_mms == -1
        else:
            c_alta = c_baixa = True
            if rsi_ativo and s_rsi != 1:
                c_alta = False
            if rsi_ativo and s_rsi != -1:
                c_baixa = False
            if stoch_ativo and s_stoch != 1:
                c_alta = False
            if stoch_ativo and s_stoch != -1:
                c_baixa = False

        t_antiga = "alta" if c_alta else ("baixa" if c_baixa else "nenhuma")
        if t_antiga == tendencia:
            qtd_candles += 1
        else:
            break
    return qtd_candles


def avaliar_ativo_com_candles(
    ativo, df_ativo, timeframe, mms_periodos, rsi_ativo, stoch_ativo, mc=0, mercado="b3"
) -> dict:
    """Avalia ativo com candles: variacao, indicadores, tendencia, confluencia.

    Args:
        ativo: dict do ativo (codigo, ticker, nome, etc)
        df_ativo: DataFrame OHLCV com colunas Open, High, Low, Close, Volume
        timeframe: '1d', '1s', '1m', etc
        mms_periodos: lista de periodos MMS (vazio = desativado)
        rsi_ativo: bool se RSI deve ser calculado
        stoch_ativo: bool se Stoch deve ser calculado
        mc: market cap (para repassar ao resultado)
        mercado: reservado para futuro (B3 vs cripto)

    Returns:
        Dict em formato compativel com cache (camelCase keys).
    """
    # `mercado` reservado para diferenciacao B3 x cripto em futuras extensoes
    _ = mercado
    sem_filtro = not mms_periodos and not rsi_ativo and not stoch_ativo

    df_ativo.dropna(subset=["Close"], inplace=True)
    if df_ativo.empty or len(df_ativo) < 2:
        return montar_resultado_sem_dados(ativo, mc, sem_filtro)

    close_price = float(df_ativo["Close"].iloc[-1])
    prev_close = float(df_ativo["Close"].iloc[-2])
    if prev_close == 0 or math.isnan(close_price) or math.isnan(prev_close):
        return montar_resultado_sem_dados(ativo, mc, sem_filtro)

    try:
        from datetime import datetime

        if "Timestamp" in df_ativo.columns:
            ts = df_ativo["Timestamp"].iloc[-1]
            data_str = datetime.fromtimestamp(ts / 1000).strftime("%d-%m-%y")
        else:
            last_date = df_ativo.index[-1]
            if timeframe in ("1s", "1M"):
                now = datetime.now()
                delta_dias = (
                    (now - last_date.to_pydatetime().replace(tzinfo=None)).days
                    if hasattr(last_date, "to_pydatetime")
                    else (now - last_date).days
                )
                max_delta = 7 if timeframe == "1s" else 31
                if 0 <= delta_dias < max_delta:
                    data_str = now.strftime("%d-%m-%y")
                else:
                    data_str = last_date.strftime("%d-%m-%y")
            else:
                data_str = last_date.strftime("%d-%m-%y")
    except Exception:
        data_str = ""

    # Calculo correto da "Variacao de Hoje" (Variacao Diaria)
    variacao = 0.0
    variacao_7d = 0.0
    variacao_30d = 0.0
    try:
        dates = pd.to_datetime(
            df_ativo["Timestamp"] if "Timestamp" in df_ativo.columns else df_ativo.index
        ).dt.date
        current_date = dates.iloc[-1]

        if timeframe in ["1m", "5m", "15m", "30m", "1h"]:
            prev_days_mask = dates < current_date
            if prev_days_mask.any():
                valid_prev_closes = df_ativo["Close"][prev_days_mask].dropna()
                if not valid_prev_closes.empty:
                    real_prev_close = float(valid_prev_closes.iloc[-1])
                    if real_prev_close > 0:
                        variacao = (
                            (close_price - real_prev_close) / real_prev_close
                        ) * 100
            else:
                current_date_mask = dates == current_date
                first_open_today = float(df_ativo["Open"][current_date_mask].iloc[0])
                if first_open_today > 0:
                    variacao = (
                        (close_price - first_open_today) / first_open_today
                    ) * 100
        else:
            if prev_close > 0:
                variacao = ((close_price - prev_close) / prev_close) * 100

        def get_price_n_days_ago(n):
            import datetime

            target_date = current_date - datetime.timedelta(days=n)
            mask = dates <= target_date
            valid_closes = df_ativo["Close"][mask].dropna()
            if not valid_closes.empty:
                return float(valid_closes.iloc[-1])
            all_closes = df_ativo["Close"].dropna()
            if not all_closes.empty:
                first_date = (
                    pd.to_datetime(df_ativo.index[0]).date()
                    if not hasattr(df_ativo.index[0], "date")
                    else df_ativo.index[0].date()
                )
                dias_disponiveis = (current_date - first_date).days
                if dias_disponiveis >= n // 2:
                    return float(all_closes.iloc[0])
            return 0.0

        p_7d = get_price_n_days_ago(7)
        if p_7d > 0:
            variacao_7d = ((close_price - p_7d) / p_7d) * 100

        p_30d = get_price_n_days_ago(30)
        if p_30d > 0:
            variacao_30d = ((close_price - p_30d) / p_30d) * 100
    except Exception:
        if prev_close > 0:
            variacao = ((close_price - prev_close) / prev_close) * 100

    tem_volume_alto = calcular_volume_anomalo_semanal(df_ativo, timeframe)

    try:
        df_ativo = calcular_indicadores(df_ativo, mms_periodos, rsi_ativo, stoch_ativo)
        sinal_mms, sinal_rsi, sinal_stoch = verificar_confluencia(
            df_ativo.iloc[-1], mms_periodos, rsi_ativo, stoch_ativo, close_price
        )
    except Exception:
        sinal_mms, sinal_rsi, sinal_stoch = 0, 0, 0

    confluencia_alta, confluencia_baixa = True, True
    indicadores_avaliados = []

    if mms_periodos:
        confluencia_alta = sinal_mms == 1
        confluencia_baixa = sinal_mms == -1
        indicadores_avaliados.append({"nome": "MMS", "sinal": sinal_mms})
        if rsi_ativo:
            indicadores_avaliados.append({"nome": "RSI", "sinal": sinal_rsi})
        if stoch_ativo:
            indicadores_avaliados.append({"nome": "STOCH", "sinal": sinal_stoch})
    else:
        if rsi_ativo:
            if sinal_rsi != 1:
                confluencia_alta = False
            if sinal_rsi != -1:
                confluencia_baixa = False
            indicadores_avaliados.append({"nome": "RSI", "sinal": sinal_rsi})
        if stoch_ativo:
            if sinal_stoch != 1:
                confluencia_alta = False
            if sinal_stoch != -1:
                confluencia_baixa = False
            indicadores_avaliados.append({"nome": "STOCH", "sinal": sinal_stoch})

    tem_confluencia = sem_filtro or confluencia_alta or confluencia_baixa
    if confluencia_alta:
        tendencia = "alta"
    elif confluencia_baixa:
        tendencia = "baixa"
    else:
        tendencia = "alta" if variacao >= 0 else "baixa"

    qtd_candles = 1
    if not sem_filtro and tem_confluencia:
        qtd_candles = calcular_qtd_candles_confluencia(
            df_ativo, timeframe, tendencia, mms_periodos, rsi_ativo, stoch_ativo
        )

    tempo = (
        formatar_tendencia_recente(qtd_candles, timeframe, tendencia)
        if tem_confluencia
        else "Sem confluência; exibindo variação"
    )

    return {
        "ativo": ativo,
        "fechamento": float(df_ativo["Close"].iloc[-1]) if not df_ativo.empty else 0.0,
        "variacao": variacao,
        "variacao_7d": variacao_7d,
        "variacao_30d": variacao_30d,
        "isAlta": tendencia == "alta",
        "indicadores": indicadores_avaliados,
        "semFiltro": sem_filtro,
        "semConfluencia": not tem_confluencia,
        "qtdCandles": qtd_candles,
        "tempoTendencia": tempo,
        "tendencia": tendencia,
        "marketCap": mc,
        "volumeSpike": tem_volume_alto,
        "dataVariacao": data_str,
    }
