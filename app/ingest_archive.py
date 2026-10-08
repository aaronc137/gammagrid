"""把 morning-bites 的 out/gex 归档回放进数据库 —— 本 fork 的采集器, 替代上游的 worker 循环。

    python -m app.ingest_archive [--out /home/mb/morning-bites/out] [--since 15]

每份快照 `out/gex/<date>-<session>.json` 是那一班「三份 raw 齐了」的标志(gex.py 先归档 raw 再写
快照, 快照是 .tmp + os.replace 原子写)。只回放快照 `reads` 里列出的标的: 不在里面的那份 raw 是被
morning-bites 的 `_source_stale` 判为上游冻结的, 这边也不收。

幂等: 每个 (ticker, 'cboe', collected_at) 只入一次, 查的是 snapshot_iv_summary(一行一班, 主键),
不扫 option_snapshots。collected_at 与 collection_runs.started_at 都用 Cboe 给那份链盖的报价时刻
(payload["timestamp"]), 不用入库时刻: 回放两个月归档时每份必须是它自己的时刻, 「较昨日」的日分组、
热图的 Replay 列表与新鲜度判定全靠它。

不走 collector.collect_watchlist(它用 now() 当 collected_at, 还会去 provider 要价格历史);
也不用 collector._write_day_summaries(它按「最近 1 天」找 moment, 回放 8-15 那班会写错)。
每班入库后直接 day_summary.build_row + upsert, 与上游采集路径同一条算式。

跑完写 `<out>/gammagrid/ingest.ok`: 第一行是磁盘上最新那份快照名, 第二行时刻 —— morning-bites 的
金丝雀 gammagrid_fresh 拿它与 out/gex 最新快照名比, 不等即入库落后一班。只写这一个文件进 out/。

systemd 的 gg-ingest.path 盯 out/gex 目录触发(PathChanged), 单元在运行中漏掉的事件由
「每次全量扫、幂等跳过」兜住; 起手 sleep 几秒让 .tmp → os.replace 那两步落稳。

Modified for morning-bites, 2026-10-08. AGPL-3.0, 同本仓 LICENSE。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path

from app import collector, config, day_summary, db, metrics, worker
from app.providers import cboe_archive

log = logging.getLogger("ingest")

SOURCE = "cboe"
INTERVAL_MINUTES = 240
TICKERS = ("SPX", "SPY", "QQQ")
_SESSION_ORDER = {"premarket": 0, "intraday": 1, "close": 2}


def snapshot_files(out_root: Path, since_days: int | None) -> list[Path]:
    """`out/gex/<date>-<session>.json`, 按 (日期, 盘前 < 盘中 < 收盘) 排序 —— 字典序会排成 close < intraday < premarket。"""
    files = []
    for path in (out_root / "gex").glob("????-??-??-*.json"):
        date_str, session = path.stem[:10], path.stem[11:]
        if session not in _SESSION_ORDER:
            continue
        if since_days is not None and dt.date.fromisoformat(date_str) < dt.date.today() - dt.timedelta(days=since_days):
            continue
        files.append(path)
    return sorted(files, key=lambda p: (p.stem[:10], _SESSION_ORDER[p.stem[11:]]))


def already_stored(conn, ticker: str, collected_at: dt.datetime) -> bool:
    row = conn.execute(
        "SELECT 1 FROM snapshot_iv_summary WHERE ticker = %s AND source = %s AND collected_at = %s",
        (ticker, SOURCE, collected_at),
    ).fetchone()
    return row is not None


def ingest_one(conn, ticker: str, raw: Path, session_date: dt.date) -> str:
    """一份 raw → 库。返回 'stored' / 'present' / 'empty'。"""
    collected_at, spot, frame = cboe_archive.load_chain(raw, ticker, session_date)
    if already_stored(conn, ticker, collected_at):
        return "present"
    if frame.empty:
        return "empty"
    db.insert_snapshot(conn, ticker, collected_at, spot, frame, source=SOURCE)
    # IV 是 Cboe 报价 IV(app/metrics.py 的 with_solved_iv 直通), 旧式 NULL 戳会让波动率页永远喊「还在重算」。
    conn.execute(
        "UPDATE snapshot_iv_summary SET iv_model = 'provider' WHERE ticker = %s AND source = %s AND collected_at = %s",
        (ticker, SOURCE, collected_at),
    )
    db.log_run(
        conn, collected_at, collected_at, ticker, "success",
        rows_fetched=len(frame), oi_zero_fraction=collector._oi_zero_fraction(frame), source=SOURCE,
    )
    row = day_summary.build_row(conn, ticker, SOURCE, collected_at, metrics.DEFAULT_PRICING)
    if row is not None:
        db.upsert_day_summary(conn, ticker, SOURCE, row, day_summary.CODE_SHA)
    return "stored"


def ingest(conn, out_root: Path, since_days: int | None = None) -> dict:
    out_root = Path(out_root)
    for ticker in TICKERS:
        db.add_ticker(conn, ticker)
    # 没有 worker 在跑, 这个值只影响新鲜度判定: 240 分钟 → 两个周期 = 8 个开市小时, 漏一班当天不报,
    # 漏一整天报 stale(第二道是 morning-bites 的金丝雀 gammagrid_fresh)。上游默认 0 = 关, 页面会按 15 分钟判。
    if db.get_collector_interval(conn) != INTERVAL_MINUTES:
        db.set_collector_interval(conn, INTERVAL_MINUTES)
    counts = {"stored": 0, "present": 0, "empty": 0, "missing_raw": 0, "failed": 0}
    ok_name: str | None = None
    ok_at: dt.datetime | None = None
    # 任一班失败后 ok 名就不再推进: 后面干净的一班不许把前面失败的那班盖过去, 否则 gammagrid_fresh 只抓得住最新一班的失败。
    any_failed = False
    files = snapshot_files(out_root, since_days)
    for path in files:
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("跳过读不动的快照 %s: %s", path.name, exc)
            counts["failed"] += 1
            any_failed = True
            continue
        date_str, session = snap["date"], snap["session"]
        session_date = dt.date.fromisoformat(date_str)
        clean = True
        for read in snap.get("reads") or []:
            ticker = str(read["ticker"]).upper()
            raw = out_root / "gex" / "raw" / f"{date_str}-{session}-{cboe_archive.url_ticker(ticker)}.json.gz"
            if not raw.is_file():
                counts["missing_raw"] += 1
                log.warning("%s: 没有 %s 的 raw(%s)", path.stem, ticker, raw.name)
                continue
            try:
                outcome = ingest_one(conn, ticker, raw, session_date)
            except Exception:  # noqa: BLE001 — 一份坏链不许拖垮回放
                counts["failed"] += 1
                clean = False
                any_failed = True
                log.error("%s %s 入库失败", path.stem, ticker, exc_info=True)
                continue
            counts[outcome] += 1
            if outcome == "stored":
                log.info("%s %s 入库", path.stem, ticker)
        if clean and not any_failed:
            ok_name, ok_at = path.stem, dt.datetime.now(dt.UTC)
    # 上游 worker 每个周期顺手做的三件库内维护, 这里跑完一轮各做一次(都是幂等 / 按日标记的)。
    worker.archive_if_due(conn)
    worker.rebuild_stale_volume_stats(conn)
    worker.fill_missing_day_summaries(conn)
    if ok_name is not None:
        stamp = out_root / "gammagrid" / "ingest.ok"
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(f"{ok_name}\n{ok_at.isoformat(timespec='seconds')}\n", encoding="utf-8")
    counts["snapshots"] = len(files)
    counts["ingest_ok"] = ok_name
    return counts


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="回放 morning-bites 的 out/gex 归档进数据库。")
    parser.add_argument("--out", default=config.MB_OUT, help="morning-bites 的 out/ 根(默认 GG_MB_OUT)")
    parser.add_argument("--since", type=int, default=None, help="只回放最近 N 天的快照(默认全部; 已入库的照样跳过)")
    parser.add_argument("--settle", type=float, default=5.0, help="起手等几秒让 .tmp → os.replace 落稳(path 单元用)")
    args = parser.parse_args(argv)
    if args.settle > 0:
        time.sleep(args.settle)
    conn = db.get_connection()
    try:
        counts = ingest(conn, Path(args.out), args.since)
    finally:
        conn.close()
    log.info("done %s", counts)
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
