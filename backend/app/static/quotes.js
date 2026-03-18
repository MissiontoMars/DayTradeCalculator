const quotesEl = document.getElementById("quotes");
const quoteErrorEl = document.getElementById("quoteError");
const updatedAtEl = document.getElementById("updatedAt");
const countdownEl = document.getElementById("countdown");
const dataLagEl = document.getElementById("dataLag");

const LEVERAGE = 2;
const RKLB_RANGE = 1;
const REFRESH_SECONDS = 10;

function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmt2(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return Number(n).toFixed(2);
}

function fmtPct(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return `${Number(n).toFixed(2)}%`;
}

function setError(msg) {
  quoteErrorEl.textContent = msg || "";
}

function renderTable(rklb, rklx) {
  const rklbC = Number(rklb.c);
  const rklxC = Number(rklx.c);

  const rklbDown = rklbC - RKLB_RANGE;
  const rklbUp = rklbC + RKLB_RANGE;

  const pctDown = rklbC > 0 ? rklbDown / rklbC - 1 : 0;
  const pctUp = rklbC > 0 ? rklbUp / rklbC - 1 : 0;

  const rklxDown = rklxC * (1 + LEVERAGE * pctDown);
  const rklxUp = rklxC * (1 + LEVERAGE * pctUp);

  return `
    <table>
      <thead>
        <tr>
          <th>标的</th>
          <th>当前价</th>
          <th>涨跌额</th>
          <th>涨跌幅</th>
          <th>RKLB - $${esc(RKLB_RANGE)}</th>
          <th>RKLB + $${esc(RKLB_RANGE)}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>RKLB</td>
          <td>${esc(fmt2(rklbC))}</td>
          <td>${esc(fmt2(rklb.d))}</td>
          <td>${esc(fmtPct(rklb.dp))}</td>
          <td>${esc(fmt2(rklbDown))}</td>
          <td>${esc(fmt2(rklbUp))}</td>
        </tr>
        <tr>
          <td>RKLX (2x)</td>
          <td>${esc(fmt2(rklxC))}</td>
          <td>${esc(fmt2(rklx.d))}</td>
          <td>${esc(fmtPct(rklx.dp))}</td>
          <td>${esc(fmt2(rklxDown))}</td>
          <td>${esc(fmt2(rklxUp))}</td>
        </tr>
      </tbody>
    </table>
    <div class="muted" style="margin-top: 8px">
      说明：RKLX 的两个目标价按线性近似计算：RKLX_target = RKLX_now × (1 + 2 × (RKLB_target / RKLB_now − 1))
    </div>
  `;
}

async function fetchQuotes() {
  const r = await fetch("/api/quotes?symbols=RKLB,RKLX");
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `HTTP ${r.status}`);
  }
  return await r.json();
}

async function tick() {
  try {
    const data = await fetchQuotes();
    const q = data.quotes || {};
    const rklb = q.RKLB;
    const rklx = q.RKLX;
    if (!rklb || !rklx) throw new Error("缺少 RKLB/RKLX 行情数据");
    const tRklb = Number(rklb.t);
    const tRklx = Number(rklx.t);
    const t = Math.max(tRklb || 0, tRklx || 0);
    setError("");
    quotesEl.innerHTML = renderTable(rklb, rklx);
    const now = new Date();
    updatedAtEl.textContent = `更新时间：${now.toLocaleString()}`;
    if (dataLagEl) {
      const ts = t ? new Date(t * 1000) : null;
      dataLagEl.textContent = ts ? `（数据时间：${ts.toLocaleTimeString()}）` : "";
    }
    if (t) {
      lastDataT = t;
    }
  } catch (e) {
    setError(`获取行情失败：${e && e.message ? e.message : String(e)}`);
  }
}

let remain = REFRESH_SECONDS;
let lastDataT = null;
let sinceLastData = null;

function renderCountdown() {
  if (!countdownEl) return;
  const lagText =
    typeof sinceLastData === "number" ? `，距数据上次更新 ${sinceLastData}s` : "";
  countdownEl.textContent = `（${remain}s 后刷新${lagText}）`;
}

async function refreshNow() {
  remain = REFRESH_SECONDS;
  renderCountdown();
  await tick();
}

renderCountdown();
refreshNow();

setInterval(() => {
  remain = Math.max(0, remain - 1);
  if (lastDataT) {
    const nowSec = Math.floor(Date.now() / 1000);
    sinceLastData = Math.max(0, nowSec - lastDataT);
  } else {
    sinceLastData = null;
  }
  renderCountdown();
  if (remain === 0) {
    refreshNow();
  }
}, 1000);
