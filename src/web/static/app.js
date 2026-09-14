// ==========================================================================
// FUNDAMENTAL ANALYSIS HUB — CLIENT-SIDE APPLICATION
// SPA Engine: Real-Time Brokerage, Plotly Charts & REST API Client
// ==========================================================================

let currentPortfolioData = null;
let currentTimelineData = null;
let currentPositions = {};
let availableCash = 0;
let quoteDebounceTimer = null;
let activeTickerQuote = null;

// Formatter Helpers
const formatCurrency = (val, decimals = 2) => {
  if (val === null || val === undefined || isNaN(val)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
};

const formatPct = (val, decimals = 2, includeSign = true) => {
  if (val === null || val === undefined || isNaN(val)) return '0.00%';
  const sign = val > 0 && includeSign ? '+' : '';
  return `${sign}${Number(val).toFixed(decimals)}%`;
};

// Toast Notification Manager
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? '✅' : '❌';
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==========================================================================
// DATA FETCHING & UI HYDRATION
// ==========================================================================
async function refreshAll() {
  await Promise.all([
    fetchPortfolio(),
    fetchTimeline(),
    fetchHistory(),
  ]);
}

async function fetchPortfolio() {
  try {
    const res = await fetch('/api/portfolio');
    if (!res.ok) throw new Error('Error al cargar datos del portafolio');
    const data = await res.json();
    currentPortfolioData = data;
    currentPositions = data.positions || {};
    availableCash = data.summary.cash_balance || 0;

    renderHeaderStats(data.summary);
    renderKpiCards(data.summary);
    renderPositionsTable(data.positions);
    renderAllocationChart(data.allocation);
    renderSectorsChart(data.sectors, data.concentration);
    updateSellDropdown(data.positions);
    updateCashHints();
  } catch (err) {
    console.error(err);
    showToast('No se pudo actualizar el portafolio: ' + err.message, 'error');
  }
}

async function fetchTimeline() {
  try {
    const res = await fetch('/api/timeline?benchmark=SPY');
    if (!res.ok) throw new Error('Error al cargar serie temporal');
    const data = await res.json();
    currentTimelineData = data;

    renderTimelineStats(data.metrics);
    renderEvolutionChart(data);
  } catch (err) {
    console.error(err);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    if (!res.ok) return;
    const data = await res.json();
    renderHistoryTable(data.transactions || []);
  } catch (err) {
    console.error(err);
  }
}

async function fetchWatchlist() {
  try {
    const res = await fetch('/api/watchlist');
    if (!res.ok) return;
    const data = await res.json();
    renderWatchlistChips(data.watchlist || []);
  } catch (err) {
    console.error(err);
  }
}

// ==========================================================================
// RENDERERS: METRICS & HEADER
// ==========================================================================
function renderHeaderStats(summary) {
  document.getElementById('nav-portfolio-val').textContent = formatCurrency(summary.portfolio_value);
  document.getElementById('nav-cash-val').textContent = formatCurrency(summary.cash_balance);

  const retBadge = document.getElementById('nav-return-badge');
  retBadge.textContent = formatPct(summary.total_return_pct);
  retBadge.className = summary.total_return_pct >= 0 ? 'badge-green' : 'badge-red';
}

function renderTimelineStats(metrics) {
  if (!metrics) return;
  const spyBadge = document.getElementById('nav-spy-badge');
  spyBadge.textContent = formatPct(metrics.benchmark_return_pct);

  const alphaBadge = document.getElementById('nav-alpha-badge');
  alphaBadge.textContent = formatPct(metrics.alpha_pct);
  alphaBadge.className = metrics.alpha_pct >= 0 ? 'badge-green' : 'badge-red';

  const kpiAlpha = document.getElementById('kpi-alpha-text');
  kpiAlpha.textContent = `Alpha: ${formatPct(metrics.alpha_pct)} vs S&P 500`;
  kpiAlpha.style.color = metrics.alpha_pct >= 0 ? 'var(--accent-emerald)' : 'var(--accent-red)';

  document.getElementById('kpi-benchmark-val').textContent = formatCurrency(metrics.current_benchmark_val);
}

function renderKpiCards(summary) {
  document.getElementById('kpi-nav').textContent = formatCurrency(summary.portfolio_value);
  const navSub = document.getElementById('kpi-nav-sub');
  navSub.textContent = `Rentabilidad: ${formatPct(summary.total_return_pct)}`;
  navSub.style.color = summary.total_return_pct >= 0 ? 'var(--accent-emerald)' : 'var(--accent-red)';

  document.getElementById('kpi-deposits').textContent = formatCurrency(summary.net_deposits);
  document.getElementById('kpi-cash').textContent = formatCurrency(summary.cash_balance);
  document.getElementById('kpi-cash-pct').textContent = `${summary.cash_weight_pct}% en liquidez`;

  const unpnlEl = document.getElementById('kpi-unrealized-pnl');
  unpnlEl.textContent = formatCurrency(summary.unrealized_pnl);
  unpnlEl.style.color = summary.unrealized_pnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-red)';

  const invested = summary.invested_capital || 0;
  const unpnlPct = invested > 0 ? (summary.unrealized_pnl / invested) * 100 : 0;
  const unpnlSub = document.getElementById('kpi-unrealized-pct');
  unpnlSub.textContent = `${formatPct(unpnlPct)} sobre invertido`;
}

