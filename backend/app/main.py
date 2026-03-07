from __future__ import annotations

import io
import os
from decimal import Decimal
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from sqlmodel import Session, select

from .calc.pnl import Trade as CalcTrade
from .calc.pnl import compute_realized_pnl, lots_to_json
from .db import engine, init_db
from .models import CalcRun, OcrSession
from .ocr.engine import engine as ocr_engine
from .ocr.dedup import dedup_trades
from .ocr.parse import cluster_ocr_lines, parse_ocr_items
from .schemas import (
    CalcRequest,
    CalcResponse,
    CalcRunDetail,
    CalcRunSummary,
    OcrResponse,
    SymbolResult,
    TradeInput,
)
from .util import json_dumps, json_loads, utcnow


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")


app = FastAPI(title="美股做T收益计算器")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def _startup() -> None:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def _save_upload(session_id: str, idx: int, up: UploadFile) -> tuple[str, bytes]:
    raw = up.file.read()
    ext = os.path.splitext(up.filename or "")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    sess_dir = os.path.join(IMAGES_DIR, session_id)
    os.makedirs(sess_dir, exist_ok=True)
    path = os.path.join(sess_dir, f"{idx:03d}{ext}")
    with open(path, "wb") as f:
        f.write(raw)
    return path, raw


@app.post("/api/ocr", response_model=OcrResponse)
def ocr_images(files: list[UploadFile] = File(...)) -> Any:
    if not files:
        raise HTTPException(status_code=400, detail="未上传截图")

    with Session(engine) as session:
        ocr_session = OcrSession(status="processing")
        session.add(ocr_session)
        session.commit()
        session.refresh(ocr_session)

        image_paths: list[str] = []
        items_by_image: list[tuple[str, list[dict[str, Any]]]] = []
        raw_ocr: dict[str, Any] = {"engine": getattr(ocr_engine, "engine_name", None), "images": []}

        for idx, up in enumerate(files, start=1):
            path, raw = _save_upload(ocr_session.id, idx, up)
            image_paths.append(path)
            try:
                img = Image.open(io.BytesIO(raw))
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"图片无法读取: {up.filename}: {e}") from e

            items = ocr_engine.ocr(img)
            items_by_image.append((os.path.basename(path), items))
            raw_ocr["images"].append(
                {
                    "file": os.path.basename(path),
                    "items": items,
                    "lines": cluster_ocr_lines(items),
                }
            )

        trades, warnings = parse_ocr_items(items_by_image)
        trade_inputs = [
            TradeInput(
                symbol=t.symbol,
                side=t.side,  # type: ignore[arg-type]
                qty=t.qty,
                price=t.price,
                fee=t.fee,
                timestamp=t.timestamp,
                source=t.source,
            )
            for t in trades
        ]

        deduped, removed = dedup_trades(trade_inputs)
        if removed:
            warnings.append(f"检测到重复订单 {len(removed)} 笔，已自动去重（按股票代码+价格+股数+成交时间）")
        trade_inputs = deduped

        ocr_session.status = "done"
        ocr_session.image_paths_json = json_dumps(image_paths)
        ocr_session.raw_ocr_json = json_dumps(raw_ocr)
        ocr_session.parsed_trades_json = json_dumps([ti.model_dump() for ti in trade_inputs])
        ocr_session.message = None if trade_inputs else "未识别到可解析的订单行"

        session.add(ocr_session)
        session.commit()

        return OcrResponse(
            ocr_session_id=ocr_session.id,
            status=ocr_session.status,
            message=ocr_session.message,
            trades=trade_inputs,
            warnings=warnings,
        )


@app.get("/api/ocr-sessions/{ocr_session_id}")
def get_ocr_session(ocr_session_id: str) -> Any:
    with Session(engine) as session:
        row = session.get(OcrSession, ocr_session_id)
        if not row:
            raise HTTPException(status_code=404, detail="未找到 OCR 记录")
        return {
            "id": row.id,
            "created_at": row.created_at,
            "status": row.status,
            "message": row.message,
            "image_paths": json_loads(row.image_paths_json) or [],
            "raw_ocr": json_loads(row.raw_ocr_json) or {},
            "parsed_trades": json_loads(row.parsed_trades_json) or [],
        }


@app.post("/api/calc", response_model=CalcResponse)
def calc_profit(req: CalcRequest = Body(...)) -> Any:
    if not req.trades:
        raise HTTPException(status_code=400, detail="没有可计算的订单")

    by_symbol: dict[str, list[TradeInput]] = {}
    for t in req.trades:
        sym = t.symbol.strip().upper()
        by_symbol.setdefault(sym, []).append(t.model_copy(update={"symbol": sym}))

    results: list[SymbolResult] = []
    for sym, trades in by_symbol.items():
        indexed = list(enumerate(trades))
        sorted_trades = [
            t
            for _i, t in sorted(
                indexed,
                key=lambda it: (0, it[1].timestamp, it[0]) if it[1].timestamp else (1, None, it[0]),
            )
        ]
        calc_trades = [
            CalcTrade(
                symbol=sym,
                side=t.side,
                qty=t.qty,
                price=t.price,
                fee=t.fee,
                timestamp_key=(t.timestamp.isoformat() if t.timestamp else None),
                source=t.source,
            )
            for t in sorted_trades
        ]
        realized, net_shares, lots = compute_realized_pnl(calc_trades)
        results.append(
            SymbolResult(
                symbol=sym,
                realized_pnl=realized.quantize(Decimal("0.0001")),
                net_shares=net_shares,
                open_lots=lots_to_json(lots),
            )
        )

    results.sort(key=lambda r: r.symbol)

    with Session(engine) as session:
        run = CalcRun(
            status="done",
            ocr_session_id=req.ocr_session_id,
            trades_json=json_dumps([t.model_dump() for t in req.trades]),
            results_json=json_dumps([r.model_dump() for r in results]),
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        return CalcResponse(run_id=run.id, created_at=run.created_at, results=results)


@app.get("/api/runs", response_model=list[CalcRunSummary])
def list_runs() -> Any:
    with Session(engine) as session:
        rows = session.exec(select(CalcRun).order_by(CalcRun.created_at.desc()).limit(50)).all()
        return [
            CalcRunSummary(id=r.id, created_at=r.created_at, status=r.status, message=r.message) for r in rows
        ]


@app.get("/api/runs/{run_id}", response_model=CalcRunDetail)
def get_run(run_id: str) -> Any:
    with Session(engine) as session:
        run = session.get(CalcRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="未找到记录")

        trades_raw = json_loads(run.trades_json) or []
        results_raw = json_loads(run.results_json) or []
        trades = [TradeInput(**t) for t in trades_raw]
        results = [SymbolResult(**r) for r in results_raw]

        return CalcRunDetail(
            id=run.id,
            created_at=run.created_at,
            status=run.status,
            message=run.message,
            ocr_session_id=run.ocr_session_id,
            trades=trades,
            results=results,
        )
