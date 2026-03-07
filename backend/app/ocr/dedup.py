from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ..schemas import TradeInput


@dataclass(frozen=True)
class DedupKey:
    symbol: str
    qty: int
    price_q: str
    timestamp_iso: str


def _price_key(price: Decimal) -> str:
    return str(price.quantize(Decimal("0.0001")))


def _ts_key(ts) -> Optional[str]:  # type: ignore[no-untyped-def]
    if ts is None:
        return None
    return ts.replace(microsecond=0).isoformat()


def dedup_trades(trades: list[TradeInput]) -> tuple[list[TradeInput], list[TradeInput]]:
    seen: set[DedupKey] = set()
    out: list[TradeInput] = []
    removed: list[TradeInput] = []

    for t in trades:
        ts = _ts_key(t.timestamp)
        if not ts:
            out.append(t)
            continue
        key = DedupKey(
            symbol=t.symbol.strip().upper(),
            qty=int(t.qty),
            price_q=_price_key(t.price),
            timestamp_iso=ts,
        )
        if key in seen:
            removed.append(t)
            continue
        seen.add(key)
        out.append(t)

    return out, removed

