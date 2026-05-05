const state = {
  snapshot: null,
  query: "",
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 2,
});

const integer = new Intl.NumberFormat("en-US");
const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

const statusText = {
  new: "新增",
  increased: "增持",
  reduced: "减持",
  sold_out: "清仓",
  unchanged: "不变",
};

function $(id) {
  return document.getElementById(id);
}

function kindLabel(holding) {
  if (holding.put_call) return holding.put_call;
  return "Equity";
}

function tileClass(holding) {
  if (holding.put_call === "Call") return "call";
  if (holding.put_call === "Put") return "put";
  return "equity";
}

async function loadPortfolio(refresh = false) {
  const button = $("refreshButton");
  button.disabled = true;
  button.textContent = refresh ? "刷新中" : "读取中";

  try {
    const response = await fetch(`/api/portfolio${refresh ? "?refresh=1" : ""}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.snapshot = await response.json();
    render();
  } catch (error) {
    $("notice").hidden = false;
    $("notice").textContent = `读取失败：${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "刷新 SEC";
  }
}

function render() {
  const data = state.snapshot;
  const { summary } = data;
  const filing = data.latest_filing;

  $("totalValue").textContent = money.format(summary.total_value_usd);
  $("filingMeta").textContent = `报告期 ${filing.report_date} / 提交 ${filing.filing_date}`;
  $("positionCount").textContent = integer.format(summary.position_count);
  $("equityOptionCount").textContent = `${summary.equity_count} 普通股 / ${summary.option_count} 期权`;
  $("topFive").textContent = percent.format(summary.top_5_weight);
  $("topHolding").textContent = summary.top_holding
    ? `${summary.top_holding.issuer} ${percent.format(summary.top_holding.weight)}`
    : "最大持仓";
  $("optionWeight").textContent = percent.format(summary.option_weight);
  $("sourceLink").href = filing.sec_url || "https://data.sec.gov/submissions/CIK0002045724.json";

  $("notice").hidden = false;
  $("notice").textContent =
    data.warning ||
    `最新公开 13F 来自 SEC，抓取时间 ${new Date(data.fetched_at).toLocaleString()}。13F 有披露滞后，不能视作实时交易。`;

  renderTreemap(summary.holdings);
  renderSectors(summary.holdings);
  renderChanges(data.changes);
  renderTable(summary.holdings);
}

function renderTreemap(holdings) {
  $("treemap").innerHTML = holdings
    .slice(0, 24)
    .map((holding) => {
      const basis = Math.max(13, holding.weight * 100 * 1.8);
      const label = holding.ticker || holding.cusip;
      return `
        <div class="tile ${tileClass(holding)}" style="--grow:${Math.max(1, holding.weight * 100)}; --basis:${basis}%">
          <strong>${holding.issuer}</strong>
          <small>${label} / ${money.format(holding.value_usd)}</small>
          <small>${percent.format(holding.weight)} · ${kindLabel(holding)}</small>
        </div>
      `;
    })
    .join("");
}

function renderSectors(holdings) {
  const totals = new Map();
  const total = holdings.reduce((sum, holding) => sum + holding.value_usd, 0);
  for (const holding of holdings) {
    totals.set(holding.sector, (totals.get(holding.sector) || 0) + holding.value_usd);
  }

  $("sectorBars").innerHTML = Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([sector, value]) => `
      <div class="bar-row">
        <span>${sector}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(value / total) * 100}%"></div></div>
        <strong>${percent.format(value / total)}</strong>
      </div>
    `)
    .join("");
}

function renderChanges(changes) {
  $("changeList").innerHTML = changes
    .filter((change) => change.status !== "unchanged")
    .slice(0, 8)
    .map((change) => `
      <div class="change-item">
        <span class="tag ${change.status}">${statusText[change.status] || change.status}</span>
        <div>
          <strong>${change.issuer}</strong>
          <p>${change.cusip}</p>
        </div>
        <strong>${money.format(change.value_delta_usd)}</strong>
      </div>
    `)
    .join("");
}

function renderTable(holdings) {
  const query = state.query.trim().toLowerCase();
  const rows = holdings.filter((holding) => {
    if (!query) return true;
    return [holding.issuer, holding.cusip, holding.ticker || ""]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  $("holdingsTable").innerHTML = rows
    .map((holding) => `
      <tr>
        <td><span class="issuer">${holding.issuer}</span><br><small>${holding.class}</small></td>
        <td>${holding.ticker || "--"}</td>
        <td>${kindLabel(holding)}</td>
        <td>${money.format(holding.value_usd)}</td>
        <td>${percent.format(holding.weight)}</td>
        <td>${integer.format(holding.shares)}</td>
        <td>${holding.avg_reported_price ? money.format(holding.avg_reported_price) : "--"}</td>
      </tr>
    `)
    .join("");
}

$("refreshButton").addEventListener("click", () => loadPortfolio(true));
$("searchInput").addEventListener("input", (event) => {
  state.query = event.target.value;
  if (state.snapshot) renderTable(state.snapshot.summary.holdings);
});

loadPortfolio(false);
