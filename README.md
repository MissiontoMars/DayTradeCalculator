# 美股做T收益计算器（本地 Web 应用）

本项目在 MacOS 本地运行，通过浏览器使用。支持上传多张交易历史截图，后端用本地 OCR 模型识别订单行，并按股票分组做精准已实现收益计算，同时保存每次计算历史。

## 功能

- 多截图上传：一次上传多张交易历史截图
- 本地识别：优先使用 macOS Vision OCR（可选），否则回退 RapidOCR(ONNXRuntime)
- 多股票区分：识别到的订单按 Symbol 分组，分别计算
- 精确计算：使用 `Decimal` + FIFO 匹配，支持买/卖与卖空/回补
- 计算历史：每次计算会写入本地 SQLite

## 本地运行（MacOS）

```bash
cd /Users/wanxing/work/code/TT
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
export FINNHUB_TOKEN=你的token
cd backend
uvicorn app.main:app --reload --port 8000
```

### 可选：启用 macOS Vision OCR（更稳，推荐）

```bash
cd /Users/wanxing/work/code/TT
source backend/.venv/bin/activate
pip install -r backend/requirements-macos-vision.txt
```

浏览器打开：

- http://127.0.0.1:8000/
- 实时行情页：http://127.0.0.1:8000/quotes

## 使用方式

1. 上传多张截图，点击“识别订单”
2. 在表格里校对/修正识别结果（Symbol/BUY-SELL/Qty/Price/Fee/Timestamp）
3. 点击“计算收益”
4. 在“计算历史”里查看之前的结果

## 运行单元测试

```bash
cd /Users/wanxing/work/code/TT
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m unittest -v tests/test_pnl.py
PYTHONPATH=. python -m unittest -v tests/test_parse_pair.py
```

## 数据存放位置

- SQLite：`backend/app/data/app.db`
- 上传截图：`backend/app/data/images/<ocr_session_id>/`
