"""Provider registry —— morning-bites 定制版只有一个: Cboe 归档回放。

上游的 Yahoo provider 已删(morning-bites 不让这个页面自己取数, 见 providers/cboe_archive.py 模块头)。
get_provider() 仍是唯一把名字变成对象的地方; collector / dashboard / tests 拿到什么用什么。
"""

from __future__ import annotations

from app.providers.base import (
    CHAIN_COLUMNS,
    CHAIN_OPTIONAL_COLUMNS,
    DataProvider,
    ProviderStatus,
    is_rate_limited,
    with_retry,
)
from app.providers.cboe_archive import CboeArchiveProvider

DEFAULT_PROVIDER = "cboe"

__all__ = [
    "CHAIN_COLUMNS",
    "CHAIN_OPTIONAL_COLUMNS",
    "DEFAULT_PROVIDER",
    "CboeArchiveProvider",
    "DataProvider",
    "ProviderStatus",
    "get_provider",
    "is_rate_limited",
    "known_providers",
    "with_retry",
]


def known_providers() -> tuple[str, ...]:
    return ("cboe",)


def get_provider(name: str | None = None, token: str | None = None) -> DataProvider:
    resolved = (name or DEFAULT_PROVIDER).strip().lower()
    if resolved == "cboe":
        return CboeArchiveProvider()
    raise ValueError(
        f"Unknown data provider {resolved!r}. Known providers: {', '.join(known_providers())}."
    )
