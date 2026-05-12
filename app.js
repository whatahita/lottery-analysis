const API_BASE = window.location.origin.startsWith("http")
  ? window.location.origin
  : "http://127.0.0.1:8000";

const LOTTERIES = [
  { key: "ssq", name: "双色球" },
  { key: "kl8", name: "快乐8" },
  { key: "fc3d", name: "福彩3D" },
];

const state = {
  lottery: "ssq",
  windowSize: 30,
  draws: [],
  stats: null,
  recommendation: null,
};

const $ = (id) => document.getElementById(id);

function init() {
  $("lotteryTabs").innerHTML = LOTTERIES.map(
    (item) => `<button data-lottery="${item.key}">${item.name}</button>`
  ).join("");

  $("lotteryTabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-lottery]");
    if (!button) return;
    state.lottery = button.dataset.lottery;
    load();
  });

  $("windowChoices").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-window]");
    if (!button) return;
    state.windowSize = Number(button.dataset.window);
    load();
  });

  $("refreshButton").addEventListener("click", load);
  $("syncButton").addEventListener("click", sync);
  load();
}

async function fetchJson(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "请求失败");
  return payload;
}

async function load() {
  setError("");
  renderTabs();
  renderTitle();
  try {
    const [drawPayload, statPayload, recPayload] = await Promise.all([
      fetchJson(`/api/lottery/${state.lottery}/draws?limit=200`),
      fetchJson(`/api/lottery/${state.lottery}/stats?window=${state.windowSize}`),
      fetchJson(`/api/lottery/${state.lottery}/recommend?count=5&window=${state.windowSize}`).catch(() => null),
    ]);
    state.draws = drawPayload.draws;
    state.stats = statPayload;
    state.recommendation = recPayload;
    render();
  } catch (error) {
    setError(error.message);
  }
}

async function sync() {
  const button = $("syncButton");
  button.disabled = true;
  button.textContent = "同步中";
  setError("");
  try {
    await fetchJson(`/api/lottery/${state.lottery}/sync?page_size=120`, { method: "POST" });
    await load();
  } catch (error) {
    setError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "同步官方数据";
  }
}

function render() {
  renderTabs();
  renderTitle();
  const stats = state.stats || {};
  $("metricDraws").textContent = stats.draw_count || state.draws.length || 0;
  $("metricRecent").textContent = stats.recent_count || 0;
  $("metricAvg").textContent = stats.summary?.avg_sum || 0;
  $("metricOddEven").textContent = formatOddEven(stats.summary?.odd || 0, stats.summary?.even || 0);
  renderNumberList("hotList", stats.hot || [], "hot");
  renderNumberList("coldList", stats.cold || [], "cold");
  renderOmission(stats.omission || []);
  renderRecommendations(state.recommendation?.recommendations || []);
  renderDrawTable();
  renderTrendChart(stats.trend || []);
  renderZoneChart(stats.summary?.zones || []);
}

function renderTabs() {
  document.querySelectorAll("#lotteryTabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.lottery === state.lottery);
  });
  document.querySelectorAll("#windowChoices button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.window) === state.windowSize);
  });
}

function renderTitle() {
  const selected = LOTTERIES.find((item) => item.key === state.lottery);
  $("lotteryKey").textContent = selected.key;
  $("pageTitle").textContent = `${selected.name} 历史走势与统计`;
}

function renderNumberList(id, rows, tone) {
  $(id).innerHTML = rows.map((item) => (
    `<span class="${tone}Item"><b>${item.number}</b><small>${item.count}次</small></span>`
  )).join("");
}

function renderOmission(rows) {
  const misses = rows.map((item) => item.miss);
  const high = percentile(misses, 0.75);
  const mid = percentile(misses, 0.45);
  $("omissionList").innerHTML = rows.map((item) => (
    `<span class="missCell ${missClass(item, mid, high)}">
      <b>${item.number}</b>
      <small>${item.miss}</small>
      <i style="height:${Math.min(100, item.miss * 7)}%"></i>
    </span>`
  )).join("");
}

function renderRecommendations(rows) {
  $("recommendations").innerHTML = rows.length
    ? rows.map((item, index) => `
      <div class="rec">
        <div class="recTop"><strong>第 ${index + 1} 组</strong><span>${formatScore(item.score)} 分</span></div>
        ${balls(item.numbers, item.special)}
        <ul>${item.reasons.map((reason) => `<li>${reason}</li>`).join("")}</ul>
      </div>
    `).join("")
    : `<p class="empty">暂无推荐，请先同步开奖数据。</p>`;
}

function renderDrawTable() {
  $("drawTable").innerHTML = state.draws.map((draw) => `
    <tr>
      <td>${draw.issue}</td>
      <td>${draw.draw_date}</td>
      <td>${balls(draw.numbers.map(formatBall), (draw.special || []).map(formatBall))}</td>
      <td>${draw.source}</td>
    </tr>
  `).join("");
}

function balls(numbers, special = []) {
  return `<div class="balls">${
    numbers.map((num) => `<span class="ball">${num}</span>`).join("")
  }${
    special.map((num) => `<span class="ball special">${num}</span>`).join("")
  }</div>`;
}

