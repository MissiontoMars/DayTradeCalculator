from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from .util import utcnow, uuid4_str


class OcrSession(SQLModel, table=True):
    id: str = Field(default_factory=uuid4_str, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    status: str = Field(default="processing", index=True)
    message: Optional[str] = Field(default=None)
    image_paths_json: str = Field(default="[]")
    raw_ocr_json: Optional[str] = Field(default=None)
    parsed_trades_json: Optional[str] = Field(default=None)


class CalcRun(SQLModel, table=True):
    id: str = Field(default_factory=uuid4_str, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    status: str = Field(default="done", index=True)
    message: Optional[str] = Field(default=None)
    ocr_session_id: Optional[str] = Field(default=None, index=True)
    trades_json: str = Field(default="[]")
    results_json: str = Field(default="{}")
