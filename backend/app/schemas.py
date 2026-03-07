from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


Side = Literal["BUY", "SELL"]


class TradeInput(BaseModel):
    symbol: str = Field(min_length=1)
    side: Side
    qty: int = Field(gt=0)
    price: Decimal = Field(ge=Decimal("0"))
    fee: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    timestamp: Optional[datetime] = None
    source: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_ts(cls, v):  # type: ignore[no-untyped-def]
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v
        s = str(v).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return datetime.fromisoformat(s)


class OcrResponse(BaseModel):
    ocr_session_id: str
    status: str
    message: Optional[str] = None
    trades: list[TradeInput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CalcRequest(BaseModel):
    ocr_session_id: Optional[str] = None
    trades: list[TradeInput]


class SymbolResult(BaseModel):
    symbol: str
    realized_pnl: Decimal
    net_shares: int
    open_lots: list[dict]


class CalcResponse(BaseModel):
    run_id: str
    created_at: datetime
    results: list[SymbolResult]


class CalcRunSummary(BaseModel):
    id: str
    created_at: datetime
    status: str
    message: Optional[str] = None


class CalcRunDetail(BaseModel):
    id: str
    created_at: datetime
    status: str
    message: Optional[str] = None
    ocr_session_id: Optional[str] = None
    trades: list[TradeInput]
    results: list[SymbolResult]
