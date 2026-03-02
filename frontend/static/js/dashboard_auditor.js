/**
 * dashboard_auditor.js — Auditor Dashboard (read-only)
 * Requires /static/js/auth.js and /static/js/api.js loaded before this.
 * Requires Chart.js global.
 */

ArgusAuth.requireAuth('AUDITOR');

let chartRisk = null, chartDaily = null;

const TABS = {
    overview: '📊 Auditor Overview',
    transactions: '💳 Transaction Records',
    investigations: '🔍 Investigation Cases',
    audit: '📋 Full Audit Log',
};

(function () {
    const u = ArgusAuth.getUser();
    if (!u) return;
    const name = u.full_name || u.email;
    const el = document.getElementById('sidebar-name');
    const av = document.getElementById('sidebar-avatar');
    if (el) el.textContent = name;
    if (av) av.textContent = name.charAt(0).toUpperCase();
})();

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
}
document.querySelectorAll('.nav-item[data-tab]').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); switchTab(a.dataset.tab); });
});

const fmtAmt = v => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);
const fmtDate = s => s ? new Date(s).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
const badge = (text, cls) => `<span class="badge badge-${cls}">${text}</span>`;
function statusBadge(s) { return badge(s, { PENDING: 'warning', APPROVED: 'success', FLAGGED: 'danger', REJECTED: 'secondary' }[s] || 'secondary'); }
function riskBadge(r) { return badge(r, { LOW: 'success', HIGH: 'danger', OTP_REQUIRED: 'warning' }[r] || 'secondary'); }
function invBadge(s) { return badge(s.replace(/_/g, ' '), { OPEN: 'danger', IN_PROGRESS: 'warning', CLOSED_RESOLVED: 'success', CLOSED_FALSE_POSITIVE: 'secondary' }[s] || 'secondary'); }

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
}

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
    const OPTS = {
        x: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.08)' } },
        y: { ticks: { color: 'rgba(255,255,255,0.6)' }, grid: { color: 'rgba(255,255,255,0.08)' } }
    };
    if (ctxD) {
        if (chartDaily) chartDaily.destroy();
        chartDaily = new Chart(ctxD, {
            type: 'bar', data: {
                labels: daily.map(d => d.date),
                datasets: [{ label: 'Transactions', data: daily.map(d => d.count), backgroundColor: 'rgba(0,212,170,0.7)', borderRadius: 6 }]
            }, options: { plugins: { legend: { display: false } }, scales: OPTS }
        });
    }
}

async function loadTransactions() {
    const wrap = document.getElementById('txn-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    const sF = document.getElementById('filter-status')?.value || '';
    const rF = document.getElementById('filter-risk')?.value || '';
    try {
        const data = await ArgusAPI.getTransactions(sF, rF);
        const rows = data.results || data;
        if (!rows?.length) { wrap.innerHTML = '<div class="empty-state"><p>No transactions found.</p></div>'; return; }
        const t = document.createElement('table'); t.className = 'data-table';
        t.innerHTML = `<thead><tr><th>ID</th><th>Amount</th><th>Merchant</th><th>Status</th><th>Risk</th><th>Score</th><th>Date</th></tr></thead>
        <tbody>${rows.map(r => `<tr>
            <td><code style="font-size:.78rem;">${r.id || '—'}</code></td>
            <td>${fmtAmt(r.amount || 0)}</td>
            <td>${r.merchant_name || r.merchant_category || '—'}</td>
            <td>${statusBadge(r.status)}</td>
            <td>${riskBadge(r.risk_level)}</td>
            <td>${r.fraud_score != null ? (r.fraud_score * 100).toFixed(1) + '%' : '—'}</td>
            <td style="white-space:nowrap;">${fmtDate(r.created_at)}</td>
        </tr>`).join('')}</tbody>`;
        wrap.innerHTML = ''; wrap.appendChild(t);
    } catch (e) { wrap.innerHTML = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`; }
}

async function loadInvestigations() {
    const wrap = document.getElementById('inv-table-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    try {
        const rows = await ArgusAPI.getInvestigations();
        if (!rows?.length) { wrap.innerHTML = '<div class="empty-state"><p>No investigations.</p></div>'; return; }
        const t = document.createElement('table'); t.className = 'data-table';
        t.innerHTML = `<thead><tr><th>Case</th><th>Transaction</th><th>Status</th><th>Analyst</th><th>Notes</th><th>Created</th></tr></thead>
        <tbody>${rows.map(inv => `<tr>
            <td>#${inv.id}</td>
            <td><code style="font-size:.78rem;">${inv.transaction || '—'}</code></td>
            <td>${invBadge(inv.status)}</td>
            <td>${inv.analyst_name || inv.analyst || '—'}</td>
            <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${inv.notes || ''}">${inv.notes || '—'}</td>
            <td style="white-space:nowrap;">${fmtDate(inv.created_at)}</td>
        </tr>`).join('')}</tbody>`;
        wrap.innerHTML = ''; wrap.appendChild(t);
    } catch (e) { wrap.innerHTML = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`; }
}

async function loadAuditLog() {
    const wrap = document.getElementById('audit-table-wrap');
    const ow = document.getElementById('overview-audit-wrap');
    if (wrap) wrap.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
    const buildTable = rows => {
        const t = document.createElement('table'); t.className = 'data-table';
        t.innerHTML = `<thead><tr><th>Timestamp</th><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
        <tbody>${rows.map(e => `<tr>
            <td style="white-space:nowrap;">${fmtDate(e.timestamp)}</td>
            <td>${e.actor_name || e.actor || '—'}</td>
            <td><code style="font-size:.78rem;">${e.action || '—'}</code></td>
            <td>${e.entity_type || '—'} ${e.entity_id ? '#' + e.entity_id : ''}</td>
            <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${e.detail || ''}">${e.detail || '—'}</td>
        </tr>`).join('')}</tbody>`;
        return t;
    };
    try {
        const data = await ArgusAPI.getAuditLog();
        const rows = data.results || data;
        if (!rows?.length) {
            const m = '<div class="empty-state"><p>No audit events yet.</p></div>';
            if (wrap) wrap.innerHTML = m; if (ow) ow.innerHTML = m; return;
        }
        if (wrap) { wrap.innerHTML = ''; wrap.appendChild(buildTable(rows)); }
        if (ow) { ow.innerHTML = ''; ow.appendChild(buildTable(rows.slice(0, 5))); }
    } catch (e) {
        const m = `<div class="empty-state"><p style="color:#ff6b78;">⚠️ ${e.message}</p></div>`;
        if (wrap) wrap.innerHTML = m; if (ow) ow.innerHTML = m;
    }
}

async function loadAll() {
    try { const s = await ArgusAPI.getStats(); renderKPI(s); renderCharts(s); } catch (e) { console.error(e); }
    loadTransactions(); loadAuditLog();
}
loadAll();
