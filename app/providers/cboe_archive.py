"""Cboe 期权链归档回放 —— morning-bites 定制版唯一的 provider。

morning-bites(https://github.com/aaronc137/morning-bites)每个交易日三班(09:00 / 12:35 / 16:20 ET)
把 Cboe 期权链原样 gzip 落在 `out/gex/raw/<date>-<session>-<URLTICKER>.json.gz`, 快照
`out/gex/<date>-<session>.json` 最后落盘。这里**不发任何网络请求**: 读那份 gz, 翻译成
`CHAIN_COLUMNS` 的形状交给 db.insert_snapshot。上游频次纪律(SPY 每日 4 次已顶格)因此一字不动。

OCC 解析自己写, 不 import morning_bites(两仓隔离: 本仓是 AGPL 公开 fork, 它读的是数据文件)。

两条口径处理, 都在喂库之前做完, 不依赖 gammagrid 的 SQL 层:
  * 剔除已到期行: `expiry < 场次 ET 日期`。Cboe 周一盘前 / 周五收盘的链带着昨日已到期 series,
    且保留尾盘 gamma, morning-bites 实测 SPX 542 行能把净值符号翻过来。0DTE(当日到期)保留。
  * SPX / SPXW 合并: 月度到期日 AM 结算的 SPX 与 PM 结算的 SPXW 同行权价并存, gammagrid 的
    `_one_contract_per_identity` 会把 SPXW 那半丢掉(9-30 盘前量过: 总 OI 的 2.5%)。这里按
    (expiry, strike, option_type) 合并: OI、volume 相加, 其余字段取 OI 大的那行。

Modified for morning-bites, 2026-10-08. AGPL-3.0, 同本仓 LICENSE。
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

import pandas as pd

from app import config
from app.providers.base import CHAIN_COLUMNS, ProviderStatus

#: morning-bites 的 URL 票名: 指数在 Cboe 接口里带下划线前缀。
URL_TICKER = {"SPX": "_SPX"}


def url_ticker(ticker: str) -> str:
    return URL_TICKER.get(ticker.upper(), ticker.upper())


def parse_occ(symbol: str) -> tuple[str, dt.date, str, float]:
    """`SPXW261016C00200000` → (root, expiry, 'call'/'put', strike)。末 15 位固定: 6 位日期 + 1 位类型 + 8 位行权价×1000。"""
    root = symbol[:-15]
    yymmdd = symbol[-15:-9]
    expiry = dt.date(2000 + int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6]))
    kind = "call" if symbol[-9] == "C" else "put"
    strike = int(symbol[-8:]) / 1000
    return root, expiry, kind, strike


def _merge_same_identity(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """同 (expiry, strike, option_type) 的多行(SPX + SPXW)合成一行: OI / volume 相加, 其余取 OI 大的那行。"""
    identity = ["expiry", "strike", "option_type"]
    if not frame.duplicated(subset=identity).any():
        return frame
    ranked = frame.sort_values("open_interest", ascending=False, kind="stable")
    summed = ranked.groupby(identity, sort=False)[["open_interest", "volume"]].sum()
    first = ranked.groupby(identity, sort=False).first()
    first[["open_interest", "volume"]] = summed
    return first.reset_index()[list(frame.columns)]


def chain_from_payload(payload: dict, ticker: str, session_date: dt.date) -> tuple[float, pd.DataFrame]:
    """一份 Cboe 响应 → (spot, 恰好 CHAIN_COLUMNS + contract_symbol 的 DataFrame)。"""
    data = payload["data"]
    spot = float(data["current_price"])
    rows = []
    for o in data.get("options") or []:
        root, expiry, kind, strike = parse_occ(o["option"])
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
    return spot, _merge_same_identity(frame, ticker)


def collected_at_of(payload: dict) -> dt.datetime:
    """Cboe 给这份链盖的报价时刻(顶层 `timestamp`, UTC 裸串), 回放两个月归档时每份必须用它自己的时刻。"""
    return dt.datetime.fromisoformat(str(payload["timestamp"]).replace(" ", "T")).replace(tzinfo=None)


def load_chain(path: Path, ticker: str, session_date: dt.date) -> tuple[dt.datetime, float, pd.DataFrame]:
    """读一份 gz → (collected_at, spot, chain)。"""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    spot, frame = chain_from_payload(payload, ticker, session_date)
    return collected_at_of(payload), spot, frame


class CboeArchiveProvider:
    """DataProvider 协议的归档版: 只读盘, 永不联网。`name` 写进每一行的 source, 定了就不改。"""

    name = "cboe"
    price_history_source = "cboe"
    requires_token = False
    unsupported_symbols: dict[str, str | None] = {}

    def __init__(self, archive_dir: str | Path | None = None) -> None:
        self.archive_dir = Path(archive_dir or config.MB_OUT) / "gex"

    def latest_raw(self, ticker: str) -> Path | None:
        paths = sorted((self.archive_dir / "raw").glob(f"????-??-??-*-{url_ticker(ticker)}.json.gz"))
        return paths[-1] if paths else None

    def fetch_ticker_snapshot(self, ticker: str) -> tuple[float, pd.DataFrame]:
        path = self.latest_raw(ticker)
        if path is None:
            raise FileNotFoundError(f"{self.archive_dir} 里没有 {ticker} 的 raw 归档")
        _at, spot, frame = load_chain(path, ticker, dt.date.fromisoformat(path.name[:10]))
        return spot, frame

    def fetch_price_history(self, ticker: str, period: str) -> pd.DataFrame:
        """没有价格历史源, 也不去要: 空帧让 realized volatility 那一步安静地写 0 行。"""
        return pd.DataFrame(columns=["close"])

    def check_access(self) -> ProviderStatus:
        if self.archive_dir.is_dir():
            return ProviderStatus(True, f"读 {self.archive_dir}")
        return ProviderStatus(False, f"归档目录不存在: {self.archive_dir}(设 GG_MB_OUT)")