function formatBall(value) {
  const text = String(value);
  return state.lottery === "fc3d" ? text : text.padStart(2, "0");
}

function formatOddEven(odd, even) {
  const total = odd + even;
  if (!total) return "0% / 0%";
  return `${Math.round((odd / total) * 100)}% / ${Math.round((even / total) * 100)}%`;
}

function formatScore(score) {
  const value = Number(score) || 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function renderTrendChart(rows) {
  const data = rows.map((item) => ({ label: item.issue, value: item.sum, span: item.span }));
  drawLineChart($("trendChart"), data, "#0f766e");
}

function renderZoneChart(rows) {
  drawBarChart($("zoneChart"), rows.map((item) => ({ label: item.label, value: item.count })), "#2563eb");
}

function drawLineChart(el, data, color) {
  if (!data.length) {
    el.innerHTML = `<p class="empty">暂无数据</p>`;
    return;
  }

  const width = 720;
  const height = 300;
  const pad = { left: 48, right: 20, top: 32, bottom: 46 };
  const values = data.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const ticks = buildTicks(min, max, 4);
  const scaleX = (index) => pad.left + (index * (width - pad.left - pad.right)) / Math.max(data.length - 1, 1);
  const scaleY = (value) => height - pad.bottom - ((value - min) * (height - pad.top - pad.bottom)) / Math.max(max - min, 1);
  const points = data.map((item, index) => `${scaleX(index)},${scaleY(item.value)}`).join(" ");
  const area = `${pad.left},${height - pad.bottom} ${points} ${width - pad.right},${height - pad.bottom}`;
  const latest = data[data.length - 1];

  el.innerHTML = `
    <div class="chartSummary">
      <span>最新和值 <b>${latest.value}</b></span>
      <span>最低 <b>${min}</b></span>
      <span>最高 <b>${max}</b></span>
    </div>
    <svg viewBox="0 0 ${width} ${height}" role="img" class="trendSvg">
      <defs>
        <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.22" />
          <stop offset="100%" stop-color="${color}" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      ${ticks.map((tick) => `
        <line x1="${pad.left}" y1="${scaleY(tick)}" x2="${width - pad.right}" y2="${scaleY(tick)}" class="gridLine" />
        <text x="${pad.left - 10}" y="${scaleY(tick) + 4}" class="axisText" text-anchor="end">${tick}</text>
      `).join("")}
      <polyline points="${area}" fill="url(#trendFill)" stroke="none" />
      <polyline points="${points}" fill="none" stroke="${color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
      ${data.map((item, index) => `<circle cx="${scaleX(index)}" cy="${scaleY(item.value)}" r="${index === data.length - 1 ? 5 : 3}" fill="${index === data.length - 1 ? "#f59e0b" : color}" stroke="#fff" stroke-width="2"><title>${item.label}: ${item.value}</title></circle>`).join("")}
      <text x="${pad.left}" y="${height - 14}" class="axisText">${data[0].label}</text>
      <text x="${width - pad.right}" y="${height - 14}" class="axisText" text-anchor="end">${latest.label}</text>
    </svg>
  `;
}

function drawBarChart(el, data, color) {
  if (!data.length) {
    el.innerHTML = `<p class="empty">暂无数据</p>`;
    return;
  }

  const width = 720;
  const height = 300;
  const pad = { left: 38, right: 22, top: 34, bottom: 48 };
  const max = Math.max(...data.map((item) => item.value), 1);
  const slot = (width - pad.left - pad.right) / data.length;
  const barWidth = Math.max(34, slot - 24);

  el.innerHTML = `
    <div class="chartSummary">
      ${data.map((item) => `<span>${item.label} <b>${item.value}</b></span>`).join("")}
    </div>
    <svg viewBox="0 0 ${width} ${height}" role="img" class="barSvg">
      <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" class="axis" />
      ${data.map((item, index) => {
        const x = pad.left + index * slot + (slot - barWidth) / 2;
        const railHeight = height - pad.top - pad.bottom;
        const barHeight = (item.value / max) * railHeight;
        const y = height - pad.bottom - barHeight;
        return `<rect x="${x}" y="${pad.top}" width="${barWidth}" height="${railHeight}" class="barRail" rx="8"></rect>
          <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="8"><title>${item.label}: ${item.value}</title></rect>
          <text x="${x + barWidth / 2}" y="${y - 8}" class="barValue" text-anchor="middle">${item.value}</text>
          <text x="${x + barWidth / 2}" y="${height - 16}" class="axisText" text-anchor="middle">${item.label}</text>`;
      }).join("")}
    </svg>
  `;
}

function buildTicks(min, max, count) {
  if (min === max) return [min];
  const step = (max - min) / count;
  return Array.from({ length: count + 1 }, (_, index) => Math.round(min + step * index));
}

function percentile(values, ratio) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor((sorted.length - 1) * ratio)];
}

function missClass(item, mid, high) {
  if (item.latest) return "latest";
  if (item.miss >= high) return "missHigh";
  if (item.miss >= mid) return "missMid";
  return "missLow";
}

function setError(message) {
  $("errorBox").textContent = message;
  $("errorBox").classList.toggle("hidden", !message);
}

init();
