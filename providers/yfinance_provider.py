import yfinance as yf
import pandas as pd
import datetime
import pytz
import threading
import time
import logging
from services.cache import cache, cache_is_fresh, cache_set_with_ts


def requires_update_based_on_business_day(df):
    if df is None or df.empty:
        return True

    sp_tz = pytz.timezone("America/Sao_Paulo")
    now = pd.Timestamp.now(tz=sp_tz)

    last_dt = df.index.max()
    if pd.isna(last_dt):
        return True

    if getattr(last_dt, "tzinfo", None) is None:
        try:
            last_dt = last_dt.tz_localize("America/Sao_Paulo")
        except Exception:
            pass
    else:
        try:
            last_dt = last_dt.tz_convert("America/Sao_Paulo")
        except Exception:
            pass

    if not hasattr(last_dt, "date"):
        return True

    last_date = last_dt.date()

    if now.weekday() == 5:  # Sab
        expected = (now - datetime.timedelta(days=1)).date()
    elif now.weekday() == 6:  # Dom
        expected = (now - datetime.timedelta(days=2)).date()
    elif now.hour < 10:
        if now.weekday() == 0:
            expected = (now - datetime.timedelta(days=3)).date()
        else:
            expected = (now - datetime.timedelta(days=1)).date()
    else:
        expected = now.date()

    if last_date < expected:
        return True

    market_open = (now.weekday() < 5) and (10 <= now.hour < 18)
    if not market_open:
        return False

    return "CHECK_TTL"


_yf_semaphore = threading.Semaphore(3)

_negative_cache_lock = threading.Lock()
_NEGATIVE_CACHE: dict[str, float] = {}


