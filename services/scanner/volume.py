"""
Deteccao de volume anomalo (spike) em series temporais de candles.

Usa referencia semanal: compara volume atual com media movel da semana
anterior equivalente para o timeframe. Se atual > media * 2.0, marca spike.
"""
import pandas as pd

# Multiplicador para deteccao de volume anomalo (2x a media semanal)
VOLUME_SPIKE_MULTIPLIER = 2.0

# Numero de candles equivalentes a 1 semana por timeframe
VOLUME_WEEK_CANDLES_B3 = {
    "1m": 2100,  # 5 pregoes x ~420 candles de 1 minuto
    "5m": 420,  # 5 pregoes x ~84 candles de 5 minutos
    "15m": 140,  # 5 pregoes x ~28 candles de 15 minutos
    "30m": 70,  # 5 pregoes x ~14 candles de 30 minutos
    "1h": 35,  # 5 pregoes x ~7 candles de 1 hora
    "1d": 5,  # 5 pregoes
    "1s": 4,  # media de semanas anteriores para candle semanal
    "1M": 3,  # fallback para candle mensal
}


def calcular_volume_anomalo_semanal(df_ativo, timeframe: str) -> bool:
    """Identifica picos de volume ('volume spike').

    Multiplicador = 2x a media da semana anterior equivalente.
    A media ignora o candle atual e usa a janela semanal disponivel para o timeframe.
    Se nao houver historico suficiente para uma semana completa, usa o historico
    disponivel como fallback, mantendo o calculo progressivo sem bloquear a
    exibicao dos cards.

    Args:
        df_ativo: DataFrame com coluna 'Volume'
        timeframe: '1d', '1s', '1m', '5m', etc.

    Returns:
        True se volume atual > 2x media semanal, False caso contrario.
    """
    if df_ativo is None or "Volume" not in df_ativo.columns:
        return False

    volumes = pd.to_numeric(df_ativo["Volume"], errors="coerce").dropna()
    if len(volumes) < 2:
        return False

    vol_atual = float(volumes.iloc[-1])
    historico = volumes.iloc[:-1]
    if historico.empty or vol_atual <= 0:
        return False

    referencia_velas = VOLUME_WEEK_CANDLES_B3.get(timeframe, 5)
    janela = min(referencia_velas, len(historico))
    if janela <= 0:
        return False

    vol_medio_semanal = float(historico.tail(janela).mean())
    return vol_medio_semanal > 0 and vol_atual > (
        vol_medio_semanal * VOLUME_SPIKE_MULTIPLIER
    )
