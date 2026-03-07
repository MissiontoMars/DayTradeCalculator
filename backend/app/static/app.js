const uploadForm = document.getElementById("uploadForm");
const filesInput = document.getElementById("files");
const uploadStatus = document.getElementById("uploadStatus");
const warningsEl = document.getElementById("warnings");
const debugBtn = document.getElementById("debugBtn");
const debugEl = document.getElementById("debug");
const tradesEl = document.getElementById("trades");
const calcBtn = document.getElementById("calcBtn");
const resultsEl = document.getElementById("results");
const historyEl = document.getElementById("history");
const refreshHistoryBtn = document.getElementById("refreshHistory");

let currentOcrSessionId = null;

function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setStatus(msg) {
  uploadStatus.textContent = msg || "";
}

function renderWarnings(list) {
  if (!list || list.length === 0) {
    warningsEl.textContent = "";
    return;
  }
  warningsEl.textContent = list.map((w) => `- ${w}`).join("\n");
}

function setDebug(text) {
  const t = text || "";
  debugEl.textContent = t;
  debugEl.style.display = t ? "block" : "none";
}

function groupBySymbol(trades) {
  const m = new Map();
  for (const t of trades) {
    const sym = (t.symbol || "").toUpperCase();
    if (!m.has(sym)) m.set(sym, []);
    m.get(sym).push(t);
  }
  return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function makeTradeTable(trades) {
  const rows = trades
    .map((t, i) => {
      const ts = t.timestamp ? String(t.timestamp) : "";
      return `
      <tr data-row="${i}">
        <td contenteditable="true" data-field="symbol">${esc(t.symbol || "")}</td>
        <td>
          <select data-field="side">
            <option value="BUY" ${t.side === "BUY" ? "selected" : ""}>BUY</option>
            <option value="SELL" ${t.side === "SELL" ? "selected" : ""}>SELL</option>
          </select>
        </td>
        <td contenteditable="true" data-field="qty">${esc(t.qty ?? "")}</td>
        <td contenteditable="true" data-field="price">${esc(t.price ?? "")}</td>
        <td contenteditable="true" data-field="fee">${esc(t.fee ?? "0")}</td>
        <td contenteditable="true" data-field="timestamp">${esc(ts)}</td>
        <td class="muted">${esc(t.source || "")}</td>
      </tr>`;
    })
    .join("");

  return `
    <table class="tradeTable">
      <thead>
        <tr>
          <th>股票代码</th>
          <th>Side</th>
          <th>Qty</th>
          <th>Price</th>
          <th>Fee</th>
          <th>Timestamp(可空)</th>
          <th>来源</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderTrades(trades) {
  if (!trades || trades.length === 0) {
    tradesEl.innerHTML = `<div class="muted">暂无可计算订单</div>`;
    calcBtn.disabled = true;
    return;
  }
  const groups = groupBySymbol(trades);
  const blocks = groups
    .map(([sym, ts]) => {
      return `
        <div style="margin-top: 10px">
          <span class="tag">${esc(sym)}</span>
          <span class="muted">${ts.length} 笔</span>
          ${makeTradeTable(ts)}
        </div>
      `;
    })
    .join("");
  tradesEl.innerHTML = blocks;
  calcBtn.disabled = false;
}

function readTradesFromTables() {
  const tables = document.querySelectorAll(".tradeTable");
  const out = [];
  for (const table of tables) {
    const rows = table.querySelectorAll("tbody tr");
    for (const row of rows) {
      const getCell = (field) => row.querySelector(`[data-field="${field}"]`);
      const symbol = (getCell("symbol")?.textContent || "").trim();
      const side = getCell("side")?.value || "BUY";
      const qty = parseInt((getCell("qty")?.textContent || "").trim(), 10);
      const price = (getCell("price")?.textContent || "").trim();
      const fee = (getCell("fee")?.textContent || "0").trim();
      const timestamp = (getCell("timestamp")?.textContent || "").trim();

      if (!symbol) continue;
      if (!Number.isFinite(qty) || qty <= 0) continue;
      out.push({
        symbol,
        side,
        qty,
        price,
        fee,
        timestamp: timestamp ? timestamp : null,
      });
    }
  }
  return out;
}

function renderResults(res) {
  if (!res || res.length === 0) {
    resultsEl.innerHTML = `<div class="muted">暂无结果</div>`;
    return;
  }
  const rows = res
    .map((r) => {
      return `
        <tr>
          <td>${esc(r.symbol)}</td>
          <td>${esc(r.realized_pnl)}</td>
          <td>${esc(r.net_shares)}</td>
          <td>${esc(JSON.stringify(r.open_lots))}</td>
        </tr>
      `;
    })
    .join("");
  resultsEl.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>股票代码</th>
          <th>已实现收益</th>
          <th>净持仓</th>
          <th>未平仓Lots</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function refreshHistory() {
  const r = await fetch("/api/runs");
  if (!r.ok) return;
  const rows = await r.json();
  if (!rows || rows.length === 0) {
    historyEl.innerHTML = `<div class="muted">暂无历史记录</div>`;
    return;
  }
  historyEl.innerHTML = rows
    .map((x) => {
      return `<div style="margin: 6px 0">
        <a href="#" data-run="${esc(x.id)}">${esc(x.id)}</a>
        <span class="muted">${esc(x.created_at)} ${esc(x.status)}</span>
      </div>`;
    })
    .join("");

  historyEl.querySelectorAll("a[data-run]").forEach((a) => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = a.getAttribute("data-run");
      const rr = await fetch(`/api/runs/${id}`);
      if (!rr.ok) return;
      const detail = await rr.json();
      renderResults(detail.results || []);
    });
  });
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const files = filesInput.files;
  if (!files || files.length === 0) return;

  setStatus("识别中…");
  renderWarnings([]);
  setDebug("");
  debugBtn.disabled = true;
  tradesEl.innerHTML = "";
  resultsEl.innerHTML = "";
  calcBtn.disabled = true;

  const fd = new FormData();
  for (const f of files) fd.append("files", f);

  const r = await fetch("/api/ocr", { method: "POST", body: fd });
  if (!r.ok) {
    const t = await r.text();
    setStatus(`识别失败: ${t}`);
    return;
  }
  const data = await r.json();
  currentOcrSessionId = data.ocr_session_id;
  setStatus(`识别完成: ${files.length} 张截图`);
  renderWarnings(data.warnings || []);
  renderTrades(data.trades || []);
  debugBtn.disabled = false;
});

debugBtn.addEventListener("click", async () => {
  if (!currentOcrSessionId) return;
  const r = await fetch(`/api/ocr-sessions/${currentOcrSessionId}`);
  if (!r.ok) {
    setDebug("调试信息获取失败");
    return;
  }
  const data = await r.json();
  const images = (data.raw_ocr && data.raw_ocr.images) || [];
  const lines = [];
  for (const img of images) {
    lines.push(`== ${img.file} ==`);
    const ls = img.lines || [];
    for (const l of ls) lines.push(l);
    lines.push("");
  }
  setDebug(lines.join("\n").trim());
});

calcBtn.addEventListener("click", async () => {
  const trades = readTradesFromTables();
  if (!trades || trades.length === 0) return;
  const payload = { ocr_session_id: currentOcrSessionId, trades };
  const r = await fetch("/api/calc", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const t = await r.text();
    resultsEl.innerHTML = `<div class="warnings">计算失败: ${esc(t)}</div>`;
    return;
  }
  const data = await r.json();
  renderResults(data.results || []);
  await refreshHistory();
});

refreshHistoryBtn.addEventListener("click", async () => {
  await refreshHistory();
});

refreshHistory();
