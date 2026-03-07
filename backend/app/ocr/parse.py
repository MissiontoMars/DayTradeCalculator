from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class ParsedTrade:
    symbol: str
    side: str
    qty: int
    price: Decimal
    fee: Decimal
    timestamp: Optional[datetime]
    source: Optional[str]


_BUY_WORDS = ("BUY", "B", "买", "买入")
_SELL_WORDS = ("SELL", "S", "卖", "卖出")


def _normalize_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("，", ",").replace("：", ":").replace("￥", "$")
    return s


def _cluster_lines(items: list[dict[str, Any]]) -> list[str]:
    boxes = []
    for it in items:
        text = _normalize_text(str(it.get("text") or ""))
        if not text:
            continue
        box = it.get("box")
        if not box or len(box) < 4:
            continue
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        boxes.append(
            {
                "text": text,
                "y": float(min(ys)),
                "y2": float(max(ys)),
                "x": float(min(xs)),
            }
        )

    boxes.sort(key=lambda b: (b["y"], b["x"]))

    heights = sorted(max(1.0, b["y2"] - b["y"]) for b in boxes)
    if heights:
        mid = heights[len(heights) // 2]
        y_thresh = max(8.0, min(30.0, mid * 0.7))
    else:
        y_thresh = 12.0

    lines: list[list[dict[str, Any]]] = []
    for b in boxes:
        if not lines:
            lines.append([b])
            continue
        if abs(b["y"] - lines[-1][0]["y"]) <= y_thresh:
            lines[-1].append(b)
        else:
            lines.append([b])

    out: list[str] = []
    for line in lines:
        line.sort(key=lambda b: b["x"])
        out.append(" ".join(b["text"] for b in line))
    return out


def cluster_ocr_lines(items: list[dict[str, Any]]) -> list[str]:
    return _cluster_lines(items)


def _parse_side(line: str) -> Optional[str]:
    up = line.upper()
    for w in _BUY_WORDS:
        if w in up or w in line:
            return "BUY"
    for w in _SELL_WORDS:
        if w in up or w in line:
            return "SELL"
    return None


_SYMBOL_RE = re.compile(r"\b[A-Z]{1,6}\b")
_SYMBOL_STOPWORDS = {
    "BUY",
    "SELL",
    "USD",
    "CNY",
    "ETF",
    "LIMIT",
    "MARKET",
    "DAY",
    "GTC",
    "FILLED",
    "EXECUTED",
    "ORDER",
    "TRADE",
    "ALL",
    "PARTIAL",
    "CANCELLED",
    "CANCELED",
}


def _parse_symbol(line: str) -> Optional[str]:
    candidates = _SYMBOL_RE.findall(line.upper())
    if not candidates:
        return None
    for c in candidates:
        if c in _SYMBOL_STOPWORDS:
            continue
        return c
    return candidates[0]


def _parse_qty(line: str) -> Optional[int]:
    s = line.replace(",", "")
    nums = re.findall(r"\b(\d{1,9})\b", s)
    if not nums:
        return None
    for token in nums:
        try:
            n = int(token)
        except ValueError:
            continue
        if 1900 <= n <= 2100:
            continue
        if n == 0:
            continue
        return n
    return None


def _parse_price(line: str) -> Optional[Decimal]:
    s = line.replace(",", "")
    m = re.search(r"@\s*([0-9]+(?:\.[0-9]+)?)", s)
    if m:
        return Decimal(m.group(1))
    nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", s)
    if not nums:
        return None
    return Decimal(nums[-1])


def _parse_fee(line: str) -> Decimal:
    s = line.replace(",", "").lower()
    m = re.search(r"\b(fee|commission)\s*[: ]\s*([0-9]+(?:\.[0-9]+)?)\b", s)
    if m:
        return Decimal(m.group(2))
    return Decimal("0")


_DT_PATTERNS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
)


def _parse_timestamp(line: str) -> Optional[datetime]:
    s = _normalize_text(line)
    m = re.search(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?)|(\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}(?::\d{2})?)",
        s,
    )
    if not m:
        return None
    token = m.group(0)
    for p in _DT_PATTERNS:
        try:
            return datetime.strptime(token, p)
        except ValueError:
            continue
    return None


