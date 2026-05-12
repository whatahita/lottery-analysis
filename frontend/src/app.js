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
  $("metricOddEven").textContent = `${stats.summary?.odd || 0}:${stats.summary?.even || 0}`;
  renderNumberList("hotList", stats.hot || []);
  renderNumberList("coldList", stats.cold || []);
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

function renderNumberList(id, rows) {
  $(id).innerHTML = rows.map((item) => (
    `<span><b>${item.number}</b><small>${item.count}次</small></span>`
  )).join("");
}

function renderOmission(rows) {
  $("omissionList").innerHTML = rows.map((item) => (
    `<span class="${item.latest ? "latest" : ""}">${item.number}<small>${item.miss}</small></span>`
  )).join("");
}

function renderRecommendations(rows) {
  $("recommendations").innerHTML = rows.length
    ? rows.map((item, index) => `
      <div class="rec">
        <div class="recTop"><strong>第 ${index + 1} 组</strong><span>${item.score} 分</span></div>
        ${balls(item.numbers, item.special)}
        <ul>${item.reasons.map((reason) => `<li>${reason}</li>`).join("")}</ul>
      </div>
    `).join("")
    : `<p class="empty">暂无推荐，请先同步开奖数据。</p>`;
}

function renderDrawTable() {
  $("drawTable").innerHTML = state.draws.slice(0, 40).map((draw) => `
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

function renderTrendChart(rows) {
  const data = rows.map((item) => ({ label: item.issue, value: item.sum }));
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
  const height = 280;
  const pad = 34;
  const values = data.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const scaleX = (index) => pad + (index * (width - pad * 2)) / Math.max(data.length - 1, 1);
  const scaleY = (value) => height - pad - ((value - min) * (height - pad * 2)) / Math.max(max - min, 1);
  const points = data.map((item, index) => `${scaleX(index)},${scaleY(item.value)}`).join(" ");
  el.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img">
      <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="axis" />
      <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" class="axis" />
      <polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" />
      ${data.map((item, index) => `<circle cx="${scaleX(index)}" cy="${scaleY(item.value)}" r="3" fill="${color}"><title>${item.label}: ${item.value}</title></circle>`).join("")}
    </svg>
  `;
}

function drawBarChart(el, data, color) {
  if (!data.length) {
    el.innerHTML = `<p class="empty">暂无数据</p>`;
    return;
  }
  const width = 720;
  const height = 280;
  const pad = 34;
  const max = Math.max(...data.map((item) => item.value), 1);
  const barWidth = (width - pad * 2) / data.length - 16;
  el.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img">
      <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" class="axis" />
      ${data.map((item, index) => {
        const x = pad + index * ((width - pad * 2) / data.length) + 8;
        const barHeight = (item.value / max) * (height - pad * 2);
        const y = height - pad - barHeight;
        return `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${color}" rx="4"><title>${item.label}: ${item.value}</title></rect>
          <text x="${x + barWidth / 2}" y="${height - 10}" text-anchor="middle">${item.label}</text>`;
      }).join("")}
    </svg>
  `;
}

function setError(message) {
  $("errorBox").textContent = message;
  $("errorBox").classList.toggle("hidden", !message);
}

init();
