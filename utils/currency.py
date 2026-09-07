"""
Currency conversion utility for LandlordPro SA.

Fetches live exchange rates from exchangerate-api.com (free tier, no key needed).
Falls back to hardcoded rates if the network call fails.
"""

import requests
import streamlit as st

BASE_CURRENCY = "ZAR"

_FALLBACK_RATES = {
    "ZAR": 1.0,
    "USD": 0.054,
    "EUR": 0.050,
    "GBP": 0.043,
    "BWP": 0.73,
    "ZMW": 1.47,
    "MZN": 3.44,
    "NAD": 1.0,
    "LSL": 1.0,
    "SZL": 1.0,
}

_RATE_TTL = 3600  # seconds — cached by Streamlit


@st.cache_data(ttl=_RATE_TTL, show_spinner=False)
def _fetch_rates() -> dict:
    """Return live rates {currency: rate_from_ZAR}. Falls back on any error."""
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/ZAR",
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("rates", _FALLBACK_RATES)
    except Exception:
        pass
    return _FALLBACK_RATES


def get_supported_currencies() -> list:
    rates = _fetch_rates()
    priority = ["ZAR", "USD", "EUR", "GBP", "BWP", "ZMW", "MZN", "NAD", "LSL", "SZL"]
    others = sorted(c for c in rates if c not in priority)
    return [c for c in priority if c in rates] + others


def convert(amount_zar: float, to_currency: str) -> float:
    """Convert ZAR amount to another currency using live rates."""
    if to_currency == BASE_CURRENCY:
        return amount_zar
    rates = _fetch_rates()
    rate = rates.get(to_currency)
    if not rate:
        return amount_zar
    return amount_zar * rate


def format_converted(amount_zar: float, display_currency: str) -> str:
    """E.g. 'ZAR 120.00  (≈ USD 6.48)'"""
    if display_currency == BASE_CURRENCY:
        return f"ZAR {amount_zar:,.2f}"
    converted = convert(amount_zar, display_currency)
    return f"ZAR {amount_zar:,.2f}  (≈ {display_currency} {converted:,.2f})"


def rate_note(display_currency: str) -> str:
    if display_currency == BASE_CURRENCY:
        return ""
    rates = _fetch_rates()
    rate = rates.get(display_currency, 0)
    if not rate:
        return ""
    return (
        f"Live rate: 1 ZAR ≈ {rate:.5f} {display_currency}. "
        f"Billing is always in ZAR."
    )
