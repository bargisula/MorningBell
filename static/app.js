/* 晨鐘 MorningBell 前端（vanilla JS，無框架） */
"use strict";

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function pctSpan(pct) {
  if (pct === null || pct === undefined) return '<span class="pct flat">—</span>';
  const cls = pct > 0.05 ? "up" : pct < -0.05 ? "down" : "flat";
  const sign = pct > 0 ? "+" : "";
  return `<span class="pct ${cls}">${sign}${pct.toFixed(2)}%</span>`;
}

/* Demo 模式：清單存在訪客自己的瀏覽器（localStorage），不經過伺服器 */
let DEMO = false;

const store = {
  KEY: "morningbell.watchlist",
  read() {
    try { return JSON.parse(localStorage.getItem(this.KEY)) || []; }
    catch (_) { return []; }
  },
  write(list) { localStorage.setItem(this.KEY, JSON.stringify(list)); },
  tickers() { return this.read().map((w) => w.ticker); },
};

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let msg = `伺服器回應 ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ── 分頁切換 ─────────────────────── */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#panel-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "watchlist") loadWatchlist();
  });
});

/* ── 今日晨報 ─────────────────────── */
function renderBrief(b) {
  const light = b.light || {};
  const d = light.details || {};
  let html = `
    <p class="brief-date">${esc(b.date_label)}</p>
    ${b.market_note ? `<p class="market-note">${esc(b.market_note)}</p>` : ""}
    ${b.is_stale ? `<p class="stale-note">⚠ 行情資料日期為 ${esc(b.trade_date)}，可能不是最新。</p>` : ""}

    <div class="section-label">市場晨燈</div>
    <div class="card lamp-card">
      <div class="lamp ${esc(light.color || "unknown")}" aria-hidden="true"></div>
      <div>
        <div class="lamp-title">${esc(light.title || "")}</div>
        <div class="lamp-reason">${esc(light.reason || "")}</div>
        ${d.vix !== undefined ? `<div class="lamp-detail">S&amp;P 500 ${d.trend_up ? "高於" : "低於"}長期趨勢線 ${Math.abs(d.trend_gap_pct)}%　·　恐慌指數 VIX ${d.vix}</div>` : ""}
      </div>
    </div>

    <div class="section-label">昨夜盤勢</div>
    <div class="card">
      <p class="headline">${esc(b.headline)}</p>
      ${(b.indices || []).map((i) => `
        <div class="index-row">
          <span class="idx-name">${esc(i.name)}</span>
          <span class="idx-close">${i.close ?? "—"}</span>
          ${pctSpan(i.pct)}
        </div>`).join("")}
    </div>`;

  if (b.ai_narrative) {
    html += `
    <div class="ai-block"><span class="ai-tag">AI 主持人為你導讀</span>${esc(b.ai_narrative)}</div>`;
  }

  html += `<div class="section-label">你的清單</div>`;
  if ((b.watchlist || []).length === 0) {
    html += `<div class="card"><p class="empty">你還沒有加入任何股票。到「觀察清單」加幾支，明天的晨報就會自動幫你盯著。</p></div>`;
  } else {
    html += `<div class="card">${b.watchlist.map((w) => `
      <div class="watch-row">
        <span class="watch-ticker">${esc(w.ticker)}</span>
        <span class="watch-name">${esc(w.name)}</span>
        <span class="idx-close">${w.price ?? ""}</span>
        ${pctSpan(w.pct)}
        <span class="watch-note">${esc(w.note)}</span>
      </div>`).join("")}</div>`;
  }

  html += `<div class="section-label">接下來的大事</div>`;
  if ((b.events || []).length === 0) {
    html += `<div class="card"><p class="empty">未來十天，你清單裡的公司沒有排定的財報。</p></div>`;
  } else {
    html += `<div class="card">${b.events.map((e) => `
      <div class="index-row"><span>${esc(e.ticker)} ${esc(e.name)}</span><span class="idx-close">${esc(e.label)}</span></div>`).join("")}</div>`;
  }

  $("#panel-brief").innerHTML = html;
}

async function loadBrief() {
  try {
    let path = "/api/brief";
    if (DEMO && store.tickers().length) {
      path += "?tickers=" + encodeURIComponent(store.tickers().join(","));
    }
    renderBrief(await api(path));
  } catch (err) {
    $("#panel-brief").innerHTML =
      `<div class="error-box">晨報載入失敗：${esc(err.message)}<br>請確認網路後重新整理頁面。</div>`;
  }
}

/* ── 個股健檢 ─────────────────────── */
function checkCard(title, card, body) {
  return `
    <div class="card check-card">
      <div class="card-title">${title}</div>
      <div class="verdict"><span class="emoji">${esc(card.emoji)}</span>${esc(card.headline)}</div>
      ${body}
    </div>`;
}

function renderCheckup(c) {
  const v = c.cards.valuation, q = c.cards.quality, f = c.cards.flags;
  const vBody = v.details.length ? `
    <details><summary>看細節</summary>
      ${v.details.map((d) => `
        <div class="detail-row">
          <span class="detail-label">${esc(d.label)}</span>
          <span class="detail-value">${esc(d.value)}</span>
          <span class="detail-note">${esc(d.note)}</span>
        </div>`).join("")}
    </details>` : "";
  const qBody = q.checks.length ? `
    <details><summary>看五項體檢</summary>
      ${q.checks.map((k) => `
        <div class="detail-row">
          <span class="detail-label ${k.passed ? "check-pass" : "check-fail"}">${k.passed ? "✓" : "✗"} ${esc(k.label)}</span>
          <span class="detail-note">${esc(k.note)}</span>
        </div>`).join("")}
    </details>` : "";
  const fBody = f.items.length
    ? f.items.map((i) => `<div class="flag-item">🚩 ${esc(i)}</div>`).join("")
    : "";

  $("#checkup-result").innerHTML = `
    <div class="stock-head">
      <strong>${esc(c.ticker)}</strong> ${esc(c.name)}
      <span class="price">${c.price} ${esc(c.currency)}</span> ${pctSpan(c.pct)}
    </div>
    ${checkCard("貴不貴", v, vBody)}
    ${checkCard("體質好不好", q, qBody)}
    ${checkCard("有沒有紅旗", f, fBody)}
    <p class="disclaimer">${esc(c.disclaimer)}</p>`;
}

$("#checkup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticker = $("#checkup-input").value.trim();
  if (!ticker) return;
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  $("#checkup-result").innerHTML = `<div class="loading">正在幫 ${esc(ticker.toUpperCase())} 做健檢⋯</div>`;
  try {
    renderCheckup(await api(`/api/checkup/${encodeURIComponent(ticker)}`));
  } catch (err) {
    $("#checkup-result").innerHTML = `<div class="error-box">${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
});

