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

THE SHARED TICKERS ARE NOT REQUESTED TWICE. morning-bites fetches SPY, QQQ and
SPX itself three times a day and archives the bytes as
`<raw dir>/<ET date>-<premarket|intraday|close>-<URL ticker>.json.gz`; SPY is
already at that repository's 4-per-day ceiling from this IP. With
`GEX_RAW_DIR` set, a shared ticker is read from today's raw if one landed in
the last RAW_FRESH_MINUTES (the collector runs 3 min after each fetch), and
the GET happens only when no such file exists — logged as a WARNING, because
that is the one case that pushes SPY past the ceiling. Unset, every ticker is
a GET (upstream behaviour).

The moment stored is Cboe's own quote time (`payload['timestamp']`, naive UTC),
handed to the collector in `DataFrame.attrs['collected_at']` — the same
convention the 324 replayed archive moments carry, so a moment is the same
moment whichever path stored it, and the collector refuses to store one twice.

Modified for morning-bites, 2026-10-09. AGPL-3.0, same as the repository.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from app.providers.base import CHAIN_COLUMNS, ProviderStatus
from app.providers.yahoo import INDEX_SYMBOLS, YahooProvider

log = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

# Keep these three in step with morning_bites/gex.py (_CBOE_URL, _UA, _HTTP_TIMEOUT).
_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HTTP_TIMEOUT = 60
_REQUEST_GAP_SECONDS = 1

# Tickers morning-bites fetches itself (gex.py _TICKERS), and how recent its raw
# must be to stand in for a request: 30 min covers 09:00→09:03 and 16:20→16:23.
SHARED_TICKERS = frozenset({"SPY", "QQQ", "SPX"})
RAW_FRESH_MINUTES = 30


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


def quote_time(payload: dict) -> dt.datetime | None:
    """Cboe's own stamp on the chain (naive UTC), or None if it cannot be read."""
    try:
        return dt.datetime.fromisoformat(str(payload["timestamp"]).replace(" ", "T")).replace(tzinfo=None)
    except (KeyError, ValueError, TypeError):
        return None


def fresh_raw(raw_dir: str | os.PathLike | None, ticker: str, now: dt.datetime | None = None) -> Path | None:
    """Today's (ET) newest morning-bites raw for a shared ticker, if written in the
    last RAW_FRESH_MINUTES; None otherwise (and always None with no raw dir)."""
    if not raw_dir or ticker.upper() not in SHARED_TICKERS:
        return None
    now = now or dt.datetime.now(_ET)
    cutoff = now.timestamp() - RAW_FRESH_MINUTES * 60
    candidates = [
        path for path in Path(raw_dir).glob(f"{now:%Y-%m-%d}-*-{url_ticker(ticker)}.json.gz")
        if path.stat().st_mtime >= cutoff
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


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

    def __init__(self, raw_dir: str | os.PathLike | None = None) -> None:
        self._yahoo = YahooProvider()
        self.raw_dir = raw_dir if raw_dir is not None else os.environ.get("GEX_RAW_DIR") or None

    def fetch_underlying_price(self, ticker: str) -> float:
        return float(_get(ticker)["data"]["current_price"])

    def fetch_ticker_snapshot(self, ticker: str) -> tuple[float, pd.DataFrame]:
        now = dt.datetime.now(_ET)
        raw = fresh_raw(self.raw_dir, ticker, now)
        if raw is not None:
            with gzip.open(raw, "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
            log.info("%s: read morning-bites raw %s (no request)", ticker, raw.name)
        else:
            if self.raw_dir and ticker.upper() in SHARED_TICKERS:
                log.warning(
                    "%s: 晨刊 raw 缺席(%s 里没有 %s 的、%d 分钟内的文件), 回落直取 Cboe —— "
                    "这一次让该标的超出 morning-bites 的 ≤4 次/日",
                    ticker, self.raw_dir, f"{now:%Y-%m-%d}", RAW_FRESH_MINUTES,
                )
            payload = _get(ticker)
            log.info("%s: GET cdn.cboe.com delayed_quotes", ticker)
        spot, frame = chain_from_payload(payload, now.date())
        # The source's own moment, for the collector (see the module docstring).
        frame.attrs["collected_at"] = quote_time(payload)
        return spot, frame

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
