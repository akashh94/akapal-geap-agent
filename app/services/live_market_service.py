"""Real-time stock quotes via yfinance.

Falls back to ``None`` on any error (unknown symbol, network issue, rate
limit) so callers can chain to a mock or cached source.
"""

import logging

from app.models.quote import Quote

_LOGGER = logging.getLogger(__name__)


class LiveMarketService:
    """Wraps ``yfinance.Ticker`` to return ``Quote`` instances."""

    def get_quote(self, symbol: str) -> Quote | None:
        import yfinance as yf  # defer import so startup doesn't fail if absent

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            price = _field(info, "currentPrice", "regularMarketPrice")
            if price is None:
                _LOGGER.warning("yfinance returned no price for %s", symbol)
                return None
            try:
                price = float(price)
            except (TypeError, ValueError):
                _LOGGER.warning("yfinance returned non-numeric price for %s", symbol)
                return None

            return Quote(
                symbol=symbol,
                company_name=_str_field(info, "longName", "shortName") or symbol,
                price=price,
                change=_num(_field(info, "regularMarketChange")),
                change_percent=_num(_field(info, "regularMarketChangePercent")),
                open_price=_num(_field(info, "regularMarketOpen"), default=price),
                high_price=_num(_field(info, "regularMarketDayHigh"), default=price),
                low_price=_num(_field(info, "regularMarketDayLow"), default=price),
                volume=int(_num(_field(info, "regularMarketVolume"))),
                average_volume=int(_num(_field(info, "averageVolume"))),
                market_cap=_format_market_cap(_num(_field(info, "marketCap"))),
                pe_ratio=_num(_field(info, "trailingPE")) or None,
                eps=_num(_field(info, "trailingEps")) or None,
                week_52_high=_num(_field(info, "fiftyTwoWeekHigh"), default=price),
                week_52_low=_num(_field(info, "fiftyTwoWeekLow"), default=price * 0.75),
                dividend_yield=_num(
                    _field(info, "dividendYield", "trailingAnnualDividendYield")
                )
                or None,
            )
        except Exception:
            _LOGGER.warning("Failed to fetch live quote for %s", symbol, exc_info=True)
            return None


def _field(info: dict, *keys: str) -> float | str | None:
    """Return the first non-None value for *keys* from *info*."""
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return None


def _str_field(info: dict, *keys: str) -> str | None:
    """Return the first string value for *keys* from *info*."""
    for k in keys:
        v = info.get(k)
        if isinstance(v, str):
            return v
    return None


def _num(value: float | str | None, default: float = 0.0) -> float:
    """Coerce a yfinance field to float, falling back to *default*."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_market_cap(value: float | str | None) -> str:
    """Format a numeric market cap as a human-friendly string."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if v >= 1_000_000_000_000:
            return f"${v / 1_000_000_000_000:.1f}T"
        if v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.1f}B"
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        return f"${v:,.0f}"
    except (ValueError, TypeError):
        return str(value)
