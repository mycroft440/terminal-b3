"""Providers module - integracoes externas (brapi, yfinance).

API publica:
    from providers import (
        # Brapi
        fetch_brapi_assets, get_brapi_market_caps,
        # YFinance
        fetch_market_data, get_historical_price,
    )
"""
from providers.brapi import fetch_brapi_assets, get_brapi_market_caps
from providers.yfinance_provider import fetch_market_data, get_historical_price

__all__ = [
    # Brapi
    "fetch_brapi_assets",
    "get_brapi_market_caps",
    # YFinance
    "fetch_market_data",
    "get_historical_price",
]