function updateCashHints() {
  const hint = document.getElementById('buy-available-cash-hint');
  if (hint) {
    hint.textContent = `Disponible: ${formatCurrency(availableCash)}`;
  }
}

// ==========================================================================
// RENDERERS: TABLES
// ==========================================================================
function renderPositionsTable(positions) {
  const tbody = document.getElementById('tbody-positions');
  const countLabel = document.getElementById('positions-count-label');
  tbody.innerHTML = '';

  const keys = Object.keys(positions || {});
  countLabel.textContent = `${keys.length} activos en cartera`;

  if (keys.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; color: var(--text-dim); padding: 32px;">
          No tienes posiciones abiertas en cartera. Utiliza el <b>Order Ticket</b> a la derecha para comprar tu primera acción.
        </td>
      </tr>
    `;
    return;
  }

  keys.forEach((ticker) => {
    const pos = positions[ticker];
    const tr = document.createElement('tr');

    const pnlColor = pos.unrealized_pnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-red)';
    const pnlSign = pos.unrealized_pnl >= 0 ? '+' : '';

    tr.innerHTML = `
      <td>
        <div class="ticker-cell">
          <span class="ticker-tag">${ticker}</span>
          <div>
            <div class="asset-name">${pos.name}</div>
            <div class="asset-sector">${pos.sector || 'General'}</div>
          </div>
        </div>
      </td>
      <td><span class="chip-ticker">${pos.type || 'equity'}</span></td>
      <td style="text-align: right; font-weight: 600;">${pos.shares.toFixed(2)}</td>
      <td style="text-align: right; color: var(--text-muted);">${formatCurrency(pos.avg_cost_price)}</td>
      <td style="text-align: right; font-weight: 600;">${formatCurrency(pos.current_price)}</td>
      <td style="text-align: right; font-weight: 700;">${formatCurrency(pos.market_value)}</td>
      <td style="text-align: right; font-weight: 700; color: ${pnlColor};">
        ${pnlSign}${formatCurrency(pos.unrealized_pnl)}
      </td>
      <td style="text-align: right; font-weight: 700; color: ${pnlColor};">
        ${formatPct(pos.unrealized_pnl_pct)}
      </td>
      <td style="text-align: right; color: var(--accent-cyan); font-weight: 600;">
        ${pos.weight_pct ? pos.weight_pct.toFixed(1) : 0.0}%
      </td>
      <td style="text-align: center;">
        <button class="table-btn" onclick="quickActionBuy('${ticker}')" title="Comprar más acciones">Comprar</button>
        <button class="table-btn" onclick="quickActionSell('${ticker}')" title="Vender acciones">Vender</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderHistoryTable(transactions) {
  const tbody = document.getElementById('tbody-history');
  const countLabel = document.getElementById('tx-count-label');
  tbody.innerHTML = '';

  countLabel.textContent = `${transactions.length} transacciones registradas`;

  if (transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: var(--text-dim); padding: 24px;">
          El libro contable está vacío.
        </td>
      </tr>
    `;
    return;
  }

  transactions.forEach((tx) => {
    const tr = document.createElement('tr');
    const dateStr = tx.timestamp ? tx.timestamp.replace('T', ' ').substring(0, 16) : 'N/A';

    let typeBadge = 'badge-cyan';
    if (tx.type === 'BUY') typeBadge = 'badge-cyan';
    else if (tx.type === 'SELL') typeBadge = 'badge-red';
    else if (tx.type === 'DEPOSIT') typeBadge = 'badge-green';
    else if (tx.type === 'DIVIDEND') typeBadge = 'badge-green';

    const totalFmt = formatCurrency(tx.total);
    const sharesFmt = tx.shares ? tx.shares.toFixed(2) : '-';
    const priceFmt = tx.price ? formatCurrency(tx.price) : '-';
    const feeFmt = tx.fee ? formatCurrency(tx.fee) : '$0.00';

    tr.innerHTML = `
      <td style="color: var(--text-dim); font-size: 12px;">${dateStr}</td>
      <td><span class="${typeBadge}">${tx.type}</span></td>
      <td><b>${tx.ticker || 'CASH'}</b></td>
      <td style="text-align: right;">${sharesFmt}</td>
      <td style="text-align: right;">${priceFmt}</td>
      <td style="text-align: right; color: var(--text-dim);">${feeFmt}</td>
      <td style="text-align: right; font-weight: 700;">${totalFmt}</td>
      <td style="color: var(--text-muted); font-size: 12px; max-width: 250px; overflow: hidden; text-overflow: ellipsis;">
        ${tx.notes || '-'}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderWatchlistChips(watchlist) {
  const container = document.getElementById('quick-tickers');
  container.innerHTML = '';

  watchlist.slice(0, 7).forEach((item) => {
    const chip = document.createElement('span');
    chip.className = 'chip-ticker';
    chip.textContent = item.ticker;
    chip.onclick = () => {
      document.getElementById('buy-ticker').value = item.ticker;
      triggerQuoteLookup(item.ticker);
    };
    container.appendChild(chip);
  });
}

// ==========================================================================
// RENDERERS: PLOTLY CHARTS
// ==========================================================================
function renderEvolutionChart(timelineData) {
  const container = document.getElementById('chart-evolution');
  if (!timelineData || !timelineData.timeline) return;

  const tl = timelineData.timeline;
  const dates = tl.dates || [];
  const nav = tl.portfolio_nav || [];
  const deposits = tl.cumulative_deposits || [];
  const bench = tl.benchmark_nav || [];
  const benchTicker = timelineData.benchmark_ticker || 'SPY';

  const traceDeposits = {
    x: dates,
    y: deposits,
    mode: 'lines+markers',
    name: 'Aportes Acumulados ($)',
    line: { color: '#94a3b8', width: 2, dash: 'dot' },
    marker: { size: 4 },
    hovertemplate: '<b>Aportaciones Acumuladas:</b> $%{y:,.2f}<extra></extra>',
  };

  const traceBenchmark = {
    x: dates,
    y: bench,
    mode: 'lines+markers',
    name: `S&P 500 (${benchTicker})`,
    line: { color: '#f59e0b', width: 2.5 },
    marker: { size: 4 },
    hovertemplate: `<b>Benchmark ${benchTicker}:</b> $%{y:,.2f}<extra></extra>`,
  };

  const traceNav = {
    x: dates,
    y: nav,
    mode: 'lines+markers',
    name: 'Valor Cartera (NAV)',
    line: { color: '#06b6d4', width: 3.5 },
    marker: { size: 6 },
    fill: 'tonexty',
    fillcolor: 'rgba(6, 182, 212, 0.08)',
    hovertemplate: '<b>Valor Cartera (NAV):</b> $%{y:,.2f}<extra></extra>',
  };

  const layout = {
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8', size: 11 },
    height: 380,
    margin: { l: 60, r: 30, t: 30, b: 40 },
    xaxis: {
      gridcolor: 'rgba(255, 255, 255, 0.05)',
      tickformat: '%b %d',
    },
    yaxis: {
      gridcolor: 'rgba(255, 255, 255, 0.05)',
      tickprefix: '$',
      tickformat: ',.0f',
    },
    legend: {
      orientation: 'h',
      y: 1.12,
      x: 0.98,
      xanchor: 'right',
      font: { size: 11 },
    },
    hovermode: 'x unified',
  };

  const config = { responsive: true, displayModeBar: false };
  Plotly.react(container, [traceDeposits, traceBenchmark, traceNav], layout, config);
}

function renderAllocationChart(allocation) {
  const container = document.getElementById('chart-allocation');
  if (!allocation) return;

  const labels = [];
  const values = [];

  Object.values(allocation).forEach((item) => {
    if (item.market_value > 0) {
      labels.push(item.label);
      values.push(item.market_value);
    }
  });

  const trace = {
    labels: labels,
    values: values,
    type: 'pie',
    hole: 0.52,
    textinfo: 'label+percent',
    textposition: 'outside',
    marker: {
      colors: ['#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#64748b', '#8b5cf6'],
    },
    hovertemplate: '<b>%{label}</b><br>Valor: $%{value:,.2f}<br>%{percent}<extra></extra>',
  };

  const layout = {
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8', size: 11 },
    height: 300,
    margin: { l: 20, r: 20, t: 20, b: 20 },
    showlegend: false,
  };

  const config = { responsive: true, displayModeBar: false };
  Plotly.react(container, [trace], layout, config);
}

function renderSectorsChart(sectors, concentration) {
  const container = document.getElementById('chart-sectors');
  if (!sectors) return;

  const labels = Object.keys(sectors);
  const values = Object.values(sectors).map((s) => s.market_value);

  if (concentration && concentration.hhi_index !== undefined) {
    const badge = document.getElementById('hhi-badge');
    badge.textContent = `HHI: ${concentration.hhi_index} (${concentration.diversification_level || 'Diversificado'})`;
  }

  const trace = {
    labels: labels,
    values: values,
    type: 'pie',
    hole: 0.52,
    textinfo: 'label+percent',
    textposition: 'outside',
    marker: {
      colors: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899'],
    },
    hovertemplate: '<b>%{label}</b><br>Valor: $%{value:,.2f}<br>%{percent}<extra></extra>',
  };

  const layout = {
    template: 'plotly_dark',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, sans-serif', color: '#94a3b8', size: 11 },
    height: 300,
    margin: { l: 20, r: 20, t: 20, b: 20 },
    showlegend: false,
  };

  const config = { responsive: true, displayModeBar: false };
  Plotly.react(container, [trace], layout, config);
}

// ==========================================================================
// TRADING DESK: QUOTE LOOKUP & ORDER CALCULATION
// ==========================================================================
function triggerQuoteLookup(ticker) {
  const clean = ticker.trim().upper ? ticker.trim().toUpperCase() : ticker.trim();
  if (!clean) {
    document.getElementById('buy-quote-box').style.display = 'none';
    activeTickerQuote = null;
    return;
  }

  const loadingEl = document.getElementById('buy-quote-loading');
  loadingEl.style.display = 'inline';

  fetch(`/api/quote?ticker=${encodeURIComponent(clean)}`)
    .then((r) => r.json())
    .then((data) => {
      loadingEl.style.display = 'none';
      if (data.price) {
        activeTickerQuote = data;
        const box = document.getElementById('buy-quote-box');
        box.style.display = 'flex';
        document.getElementById('buy-quote-name').textContent = data.name || data.ticker;
        document.getElementById('buy-quote-meta').textContent = `${data.type || 'equity'} • ${data.sector || 'General'}`;
        document.getElementById('buy-quote-price').textContent = formatCurrency(data.price);

        const priceInput = document.getElementById('buy-price');
        if (!priceInput.value) {
          priceInput.placeholder = data.price.toFixed(2);
        }
        recalcBuyOrder();
      } else {
        document.getElementById('buy-quote-box').style.display = 'none';
        activeTickerQuote = null;
      }
    })
    .catch(() => {
      loadingEl.style.display = 'none';
    });
}

function recalcBuyOrder() {
  const sharesInput = parseFloat(document.getElementById('buy-shares').value) || 0;
  const customPrice = parseFloat(document.getElementById('buy-price').value);
  const quotePrice = activeTickerQuote ? activeTickerQuote.price : 0;
  const execPrice = !isNaN(customPrice) && customPrice > 0 ? customPrice : quotePrice;

  const subtotal = sharesInput * execPrice;
  const total = subtotal;

  document.getElementById('buy-calc-subtotal').textContent = formatCurrency(subtotal);
  const totalEl = document.getElementById('buy-calc-total');
  totalEl.textContent = formatCurrency(total);

  if (total > availableCash) {
    totalEl.style.color = 'var(--accent-red)';
    document.getElementById('btn-submit-buy').disabled = true;
    document.getElementById('btn-submit-buy').textContent = 'Fondos Insuficientes';
  } else {
    totalEl.style.color = 'var(--accent-cyan)';
    document.getElementById('btn-submit-buy').disabled = false;
    document.getElementById('btn-submit-buy').textContent = 'Ejecutar Orden de Compra';
  }
}

// Update Sell Dropdown
function updateSellDropdown(positions) {
  const select = document.getElementById('sell-ticker-select');
  select.innerHTML = '<option value="">Selecciona un activo...</option>';

  Object.keys(positions || {}).forEach((t) => {
    const p = positions[t];
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = `${t} — ${p.shares.toFixed(2)} acciones (${formatCurrency(p.market_value)})`;
    select.appendChild(opt);
  });
}

function recalcSellOrder() {
  const ticker = document.getElementById('sell-ticker-select').value;
  const sharesToSell = parseFloat(document.getElementById('sell-shares').value) || 0;

  if (!ticker || !currentPositions[ticker]) {
    document.getElementById('sell-quote-box').style.display = 'none';
    return;
  }

  const pos = currentPositions[ticker];
  const box = document.getElementById('sell-quote-box');
  box.style.display = 'flex';
  document.getElementById('sell-quote-name').textContent = `${ticker} • ${pos.name}`;
  document.getElementById('sell-quote-shares').textContent = `Posees: ${pos.shares.toFixed(2)} acciones`;
  document.getElementById('sell-quote-price').textContent = formatCurrency(pos.current_price);

  const estProceeds = sharesToSell * pos.current_price;
  const estCost = sharesToSell * pos.avg_cost_price;
  const estPnl = estProceeds - estCost;

  document.getElementById('sell-calc-total').textContent = formatCurrency(estProceeds);
  const pnlEl = document.getElementById('sell-calc-pnl');
  pnlEl.textContent = `${estPnl >= 0 ? '+' : ''}${formatCurrency(estPnl)}`;
  pnlEl.style.color = estPnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-red)';

  const btn = document.getElementById('btn-submit-sell');
  if (sharesToSell > pos.shares) {
    btn.disabled = true;
    btn.textContent = 'Acciones Insuficientes';
  } else {
    btn.disabled = false;
    btn.textContent = 'Ejecutar Orden de Venta';
  }
}

// Quick Actions
function quickActionBuy(ticker) {
  switchTab('tab-buy');
  const input = document.getElementById('buy-ticker');
  input.value = ticker;
  triggerQuoteLookup(ticker);
  document.getElementById('buy-shares').focus();
}

function quickActionSell(ticker) {
  switchTab('tab-sell');
  const select = document.getElementById('sell-ticker-select');
  select.value = ticker;
  recalcSellOrder();
  document.getElementById('sell-shares').focus();
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.getElementById('form-buy').style.display = tabId === 'tab-buy' ? 'flex' : 'none';
  document.getElementById('form-sell').style.display = tabId === 'tab-sell' ? 'flex' : 'none';
  document.getElementById('form-dca').style.display = tabId === 'tab-dca' ? 'flex' : 'none';
}

// ==========================================================================
// EVENT LISTENERS & FORM SUBMISSIONS
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Initial Hydration
  refreshAll();
  fetchWatchlist();

  // Polling cada 30 segundos
  setInterval(refreshAll, 30000);

  // Tab Buttons
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Ticker Quote Input Listener
  const buyTickerInput = document.getElementById('buy-ticker');
  buyTickerInput.addEventListener('input', (e) => {
    clearTimeout(quoteDebounceTimer);
    const val = e.target.value.trim();
    if (val.length >= 1) {
      quoteDebounceTimer = setTimeout(() => triggerQuoteLookup(val), 350);
    } else {
      document.getElementById('buy-quote-box').style.display = 'none';
    }
  });

  // Shares & Price Listeners for Buy Order
  document.getElementById('buy-shares').addEventListener('input', recalcBuyOrder);
  document.getElementById('buy-price').addEventListener('input', recalcBuyOrder);

  // Sell Select & Shares Listeners
  document.getElementById('sell-ticker-select').addEventListener('change', recalcSellOrder);
  document.getElementById('sell-shares').addEventListener('input', recalcSellOrder);

  // Form Submit: BUY
  document.getElementById('form-buy').addEventListener('submit', async (e) => {
    e.preventDefault();
    const ticker = document.getElementById('buy-ticker').value.trim().toUpperCase();
    const shares = parseFloat(document.getElementById('buy-shares').value);
    const priceVal = parseFloat(document.getElementById('buy-price').value);
    const notes = document.getElementById('buy-notes').value.trim();

    if (!ticker || isNaN(shares) || shares <= 0) {
      showToast('Ingresa un ticker y cantidad válidos', 'error');
      return;
    }

    const btn = document.getElementById('btn-submit-buy');
    btn.disabled = true;
    btn.textContent = 'Enviando orden...';

    try {
      const payload = {
        ticker: ticker,
        shares: shares,
        price: !isNaN(priceVal) && priceVal > 0 ? priceVal : null,
        fee: 0.0,
        notes: notes || 'Compra simulada desde Web Desk',
      };

      const res = await fetch('/api/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al ejecutar compra');

      showToast(`¡Compra ejecutada! ${shares} de ${ticker} a $${data.transaction.price.toFixed(2)}`, 'success');
      document.getElementById('form-buy').reset();
      document.getElementById('buy-quote-box').style.display = 'none';
      activeTickerQuote = null;
      recalcBuyOrder();
      await refreshAll();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Ejecutar Orden de Compra';
    }
  });

  // Form Submit: SELL
  document.getElementById('form-sell').addEventListener('submit', async (e) => {
    e.preventDefault();
    const ticker = document.getElementById('sell-ticker-select').value;
    const shares = parseFloat(document.getElementById('sell-shares').value);
    const notes = document.getElementById('sell-notes').value.trim();

    if (!ticker || isNaN(shares) || shares <= 0) {
      showToast('Selecciona posición y cantidad a vender', 'error');
      return;
    }

    const btn = document.getElementById('btn-submit-sell');
    btn.disabled = true;
    btn.textContent = 'Enviando orden...';

    try {
      const payload = {
        ticker: ticker,
        shares: shares,
        fee: 0.0,
        notes: notes || 'Venta simulada desde Web Desk',
      };

      const res = await fetch('/api/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al ejecutar venta');

      showToast(`¡Venta ejecutada! Acreditados $${data.transaction.total.toFixed(2)} en cuenta`, 'success');
      document.getElementById('form-sell').reset();
      document.getElementById('sell-quote-box').style.display = 'none';
      await refreshAll();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Ejecutar Orden de Venta';
    }
  });

  // Form Submit: DCA APORTE MENSUAL
  document.getElementById('form-dca').addEventListener('submit', async (e) => {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('dca-amount').value);
    const mode = document.getElementById('dca-mode').value;
    const notes = document.getElementById('dca-notes').value.trim();

    const btn = document.getElementById('btn-submit-dca');
    btn.disabled = true;
    btn.textContent = 'Procesando aporte...';

    try {
      if (mode === 'single') {
        const res = await fetch('/api/deposit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount, notes: notes || 'Aporte mensual DCA' }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al depositar');
        showToast(`¡Depósito de $${amount.toFixed(2)} registrado con éxito!`, 'success');
      } else {
        const months = mode === 'multi-12' ? 12 : 6;
        const res = await fetch('/api/simulate-monthly', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount, months, notes }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error en simulación');
        showToast(`¡Simulados ${months} aportes de $${amount.toFixed(2)} ($${(amount * months).toFixed(2)} total)!`, 'success');
      }
      await refreshAll();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Inyectar Capital DCA';
    }
  });

  // Header Actions
  document.getElementById('btn-export-csv').addEventListener('click', () => {
    window.location.href = '/api/export-csv';
  });

  document.getElementById('btn-reset-portfolio').addEventListener('click', async () => {
    const ok = confirm('¿Estás seguro de que deseas reiniciar el portafolio con $100,000 USD limpios?');
    if (!ok) return;

    try {
      const res = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_cash: 100000.0 }),
      });
      if (!res.ok) throw new Error('Error al reiniciar');
      showToast('Portafolio reiniciado a $100,000 USD de capital simulado.', 'success');
      await refreshAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
});