def _yf_download_with_backoff(
    tickers, period=None, start=None, end=None, interval="1d", max_retries=3
):
    now = time.time()
    with _negative_cache_lock:
        if tickers in _NEGATIVE_CACHE:
            if now - _NEGATIVE_CACHE[tickers] < 86400:  # 24h
                logging.warning(
                    f"[YFinance] Pulando download (Cache Negativo) para: {tickers[:30]}"
                )
                return None
            else:
                del _NEGATIVE_CACHE[tickers]

    for attempt in range(max_retries):
        try:
            if start and end:
                data = yf.download(
                    tickers,
                    start=start,
                    end=end,
                    interval=interval,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                )
            else:
                data = yf.download(
                    tickers,
                    period=period,
                    interval=interval,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                )

            # yfinance sometimes returns an empty DataFrame if rate-limited without raising HTTPError
            if data is not None and not data.empty:
                # Normaliza MultiIndex columns para single-ticker downloads
                # yfinance com group_by='ticker' cria MultiIndex (Ticker, Price)
                # mesmo para 1 ticker, causando KeyError: 'Close' no cache.
                if isinstance(data.columns, pd.MultiIndex):
                    if " " not in tickers.strip():
                        # Single ticker: extrair sub-DataFrame pelo nome do ticker
                        ticker_name = tickers.strip()
                        try:
                            data = data[ticker_name]
                        except (KeyError, TypeError):
                            # Fallback: tenta dropar o nível do ticker
                            data.columns = data.columns.droplevel(0)
                return data

            # If empty, we might have hit a silent rate limit, or the ticker just doesn't have data.
            # We'll do a small backoff and retry just in case it's a silent limit.
            if attempt < max_retries - 1:
                time.sleep((2**attempt))

        except Exception as e:
            err_msg = str(e).lower()
            if (
                "429" in err_msg
                or "too many requests" in err_msg
                or "rate limit" in err_msg
            ):
                wait_time = (2**attempt) * 2
                logging.warning(
                    f"[YFinance] Rate limit 429 atingido. Retentando em {wait_time}s... (Tentativa {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logging.error(f"[YFinance] Erro ao baixar {tickers[:30]}: {e}")
                time.sleep(1)

    logging.error(
        f"[YFinance] Download falhou para {tickers[:30]} após {max_retries} tentativas. Inserindo no Cache Negativo (24h)."
    )
    with _negative_cache_lock:
        _NEGATIVE_CACHE[tickers] = time.time()
    return None


def fetch_market_data(tickers_str, period, interval, ttl=None):
    cache_key = f"market_data_{tickers_str}_{period}_{interval}"
    cached_df = cache.get(cache_key)
    yf_interval = interval  # 4h removido da UI; interval passado direto para yfinance

    fresh_by_time = cache_is_fresh(cache_key, ttl) if ttl else False
    status = (
        requires_update_based_on_business_day(cached_df)
        if cached_df is not None
        else True
    )

    # Decisão de Cache
    is_fresh = False
    force_sync_update = False

    if status is False:
        is_fresh = True
    elif status == "CHECK_TTL":
        is_fresh = fresh_by_time
    else:
        # Completamente desatualizado (falta o último dia útil)
        if fresh_by_time:
            # Já tentamos baixar recentemente, mas o provedor não tem a data. Retorna cache pra não travar.
            is_fresh = True
        else:
            is_fresh = False
            force_sync_update = True

    # Se temos cache e consideramos fresco ou se não há mais o que fazer
    if cached_df is not None and not cached_df.empty and is_fresh:
        logging.info(
            f"[CACHE INFO] Banco local preparado priorizado ({interval}). Ignorando rede para {tickers_str[:30]}."
        )
        return cached_df

    # Função interna para o incremento de dados (usada no modo síncrono e assíncrono)
    def _do_incremental_update():
        if not _yf_semaphore.acquire(blocking=False):
            logging.info(
                f"[CACHE INFO] Concorrência máxima atingida. Adiada a att de {tickers_str[:30]}"
            )
            return None
        try:
            last_date = cached_df.index.max()
            now = pd.Timestamp.now(tz=last_date.tz)
            delta_days = (now - last_date).days

            if delta_days <= 0:
                recent_period_days = 2
            else:
                recent_period_days = delta_days + 2

            if interval == "1m" or yf_interval == "1m":
                recent_period_days = min(recent_period_days, 7)
            elif interval in ["5m", "15m", "30m"] or yf_interval in [
                "5m",
                "15m",
                "30m",
            ]:
                recent_period_days = min(recent_period_days, 60)
            elif interval == "1h" or yf_interval == "1h":
                recent_period_days = min(recent_period_days, 720)

            recent_period = f"{recent_period_days}d"

            logging.info(
                f"[CACHE INFO] Atualização Incremental (delta: {delta_days} dias) para {tickers_str[:30]}..."
            )
            recent_data = _yf_download_with_backoff(
                tickers_str, period=recent_period, interval=yf_interval
            )

            if recent_data is not None and not recent_data.empty:
                # Reconcilia formato de colunas entre cache e dados novos
                cached_is_multi = isinstance(cached_df.columns, pd.MultiIndex)
                recent_is_multi = isinstance(recent_data.columns, pd.MultiIndex)
                if cached_is_multi and not recent_is_multi:
                    # Cache antigo com MultiIndex, dados novos flat -> flatten cache
                    ticker_name = tickers_str.strip()
                    try:
                        new_cached_df = (
                            cached_df[ticker_name].copy()
                            if " " not in ticker_name
                            else cached_df.copy()
                        )
                    except (KeyError, TypeError):
                        new_cached_df = cached_df.copy()
                        new_cached_df.columns = new_cached_df.columns.droplevel(0)
                elif not cached_is_multi and recent_is_multi:
                    # Cache flat, dados novos com MultiIndex -> flatten novos
                    ticker_name = tickers_str.strip()
                    try:
                        recent_data = (
                            recent_data[ticker_name]
                            if " " not in ticker_name
                            else recent_data
                        )
                    except (KeyError, TypeError):
                        recent_data.columns = recent_data.columns.droplevel(0)
                    new_cached_df = cached_df.copy()
                else:
                    new_cached_df = cached_df.copy()

                missing_cols = recent_data.columns.difference(new_cached_df.columns)
                if not missing_cols.empty:
                    for col in missing_cols:
                        new_cached_df[col] = pd.NA

                # Timezone safety before update/concat
                tz_new = getattr(new_cached_df.index, "tz", None)
                tz_rec = getattr(recent_data.index, "tz", None)
                if tz_rec is not None and tz_new is None:
                    new_cached_df.index = new_cached_df.index.tz_localize(tz_rec)
                elif tz_rec is None and tz_new is not None:
                    recent_data.index = recent_data.index.tz_localize(tz_new)
                elif tz_rec is not None and tz_new is not None and tz_rec != tz_new:
                    recent_data.index = recent_data.index.tz_convert(tz_new)

                new_cached_df.update(recent_data)
                new_indices = recent_data.index.difference(new_cached_df.index)
                if not new_indices.empty:
                    new_cached_df = pd.concat(
                        [new_cached_df, recent_data.loc[new_indices]]
                    )
                new_cached_df.sort_index(inplace=True)

                cache_set_with_ts(cache_key, new_cached_df, ttl)
                logging.info(
                    f"[CACHE INFO] Atualização Concluída para {tickers_str[:30]}..."
                )
                return new_cached_df
            else:
                # Yahoo falhou ou não tem dado. Atualiza TS do cache para não martelar.
                cache_set_with_ts(cache_key, cached_df, ttl)
                return cached_df
        except Exception as e:
            logging.error(f"[CACHE ERRO] Falha na atualização incremental: {e}")
            return cached_df
        finally:
            _yf_semaphore.release()

    # Se temos cache, mas precisamos atualizar (está velho ou TTL expirou)
    if cached_df is not None and not cached_df.empty:
        if force_sync_update:
            updated_df = _do_incremental_update()
            if updated_df is not None and not updated_df.empty:
                return updated_df
            return cached_df
        else:
            # Só passou do TTL (mas tem dia útil). Atualiza no background para ser rápido na UI.
            t = threading.Thread(target=_do_incremental_update)
            t.daemon = True
            t.start()
            logging.info(
                f"[CACHE FAST] Exibindo dados locais instantaneamente enquanto atualiza online para {tickers_str[:30]}"
            )
            return cached_df

    # Download completo se não tem cache ou o incremental falhou
    try:
        data = _yf_download_with_backoff(
            tickers_str, period=period, interval=yf_interval
        )
        if data is not None and not data.empty:
            cache_set_with_ts(cache_key, data, ttl)
        return data
    except Exception:
        return None


def get_historical_price(ticker, date_str):
    from services.cache import cache

    cache_key = f"hist_price_{ticker}_{date_str}"
    cached_price = cache.get(cache_key)
    if cached_price is not None:
        return cached_price

    try:
        start = pd.to_datetime(date_str)
        end = start + pd.Timedelta(days=7)  # Look ahead to find the first trading day
        df = _yf_download_with_backoff(
            ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d")
        )
        if not df.empty:
            df = df.dropna(subset=["Close"])
            if not df.empty:
                price = float(df["Close"].iloc[0])
                if price > 0:
                    cache.set(cache_key, price, expire=None)  # Never expires
                    return price
    except Exception as e:
        print(f"Erro ao buscar preco historico de {ticker} em {date_str}: {e}")
    return None