/* ── 觀察清單 ─────────────────────── */
function renderWatchlist(list) {
  $("#watch-list").innerHTML = list.length
    ? list.map((w) => `
        <div class="wl-row">
          <strong>${esc(w.ticker)}</strong>
          <span class="watch-name">${esc(w.name || "")}</span>
          <button data-ticker="${esc(w.ticker)}">移除</button>
        </div>`).join("")
    : `<p class="empty">清單是空的。加入第一支你關心的股票吧。</p>`;
  document.querySelectorAll(".wl-row button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (DEMO) {
        store.write(store.read().filter((w) => w.ticker !== btn.dataset.ticker));
      } else {
        await api(`/api/watchlist/${btn.dataset.ticker}`, { method: "DELETE" });
      }
      loadWatchlist();
    });
  });
}

async function loadWatchlist() {
  try {
    renderWatchlist(DEMO ? store.read() : await api("/api/watchlist"));
  } catch (err) {
    $("#watch-list").innerHTML = `<div class="error-box">${esc(err.message)}</div>`;
  }
}

$("#watch-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#watch-input");
  const ticker = input.value.trim();
  if (!ticker) return;
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  try {
    if (DEMO) {
      const found = await api(`/api/lookup/${encodeURIComponent(ticker)}`);
      const list = store.read().filter((w) => w.ticker !== found.ticker);
      list.push(found);
      store.write(list);
    } else {
      await api("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
    }
    input.value = "";
    loadWatchlist();
  } catch (err) {
    $("#watch-list").insertAdjacentHTML("afterbegin",
      `<div class="error-box">${esc(err.message)}</div>`);
    setTimeout(() => document.querySelector("#watch-list .error-box")?.remove(), 4000);
  } finally {
    btn.disabled = false;
  }
});

/* ── 啟動 ─────────────────────────── */
(async () => {
  try {
    DEMO = (await api("/api/config")).demo === true;
  } catch (_) { /* config 拿不到就當本機模式 */ }
  if (DEMO) {
    $("#panel-watchlist .hint").textContent =
      "清單存在你這台裝置的瀏覽器裡，不會上傳，也只有你看得到。";
  }
  loadBrief();
  loadWatchlist();
})();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js", { scope: "/" })
    .catch((err) => console.warn("Service worker 註冊失敗：", err));
}
