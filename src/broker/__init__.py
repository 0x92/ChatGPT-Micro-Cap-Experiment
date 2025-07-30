"""Simple broker API wrapper for paper trading.

This module communicates with a remote brokerage API using
credentials provided through environment variables. Only
paper-trading endpoints are used.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

# Environment variable names
_API_KEY_ENV = "BROKER_API_KEY"
_SECRET_KEY_ENV = "BROKER_SECRET_KEY"
_BASE_URL_ENV = "BROKER_BASE_URL"


def _get_headers() -> Dict[str, str]:
    """Return authentication headers for the brokerage API."""
    api_key = os.getenv(_API_KEY_ENV)
    secret_key = os.getenv(_SECRET_KEY_ENV)
    if not api_key or not secret_key:
        raise EnvironmentError(
            f"{_API_KEY_ENV} and {_SECRET_KEY_ENV} must be set for broker access"
        )
    return {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key,
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    """Return the base URL for the brokerage API."""
    return os.getenv(_BASE_URL_ENV, "https://paper-api.alpaca.markets")


def place_order(symbol: str, qty: int, side: str, order_type: str = "market", time_in_force: str = "gtc") -> Dict[str, Any]:
    """Place an order through the brokerage API.

    Parameters
    ----------
    symbol:
        Stock ticker to trade.
    qty:
        Number of shares.
    side:
        "buy" or "sell".
    order_type:
        Order type, defaults to "market".
    time_in_force:
        How long the order remains active.

    Returns
    -------
    Dict[str, Any]
        JSON response from the API.
    """
    url = f"{_base_url()}/v2/orders"
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
    }
    response = requests.post(url, json=payload, headers=_get_headers(), timeout=10)
    response.raise_for_status()
    return response.json()


def get_account() -> Dict[str, Any]:
    """Return account information from the brokerage API."""
    url = f"{_base_url()}/v2/account"
    response = requests.get(url, headers=_get_headers(), timeout=10)
    response.raise_for_status()
    return response.json()


def list_positions() -> List[Dict[str, Any]]:
    """Return open positions from the brokerage API."""
    url = f"{_base_url()}/v2/positions"
    response = requests.get(url, headers=_get_headers(), timeout=10)
    response.raise_for_status()
    return response.json()
