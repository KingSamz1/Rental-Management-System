"""
Currency conversion utility for LandlordPro UG.

Fetches live exchange rates from exchangerate-api.com (free tier, no key needed).
Falls back to hardcoded rates if the network call fails.
"""

import requests
import streamlit as st

BASE_CURRENCY = "UGX"

_FALLBACK_RATES = {
    "UGX": 1.0,
    "USD": 0.000268,
    "EUR": 0.000248,
    "GBP": 0.000212,
    "KES": 0.034,
    "TZS": 0.68,
    "RWF": 0.30,
    "ETB": 0.015,
    "ZAR": 0.0049,
}

_RATE_TTL = 3600  # seconds — cached by Streamlit


@st.cache_data(ttl=_RATE_TTL, show_spinner=False)
def _fetch_rates() -> dict:
    """Return live rates {currency: rate_from_UGX}. Falls back on any error."""
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/UGX",
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("rates", _FALLBACK_RATES)
    except Exception:
        pass
    return _FALLBACK_RATES


def get_supported_currencies() -> list:
    rates = _fetch_rates()
    priority = ["UGX", "USD", "EUR", "GBP", "KES", "TZS", "RWF", "ETB", "ZAR"]
    others = sorted(c for c in rates if c not in priority)
    return [c for c in priority if c in rates] + others


def convert(amount_ugx: float, to_currency: str) -> float:
    """Convert UGX amount to another currency using live rates."""
    if to_currency == BASE_CURRENCY:
        return amount_ugx
    rates = _fetch_rates()
    rate = rates.get(to_currency)
    if not rate:
        return amount_ugx
    return amount_ugx * rate


def format_converted(amount_ugx: float, display_currency: str) -> str:
    """E.g. 'UGX 120,000  (≈ USD 32.16)'"""
    if display_currency == BASE_CURRENCY:
        return f"UGX {amount_ugx:,.0f}"
    converted = convert(amount_ugx, display_currency)
    return f"UGX {amount_ugx:,.0f}  (≈ {display_currency} {converted:,.2f})"


def rate_note(display_currency: str) -> str:
    if display_currency == BASE_CURRENCY:
        return ""
    rates = _fetch_rates()
    rate = rates.get(display_currency, 0)
    if not rate:
        return ""
    return (
        f"Live rate: 1 UGX ≈ {rate:.5f} {display_currency}. "
        f"Billing is always in UGX."
    )
