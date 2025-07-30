import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

import yfinance as yf

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)


def _cache_file(ticker: str, date: Optional[str] = None) -> Path:
    date = date or datetime.today().strftime("%Y-%m-%d")
    safe_ticker = ticker.replace("/", "_")
    return CACHE_DIR / f"{safe_ticker}_{date}.pkl"


def load_cached(ticker: str, date: Optional[str] = None):
    """Load cached price data if available."""
    path = _cache_file(ticker, date)
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    return None


def save_cache(ticker: str, data, date: Optional[str] = None) -> None:
    """Save price data to cache."""
    path = _cache_file(ticker, date)
    with path.open("wb") as f:
        pickle.dump(data, f)


def get_price_data(
    ticker: str,
    *,
    date: Optional[str] = None,
    period: str | None = "2d",
    **kwargs,
) -> pd.DataFrame:
    """Get price data for ticker using cache."""
    cached = load_cached(ticker, date)
    if cached is not None:
        return cached

    if period is not None:
        kwargs["period"] = period
    data = yf.download(ticker, progress=False, **kwargs)
    save_cache(ticker, data, date)
    return data
