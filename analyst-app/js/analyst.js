/**
 * analyst.js — Argus Analyst Dashboard Logic
 */
const API = "http://127.0.0.1:8001";
let authToken = null;
let currentPage = 1;
const PAGE_SIZE = 20;
let riskChart = null;

// ── Login ───────────────────────────────────────────────────────────────────
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const btn = document.getElementById("login-btn");
    const alertEl = document.getElementById("login-alert");

    btn.disabled = true;
    btn.textContent = "Signing in…";
    alertEl.style.display = "none";

    try {
        const res = await fetch(`${API}/api-token-auth/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.non_field_errors?.[0] || "Invalid credentials");

        authToken = data.token;
        document.getElementById("nav-user").textContent = `👤 ${username}`;
        document.getElementById("login-screen").classList.add("hidden");
        document.getElementById("dashboard-screen").classList.remove("hidden");
        loadDashboard();
    } catch (err) {
        alertEl.textContent = "⚠️ " + err.message;
        alertEl.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.textContent = "Sign In";
    }
});

document.getElementById("logout-btn").addEventListener("click", () => {
    authToken = null;
    document.getElementById("dashboard-screen").classList.add("hidden");
    document.getElementById("login-screen").classList.remove("hidden");
    document.getElementById("login-form").reset();
});

// ── Filter changes ───────────────────────────────────────────────────────────
document.getElementById("filter-status").addEventListener("change", () => { currentPage = 1; loadTransactions(); });
document.getElementById("filter-decision").addEventListener("change", () => { currentPage = 1; loadTransactions(); });
document.getElementById("prev-btn").addEventListener("click", () => { currentPage--; loadTransactions(); });
document.getElementById("next-btn").addEventListener("click", () => { currentPage++; loadTransactions(); });

// ── Load everything ──────────────────────────────────────────────────────────
async function loadDashboard() {
    await Promise.all([loadStats(), loadTransactions()]);
}

async function loadStats() {
    try {
        const res = await fetch(`${API}/api/analyst/stats/`, {
            headers: { Authorization: `Token ${authToken}` }
        });
        if (res.status === 403) { showError("Access denied. Staff account required."); return; }
        const data = await res.json();

        document.getElementById("s-total").textContent = data.total;
        document.getElementById("s-success").textContent = data.success;
        document.getElementById("s-blocked").textContent = data.blocked;
        document.getElementById("s-otp").textContent = data.otp_pending;
        document.getElementById("s-flagged").textContent = data.flagged;

        renderRiskChart(data.risk_distribution);
    } catch (err) {
        console.error("Stats load failed:", err);
    }
}

function renderRiskChart(dist) {
    const ctx = document.getElementById("risk-chart").getContext("2d");
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Low Risk (<30%)", "Medium Risk (30-65%)", "High Risk (>65%)"],
            datasets: [{
                data: [dist.low, dist.medium, dist.high],
                backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { color: "#e6edf3", font: { size: 13 } } },
            }
        }
    });
}

async function loadTransactions() {
    const status = document.getElementById("filter-status").value;
    const decision = document.getElementById("filter-decision").value;
    const tableWrap = document.getElementById("table-wrap");
    tableWrap.innerHTML = `<div class="empty">Loading…</div>`;

    let url = `${API}/api/analyst/transactions/?page=${currentPage}&page_size=${PAGE_SIZE}`;
    if (status) url += `&status=${status}`;
    if (decision) url += `&decision=${decision}`;

    try {
        const res = await fetch(url, { headers: { Authorization: `Token ${authToken}` } });
        if (res.status === 403) {
            tableWrap.innerHTML = `<div class="empty">⛔ Access denied. This account is not a staff account.</div>`;
            return;
        }
        const data = await res.json();
        const transactions = data.results || [];
        const total = data.count || 0;
        const totalPages = Math.ceil(total / PAGE_SIZE);

        document.getElementById("page-label").textContent = `Page ${currentPage} of ${totalPages || 1}`;
        document.getElementById("prev-btn").disabled = currentPage <= 1;
        document.getElementById("next-btn").disabled = currentPage >= totalPages;

        if (!transactions.length) {
            tableWrap.innerHTML = `<div class="empty">No transactions found.</div>`;
            return;
        }

        tableWrap.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>TXN ID</th><th>User</th><th>Amount</th><th>City</th>
            <th>Payment</th><th>Risk</th><th>Decision</th><th>Status</th>
            <th>Date</th><th>Action</th>
          </tr>
        </thead>
        <tbody>${transactions.map(buildRow).join("")}</tbody>
      </table>`;

        // Attach flag buttons
        transactions.forEach(txn => {
            const btn = document.getElementById(`flag-${txn.txn_id}`);
            if (btn) {
                btn.addEventListener("click", () => flagTransaction(txn.txn_id, btn));
            }
        });
    } catch (err) {
        tableWrap.innerHTML = `<div class="empty">⚠️ ${err.message}</div>`;
    }
}

function buildRow(txn) {
    const riskPct = txn.risk_score != null ? Math.round(txn.risk_score * 100) : 0;
    const riskColor = riskPct < 30 ? "#10b981" : riskPct < 65 ? "#f59e0b" : "#ef4444";
    const isFlagged = txn.is_flagged;

    const statusMap = {
        SUCCESS: "badge-success", BLOCKED: "badge-danger",
        OTP_REQUIRED: "badge-warning", FAILED: "badge-danger", INITIATED: "badge-info"
    };
    const decisionMap = { ALLOW: "badge-success", CHALLENGE: "badge-warning", DENY: "badge-danger" };

    const date = new Date(txn.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" });

    return `
    <tr>
      <td style="font-size:11px;color:#8b949e;">${txn.txn_id}</td>
      <td style="font-weight:600;">${txn.user_id}</td>
      <td style="font-weight:600;">₹${parseFloat(txn.amount).toLocaleString("en-IN")}</td>
      <td style="color:#8b949e;">${txn.city || "—"}</td>
      <td style="color:#8b949e;">${txn.payment_type || "—"}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          <div class="risk-bar"><div class="risk-bar-fill" style="width:${riskPct}%;background:${riskColor};"></div></div>
          <span style="color:${riskColor};font-weight:600;">${riskPct}%</span>
        </div>
      </td>
      <td><span class="badge ${decisionMap[txn.fraud_decision] || 'badge-info'}">${txn.fraud_decision || "—"}</span></td>
      <td><span class="badge ${statusMap[txn.status] || 'badge-info'}">${txn.status}</span></td>
      <td style="font-size:12px;color:#8b949e;">${date}</td>
      <td>
        <button class="btn-flag" id="flag-${txn.txn_id}" ${isFlagged ? "disabled" : ""}>
          ${isFlagged ? "Flagged" : "🚩 Flag"}
        </button>
      </td>
    </tr>`;
}

async function flagTransaction(txnId, btn) {
    btn.disabled = true;
    btn.textContent = "Flagging…";
    try {
        const res = await fetch(`${API}/api/analyst/flag/${txnId}/`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Token ${authToken}` },
            body: JSON.stringify({ reason: "Manually flagged by analyst" }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Flag failed");
        btn.textContent = "Flagged";
        showToast(`✅ ${txnId} flagged as fraud`);
        loadStats(); // refresh stats
    } catch (err) {
        btn.disabled = false;
        btn.textContent = "🚩 Flag";
        showToast(`⚠️ ${err.message}`, true);
    }
}

function showToast(msg, isError = false) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    if (isError) el.style.background = "#7f1d1d";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

function showError(msg) {
    document.getElementById("table-wrap").innerHTML = `<div class="empty">⛔ ${msg}</div>`;
}