def _try_patterns(line: str) -> Optional[tuple[str, str, int, Decimal]]:
    s = _normalize_text(line)
    up = s.upper()

    m = re.search(r"\b(BUY|SELL)\b\s+(\d{1,7})\s+([A-Z]{1,6})\b.*?(?:@|AT)\s*([0-9]+(?:\.[0-9]+)?)", up)
    if m:
        return m.group(3), m.group(1), int(m.group(2)), Decimal(m.group(4))

    m = re.search(r"\b([A-Z]{1,6})\b\s+\b(BUY|SELL)\b\s+(\d{1,7})\b.*?(?:@|AT)\s*([0-9]+(?:\.[0-9]+)?)", up)
    if m:
        return m.group(1), m.group(2), int(m.group(3)), Decimal(m.group(4))

    m = re.search(r"\b(BUY|SELL)\b\s+([A-Z]{1,6})\b\s+(\d{1,7})\b.*?(?:@|AT)\s*([0-9]+(?:\.[0-9]+)?)", up)
    if m:
        return m.group(2), m.group(1), int(m.group(3)), Decimal(m.group(4))

    m = re.search(r"(买入|卖出)\s*([A-Z]{1,6})\s*(\d{1,7})\s*(?:股)?\s*([0-9]+(?:\.[0-9]+)?)", s)
    if m:
        side = "BUY" if m.group(1) == "买入" else "SELL"
        return m.group(2).upper(), side, int(m.group(3)), Decimal(m.group(4))

    m = re.search(r"(买入|卖出)\s*(\d{1,7})\s*([A-Z]{1,6})\s*([0-9]+(?:\.[0-9]+)?)", s)
    if m:
        side = "BUY" if m.group(1) == "买入" else "SELL"
        return m.group(3).upper(), side, int(m.group(2)), Decimal(m.group(4))

    return None


def parse_line(line: str) -> Optional[tuple[str, str, int, Decimal, Decimal, Optional[datetime]]]:
    ts = _parse_timestamp(line)
    fee = _parse_fee(line)

    hit = _try_patterns(line)
    if hit:
        symbol, side, qty, price = hit
        if symbol in _SYMBOL_STOPWORDS:
            return None
        return symbol, side, qty, price, fee, ts

    side = _parse_side(line)
    if not side:
        return None
    symbol = _parse_symbol(line)
    qty = _parse_qty(line)
    price = _parse_price(line)
    if not symbol or not qty or price is None:
        return None
    return symbol, side, qty, price, fee, ts


def parse_ocr_items(
    items_by_image: Iterable[tuple[str, list[dict[str, Any]]]],
) -> tuple[list[ParsedTrade], list[str]]:
    trades: list[ParsedTrade] = []
    warnings: list[str] = []

    for source, items in items_by_image:
        lines = _cluster_lines(items)
        t, w = parse_text_lines(lines, source)
        trades.extend(t)
        warnings.extend(w)

    return trades, warnings


_ACTION_LINE_RE = re.compile(r"^(买入|卖出)\b")
_MD_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
_FILL_LINE_RE = re.compile(
    r"\b([A-Z]{1,6})\b\s+([0-9]+(?:\.[0-9]+)?)\s*(\d{2}:\d{2}:\d{2})\b",
)


def _parse_action_line(line: str) -> Optional[tuple[str, int, Optional[datetime]]]:
    s = _normalize_text(line)
    m = _ACTION_LINE_RE.match(s)
    if not m:
        return None
    side = "BUY" if m.group(1) == "买入" else "SELL"

    md = _MD_RE.search(s)
    dt: Optional[datetime] = None
    if md:
        month = int(md.group(1))
        day = int(md.group(2))
        year_raw = md.group(3)
        year = datetime.now().year if not year_raw else int(year_raw if len(year_raw) == 4 else f"20{year_raw}")
        dt = datetime(year, month, day)

    s_wo_date = s
    if md:
        s_wo_date = (s[: md.start()] + " " + s[md.end() :]).strip()
    qty = _parse_qty(s_wo_date)
    if not qty:
        return None
    return side, qty, dt


def _parse_fill_line(line: str) -> Optional[tuple[str, Decimal, Optional[datetime]]]:
    s = _normalize_text(line)
    m = _FILL_LINE_RE.search(s.upper())
    if not m:
        return None
    symbol = m.group(1).upper()
    if symbol in _SYMBOL_STOPWORDS:
        return None
    price = Decimal(m.group(2))
    h, mi, sec = (int(x) for x in m.group(3).split(":"))
    t = datetime(2000, 1, 1, h, mi, sec)
    return symbol, price, t


def _combine_date_time(d: Optional[datetime], t: Optional[datetime]) -> Optional[datetime]:
    if not d or not t:
        return None
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)


def parse_text_lines(lines: list[str], source: str | None = None) -> tuple[list[ParsedTrade], list[str]]:
    trades: list[ParsedTrade] = []
    warnings: list[str] = []

    i = 0
    while i < len(lines):
        line = _normalize_text(lines[i])

        a = _parse_action_line(line)
        if a and i + 1 < len(lines):
            next_line = _normalize_text(lines[i + 1])
            f = _parse_fill_line(next_line)
            if f:
                side, qty, d = a
                symbol, price, t = f
                ts = _combine_date_time(d, t)
                trades.append(
                    ParsedTrade(
                        symbol=symbol,
                        side=side,
                        qty=qty,
                        price=price,
                        fee=Decimal("0"),
                        timestamp=ts,
                        source=source,
                    )
                )
                i += 2
                continue

        parsed = parse_line(line)
        if not parsed:
            if _parse_side(line):
                warnings.append(f"{source}: 解析失败: {line}")
            i += 1
            continue

        symbol, side, qty, price, fee, ts = parsed
        trades.append(
            ParsedTrade(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                fee=fee,
                timestamp=ts,
                source=source,
            )
        )
        i += 1

    return trades, warnings
