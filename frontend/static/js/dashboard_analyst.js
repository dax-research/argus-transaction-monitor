/**
 * dashboard_analyst.js — Analyst Dashboard
 * Requires /static/js/auth.js and /static/js/api.js loaded before this.
 * Requires Chart.js global.
 */

ArgusAuth.requireAuth('ANALYST');

let chartRisk = null, chartDaily = null, chartStatus = null, chartLine = null;

const TABS = {
    overview: '📊 Dashboard Overview',
    transactions: '💳 All Transactions',
    investigations: '🔍 Investigation Cases',
    charts: '📈 Analytics',
    audit: '📋 Audit Log',
};

// ── User info ─────────────────────────────────────────────────────────────────
(function () {
    const u = ArgusAuth.getUser();
    if (!u) return;
    const name = u.full_name || u.email;
    const el = document.getElementById('sidebar-name');
    const av = document.getElementById('sidebar-avatar');
    if (el) el.textContent = name;
    if (av) av.textContent = name.charAt(0).toUpperCase();
})();

// ── Tab switching ──────────────────────────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item[data-tab]').forEach(a => a.classList.remove('active'));
    const panel = document.getElementById(`tab-${tab}`);
    if (panel) panel.classList.add('active');
    const nav = document.querySelector(`.nav-item[data-tab="${tab}"]`);
    if (nav) nav.classList.add('active');
    const title = document.getElementById('topbar-title');
    if (title) title.textContent = TABS[tab] || tab;
    if (tab === 'transactions') loadTransactions();
    if (tab === 'investigations') loadInvestigations();
    if (tab === 'audit') loadAuditLog();
    if (tab === 'charts') renderChartsTab();
}
document.querySelectorAll('.nav-item[data-tab]').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); switchTab(a.dataset.tab); });
});

// ── Formatters ─────────────────────────────────────────────────────────────────
const fmtAmt = v => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);
const fmtDate = s => s ? new Date(s).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
const badge = (text, cls) => `<span class="badge badge-${cls}">${text}</span>`;
function statusBadge(s) { return badge(s, { PENDING: 'warning', APPROVED: 'success', FLAGGED: 'danger', REJECTED: 'secondary' }[s] || 'secondary'); }
function riskBadge(r) { return badge(r, { LOW: 'success', HIGH: 'danger', OTP_REQUIRED: 'warning' }[r] || 'secondary'); }
function invBadge(s) { return badge(s.replace(/_/g, ' '), { OPEN: 'danger', IN_PROGRESS: 'warning', CLOSED_RESOLVED: 'success', CLOSED_FALSE_POSITIVE: 'secondary' }[s] || 'secondary'); }

// ── KPI grid ──────────────────────────────────────────────────────────────────
function renderKPI(stats) {
    const g = document.getElementById('kpi-grid');
    if (!g) return;
    g.innerHTML = [
        ['💳', stats.total_transactions, 'Total Transactions', ''],
        ['🚨', stats.flagged, 'Flagged', 'color:#ff4757'],
        ['⚠️', stats.high_risk, 'High Risk', 'color:#ffa502'],
        ['✅', stats.approved, 'Approved', 'color:#00d4aa'],
        ['📋', stats.open_investigations, 'Open Cases', ''],
        ['📈', stats.fraud_rate + '%', 'Fraud Rate', ''],
    ].map(([icon, val, label, style]) => `
        <div class="kpi-card glass">
            <div class="kpi-icon">${icon}</div>
            <div class="kpi-body">
                <div class="kpi-value" style="${style}">${typeof val === 'number' ? val.toLocaleString() : val}</div>
                <div class="kpi-label">${label}</div>
            </div>
        </div>`).join('');
    const badge = document.getElementById('badge-open');
    if (badge && stats.open_investigations > 0) badge.textContent = stats.open_investigations;
}

// ── Charts ────────────────────────────────────────────────────────────────────
const CHART_OPTS = {
    plugins: { legend: { labels: { color: 'rgba(255,255,255,0.7)' } } },
    scales: {
        x: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.08)' } },
        y: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.08)' } }
    },
};

function renderCharts(stats) {
    const rd = stats.risk_distribution || {};
    const ctxR = document.getElementById('chart-risk');
    if (ctxR) {
        if (chartRisk) chartRisk.destroy();
        chartRisk = new Chart(ctxR, {
            type: 'doughnut', data: {
                labels: ['Low', 'High', 'OTP Required'],
                datasets: [{ data: [rd.LOW || 0, rd.HIGH || 0, rd.OTP_REQUIRED || 0], backgroundColor: ['#00d4aa', '#ff4757', '#ffa502'], borderWidth: 0 }]
            }, options: { plugins: { legend: { labels: { color: 'rgba(255,255,255,0.7)' } } }, cutout: '65%' }
        });
    }
    const daily = stats.daily_transactions || [];
    const ctxD = document.getElementById('chart-daily');
    if (ctxD) {
        if (chartDaily) chartDaily.destroy();
        chartDaily = new Chart(ctxD, {
            type: 'bar', data: {
                labels: daily.map(d => d.date),
                datasets: [{ label: 'Transactions', data: daily.map(d => d.count), backgroundColor: 'rgba(124,92,252,0.7)', borderRadius: 6 }]
            }, options: { ...CHART_OPTS, plugins: { legend: { display: false } } }
        });
    }
    window._lastStats = stats;
}

