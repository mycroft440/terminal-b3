import time
import os
from typing import Optional
from diskcache import Cache

cache = Cache(os.path.join("dados", "yfinance_cache"))

# TTL inteligente por timeframe.
# Dados diários/semanais mudam poucas vezes ao dia -> cache longo.
# Dados intraday mudam rápido -> cache curto.
_TTL_POR_TIMEFRAME = {
    "1m": 60,  # 1 min
    "5m": 120,  # 2 min
    "15m": 180,  # 3 min
    "30m": 300,  # 5 min
    "1h": 600,  # 10 min
    # Diario/semanal: dados novos chegam 1x por dia (apos fechamento do pregao).
    # TTL de 6h evita re-downloads desnecessarios durante o dia. A logica em
    # requires_update_based_on_business_day() continua decidindo se os dados
    # em cache ja contemplam o ultimo dia util, entao atualizacoes reais
    # ainda acontecem quando novo candle fecha.
    "1d": 21600,  # 6 horas
    "1s": 21600,  # 6 horas
    "1M": 21600,  # 6 horas
}


def get_ttl(timeframe: str) -> int:
    """Retorna o TTL em segundos para um dado timeframe."""
    return _TTL_POR_TIMEFRAME.get(timeframe, 14400)


def cache_is_fresh(key: str, ttl: int) -> bool:
    """Verifica se uma chave no cache ainda está dentro do TTL."""
    ts = cache.get(f"{key}__ts")
    if ts is None:
        return False
    return (time.time() - ts) < ttl


def cache_set_with_ts(key: str, value, ttl: Optional[int] = None) -> None:
    """Salva valor no cache com timestamp de criação.
    O expire do diskcache é setado para 2x o TTL como safety net."""
    expire = ttl * 2 if ttl else None
    cache.set(key, value, expire=expire)
    cache.set(f"{key}__ts", time.time(), expire=expire)
