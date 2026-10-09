"""Cboe delayed quotes — the same chain morning-bites' own edition reads.

One GET per ticker per pass against Cboe's public delayed-quotes CDN; no account,
no token. URL, user agent, timeout and the one-second gap between tickers are
copied from morning-bites' `morning_bites/gex.py`, deliberately: the two products
share an exit IP, and a change to one side's habits has to be made on both.

Not wrapped in `with_retry`: morning-bites makes a single attempt per ticker and
so does this — Cboe's "429 Too Many Requests" already reads as rate-limited to
the collector, which pauses the whole pass.

Two shaping rules before the chain reaches the database, both from the archived
morning-bites provider (`cboe_archive.py`, 2026-10-08):

  * expired series are dropped (`expiry < today ET`): Cboe keeps yesterday's
    expiries in the chain with their closing gamma, enough to flip SPX's net
    sign. Today's (0DTE) stay.
  * SPX and SPXW are merged per (expiry, strike, type): AM-settled SPX and
    PM-settled SPXW list the same strikes on monthly expiries and the registry's
    one-contract-per-identity rule would otherwise drop the SPXW half (2.5% of
    SPX open interest, measured 2026-09-30). OI and volume are summed, every
    other field comes from the larger-OI row.

Greeks: Cboe serves delta/gamma/theta/vega from its own model; they are stored
as served (see `base.CHAIN_COLUMNS`). Implied volatility of exactly 0 is
stored as missing — it means "not quoted", not a volatility.

Price history comes from Yahoo (`price_history_source`): Cboe serves no daily
closes, and realized volatility needs them.

Modified for morning-bites, 2026-10-09. AGPL-3.0, same as the repository.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

import pandas as pd

from app.providers.base import CHAIN_COLUMNS, ProviderStatus
from app.providers.yahoo import INDEX_SYMBOLS, YahooProvider

_ET = ZoneInfo("America/New_York")

# Keep these three in step with morning_bites/gex.py (_CBOE_URL, _UA, _HTTP_TIMEOUT).
_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HTTP_TIMEOUT = 60
_REQUEST_GAP_SECONDS = 1


def url_ticker(ticker: str) -> str:
    """Cboe spells cash-settled indexes with an underscore: SPX → _SPX."""
    ticker = ticker.upper()
    return f"_{ticker}" if ticker in INDEX_SYMBOLS else ticker


def parse_occ(symbol: str) -> tuple[str, dt.date, str, float]:
    """`SPXW261016C00200000` → (root, expiry, 'call'/'put', strike).
    The last 15 characters are fixed: 6 date, 1 type, 8 strike × 1000."""
    root = symbol[:-15]
    yymmdd = symbol[-15:-9]
    expiry = dt.date(2000 + int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6]))
    kind = "call" if symbol[-9] == "C" else "put"
    strike = int(symbol[-8:]) / 1000
    return root, expiry, kind, strike


def _merge_same_identity(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows sharing (expiry, strike, option_type) — SPX + SPXW — become one:
    OI and volume summed, every other field from the larger-OI row (first
    non-missing value per field, in OI order)."""
    identity = ["expiry", "strike", "option_type"]
    if not frame.duplicated(subset=identity).any():
        return frame
    ranked = frame.sort_values("open_interest", ascending=False, kind="stable")
    summed = ranked.groupby(identity, sort=False)[["open_interest", "volume"]].sum()
    first = ranked.groupby(identity, sort=False).first()
    first[["open_interest", "volume"]] = summed
    return first.reset_index()[list(frame.columns)]


def chain_from_payload(payload: dict, session_date: dt.date) -> tuple[float, pd.DataFrame]:
    """One Cboe response → (spot, DataFrame of exactly CHAIN_COLUMNS + contract_symbol)."""
    data = payload["data"]
    spot = float(data["current_price"])
    rows = []
    for o in data.get("options") or []:
        _root, expiry, kind, strike = parse_occ(o["option"])
        if expiry < session_date:
            continue
        iv = o.get("iv")
        rows.append({
            "expiry": expiry, "strike": strike, "option_type": kind,
            "last_price": o.get("last_trade_price"), "bid": o.get("bid"), "ask": o.get("ask"),
            "volume": o.get("volume"), "open_interest": o.get("open_interest"),
            "implied_volatility": iv if iv is not None and iv > 0 else None,
            "in_the_money": (strike < spot) if kind == "call" else (strike > spot),
            "delta": o.get("delta"), "gamma": o.get("gamma"), "theta": o.get("theta"), "vega": o.get("vega"),
            "contract_symbol": o["option"],
        })
    frame = pd.DataFrame(rows, columns=[*CHAIN_COLUMNS, "contract_symbol"])
    if frame.empty:
        return spot, frame
    frame["open_interest"] = frame["open_interest"].fillna(0)
    frame["volume"] = frame["volume"].fillna(0)
    return spot, _merge_same_identity(frame)


def _get(ticker: str) -> dict:
    """One request, one attempt. Raises urllib.error.HTTPError on 4xx/5xx —
    "HTTP Error 429" is what the collector reads as rate-limited."""
    request = urllib.request.Request(
        _CBOE_URL.format(ticker=url_ticker(ticker)), headers={"User-Agent": _UA}
    )
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    time.sleep(_REQUEST_GAP_SECONDS)
    return payload


class CboeProvider:
    name = "cboe"  # written into option_snapshots.source; the archive's rows carry it — never change
    price_history_source = "yahoo"
    requires_token = False
    # Cboe serves the index chains Yahoo refuses (SPX, XSP, NDX, RUT, VIX, DJX).
    unsupported_symbols: dict[str, str | None] = {}
    token: str | None = None

    def __init__(self) -> None:
        self._yahoo = YahooProvider()

    def fetch_underlying_price(self, ticker: str) -> float:
        return float(_get(ticker)["data"]["current_price"])

    def fetch_ticker_snapshot(self, ticker: str) -> tuple[float, pd.DataFrame]:
        return chain_from_payload(_get(ticker), dt.datetime.now(_ET).date())

    def fetch_price_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        return self._yahoo.fetch_price_history(ticker, period)

    def underlying_has_options(self, ticker: str) -> bool | None:
        """True/False from one GET; None when Cboe could not answer (the
        caller lets the ticker through on None — see yahoo.py)."""
        try:
            return bool(_get(ticker)["data"].get("options"))
        except urllib.error.HTTPError as exc:
            return False if exc.code == 404 else None
        except Exception:  # noqa: BLE001 — every other failure means "could not find out"
            return None

    def check_access(self) -> ProviderStatus:
        try:
            spot = self.fetch_underlying_price("SPY")
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus(False, f"Cboe delayed quotes are not responding: {exc}")
        return ProviderStatus(True, f"Cboe delayed quotes are reachable (SPY {spot:.2f}). No token required.")