function renderChartsTab() {
    const s = window._lastStats; if (!s) return;
    const ctxS = document.getElementById('chart-status');
    if (ctxS) {
        if (chartStatus) chartStatus.destroy();
        chartStatus = new Chart(ctxS, {
            type: 'pie', data: {
                labels: ['Pending', 'Approved', 'Flagged', 'Rejected'],
                datasets: [{ data: [s.pending, s.approved, s.flagged, s.rejected], backgroundColor: ['#ffa502', '#00d4aa', '#ff4757', '#a0a0a0'], borderWidth: 0 }]
            }, options: { plugins: { legend: { labels: { color: 'rgba(255,255,255,0.7)' } } } }
        });
    }
    const daily = s.daily_transactions || [];
    const ctxL = document.getElementById('chart-daily2');
    if (ctxL) {
        if (chartLine) chartLine.destroy();
        chartLine = new Chart(ctxL, {
            type: 'line', data: {
                labels: daily.map(d => d.date),
                datasets: [{ label: 'Daily Transactions', data: daily.map(d => d.count), borderColor: '#7c5cfc', backgroundColor: 'rgba(124,92,252,0.15)', tension: 0.4, fill: true }]
            }, options: CHART_OPTS
        });
    }
}

// ── Transactions ───────────────────────────────────────────────────────────────
async function loadTransactions() {
    const wrap = document.getElementById('txn-table-wrap');
    const ow = document.getElementById('overview-txn-wrap');
    if (wrap) wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    const sF = document.getElementById('filter-status')?.value || '';
    const rF = document.getElementById('filter-risk')?.value || '';
    try {
        const data = await ArgusAPI.getTransactions(sF, rF);
        const rows = data.results || data;
        window._allTxnRows = rows;     // cache for client-side search
        const tbl = buildTxnTable(rows);
        if (wrap) { wrap.innerHTML = ''; wrap.appendChild(tbl); }
        if (ow) {
            const flagged = rows.filter(t => t.status === 'FLAGGED').slice(0, 5);
            ow.innerHTML = ''; ow.appendChild(buildTxnTable(flagged.length ? flagged : rows.slice(0, 5)));
        }
    } catch (e) {
        const html = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`;
        if (wrap) wrap.innerHTML = html; if (ow) ow.innerHTML = html;
    }
}

// Client-side search — filters _allTxnRows without an API call
function filterTransactions() {
    const query = (document.getElementById('search-txn')?.value || '').toLowerCase().trim();
    const wrap = document.getElementById('txn-table-wrap');
    if (!wrap) return;
    const rows = window._allTxnRows || [];
    const filtered = query
        ? rows.filter(r =>
            (r.id || '').toLowerCase().includes(query) ||
            String(r.amount || '').includes(query) ||
            (r.merchant_name || '').toLowerCase().includes(query) ||
            (r.merchant_category || '').toLowerCase().includes(query) ||
            (r.status || '').toLowerCase().includes(query)
        )
        : rows;
    wrap.innerHTML = '';
    wrap.appendChild(buildTxnTable(filtered));
}

function buildTxnTable(rows) {
    if (!rows?.length) { const d = document.createElement('div'); d.className = 'empty-state'; d.textContent = 'No transactions found.'; return d; }
    const t = document.createElement('table'); t.className = 'data-table';
    t.innerHTML = `<thead><tr><th>ID</th><th>Amount</th><th>Merchant</th><th>Status</th><th>Risk</th><th>Score</th><th>Date</th><th>Action</th></tr></thead>
    <tbody>${rows.map(r => `<tr>
        <td><code style="font-size:.78rem;">${r.id || '—'}</code></td>
        <td>${fmtAmt(r.amount || 0)}</td>
        <td>${r.merchant_name || r.merchant_category || '—'}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${riskBadge(r.risk_level)}</td>
        <td>${r.fraud_score != null ? (r.fraud_score * 100).toFixed(1) + '%' : '—'}</td>
        <td style="white-space:nowrap;">${fmtDate(r.created_at)}</td>
        <td><button class="btn btn-sm flag-btn" id="flag-${r.id}" onclick="flagTransaction('${r.id}', this)" style="background:rgba(255,165,2,.12);border:1px solid rgba(255,165,2,.3);color:#ffa502;">&#x1F6A9; Flag</button></td>
    </tr>`).join('')}</tbody>`;
    return t;
}

async function flagTransaction(txnId, btn) {
    btn.disabled = true;
    btn.textContent = '⏳ Flagging…';
    try {
        await ArgusAuth.authFetch(`/api/dashboard/transactions/${txnId}/flag/`, { method: 'POST' });
        btn.textContent = '✅ Flagged';
        btn.style.background = 'rgba(46,213,115,.12)';
        btn.style.borderColor = 'rgba(46,213,115,.3)';
        btn.style.color = '#2ed573';
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '🚩 Flag';
        alert('Failed to flag: ' + e.message);
    }
}

// ── Investigations ─────────────────────────────────────────────────────────────
async function loadInvestigations() {
    const wrap = document.getElementById('inv-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    try {
        const rows = await ArgusAPI.getInvestigations();
        if (!rows?.length) { wrap.innerHTML = '<div class="empty-state"><p>No investigations.</p></div>'; return; }

        // Store in global map so onclick can look up by id safely
        window._invData = {};
        rows.forEach(inv => { window._invData[inv.id] = inv; });

        const t = document.createElement('table'); t.className = 'data-table';
        t.innerHTML = `<thead><tr><th>Case</th><th>Transaction</th><th>Status</th><th>Analyst</th><th>Notes</th><th>Notifications</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>${rows.map(inv => {
            const hasAuditorFlag = (inv.notes || '').includes('AUDITOR_FLAGGED');
            const notifCell = hasAuditorFlag
                ? '<span class="badge badge-warning">Auditor report</span>'
                : '<span class="badge badge-secondary">—</span>';
            const safeNotes = (inv.notes || '').replace(/"/g, '&quot;');
            return `<tr>
                <td>#${inv.id}</td>
                <td><code style="font-size:.78rem;">${inv.transaction || '—'}</code></td>
                <td>${invBadge(inv.status)}</td>
                <td>${inv.analyst_name || inv.analyst || '—'}</td>
                <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${safeNotes}">${inv.notes || '—'}</td>
                <td>${notifCell}</td>
                <td style="white-space:nowrap;">${fmtDate(inv.created_at)}</td>
                <td><button class="btn btn-outline btn-sm" onclick="openInvModal(${inv.id})">Update</button></td>
            </tr>`;
        }).join('')}</tbody>`;
        wrap.innerHTML = ''; wrap.appendChild(t);
    } catch (e) { wrap.innerHTML = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`; }
}

// Safe modal opener — looks up data from global map instead of inlining strings in onclick
function openInvModal(id) {
    const inv = (window._invData || {})[id] || {};
    openModal(inv.id ?? id, inv.status || 'OPEN', inv.notes || '', inv.resolution || '');
}

// ── Audit log ─────────────────────────────────────────────────────────────────
async function loadAuditLog() {
    const wrap = document.getElementById('audit-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    try {
        const data = await ArgusAPI.getAuditLog();
        const rows = data.results || data;
        if (!rows?.length) { wrap.innerHTML = '<div class="empty-state"><p>No audit events.</p></div>'; return; }
        const t = document.createElement('table'); t.className = 'data-table';
        t.innerHTML = `<thead><tr><th>Timestamp</th><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
        <tbody>${rows.map(e => `<tr>
            <td style="white-space:nowrap;">${fmtDate(e.timestamp)}</td>
            <td>${e.actor_name || e.actor || '—'}</td>
            <td><code style="font-size:.78rem;">${e.action || '—'}</code></td>
            <td>${e.entity_type || '—'} ${e.entity_id ? '#' + e.entity_id : ''}</td>
            <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${e.detail || ''}">${e.detail || '—'}</td>
        </tr>`).join('')}</tbody>`;
        wrap.innerHTML = ''; wrap.appendChild(t);
    } catch (e) { wrap.innerHTML = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`; }
}

// ── Investigation modal ────────────────────────────────────────────────────────
function openModal(id, status, notes, resolution) {
    document.getElementById('modal-case-id').value = id;
    document.getElementById('modal-status').value = status || 'OPEN';
    document.getElementById('modal-notes').value = notes || '';
    document.getElementById('modal-resolution').value = resolution || '';
    document.getElementById('modal-error').style.display = 'none';
    document.getElementById('inv-modal').classList.add('active');
}
function closeModal() { document.getElementById('inv-modal').classList.remove('active'); }
async function submitInvUpdate() {
    const id = document.getElementById('modal-case-id').value;
    const data = {
        status: document.getElementById('modal-status').value,
        notes: document.getElementById('modal-notes').value,
        resolution: document.getElementById('modal-resolution').value,
    };
    const errEl = document.getElementById('modal-error');
    errEl.style.display = 'none';
    try {
        await ArgusAPI.updateInvestigation(id, data);
        // Update local cache so table reflects the change immediately
        if (window._invData && window._invData[id]) {
            window._invData[id] = { ...window._invData[id], ...data };
        }
        closeModal();
        loadInvestigations();
    } catch (e) { errEl.textContent = e.message; errEl.style.display = 'block'; }
}
document.getElementById('inv-modal')?.addEventListener('click', function (e) { if (e.target === this) closeModal(); });

// ── Bootstrap ──────────────────────────────────────────────────────────────────
async function loadAll() {
    try { const s = await ArgusAPI.getStats(); renderKPI(s); renderCharts(s); } catch (e) { console.error('Stats:', e); }
    loadTransactions(); loadInvestigations(); loadAuditLog();
}
loadAll();
