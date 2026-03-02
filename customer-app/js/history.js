// history.js — Transaction history page logic (fetches from backend API)
document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "index.html";
  });

  // Remove the clear button (no longer deletes from DB, so hide it)
  const clearBtn = document.getElementById("clear-btn");
  if (clearBtn) clearBtn.style.display = "none";

  await renderHistory();

  async function renderHistory() {
    const el = document.getElementById("history-content");
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⏳</div><p>Loading transactions…</p></div>`;

    let transactions = [];
    try {
      const data = await apiGetHistory(1, 100);
      transactions = data.results || [];
    } catch (err) {
      el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Failed to load history.<br><small>${err.message}</small></p></div>`;
      return;
    }

    // Stats
    const total = transactions.length;
    const success = transactions.filter(t => t.status === "SUCCESS").length;
    const otp = transactions.filter(t => t.status === "OTP_REQUIRED").length;
    const blocked = transactions.filter(t => t.status === "BLOCKED" || t.status === "FAILED").length;

    document.getElementById("stat-total").textContent = total;
    document.getElementById("stat-success").textContent = success;
    document.getElementById("stat-otp").textContent = otp;
    document.getElementById("stat-blocked").textContent = blocked;

    if (!transactions.length) {
      el.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📭</div>
          <p>No transactions yet.</p>
          <a href="dashboard.html" class="link" style="display:inline-block; margin-top:12px;">Send your first transaction →</a>
        </div>`;
      return;
    }

    el.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>TXN ID</th>
              <th>Amount</th>
              <th>City</th>
              <th>Payment Type</th>
              <th>Risk Score</th>
              <th>Decision</th>
              <th>Status</th>
              <th>Date & Time</th>
            </tr>
          </thead>
          <tbody>
            ${transactions.map(txn => buildRow(txn)).join("")}
          </tbody>
        </table>
      </div>`;
  }

  function buildRow(txn) {
    const riskPct = txn.risk_score != null ? Math.round(txn.risk_score * 100) : null;
    const riskColor = riskPct == null ? "var(--text-muted)"
      : riskPct < 30 ? "var(--accent-green)"
        : riskPct < 65 ? "var(--accent-yellow)"
          : "var(--accent-red)";

    const badge = statusBadge(txn.status);
    const decisionBadge = decisionLabel(txn.fraud_decision);
    const date = new Date(txn.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    const amount = `₹${parseFloat(txn.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

    return `
      <tr>
        <td><span class="txn-id">${txn.txn_id}</span></td>
        <td style="font-weight:600; color:var(--text-primary);">${amount}</td>
        <td style="color:var(--text-muted);">${txn.city || "—"}</td>
        <td style="color:var(--text-muted);">${txn.payment_type || "—"}</td>
        <td>
          <span style="color:${riskColor}; font-weight:600;">
            ${riskPct != null ? riskPct + "%" : "—"}
          </span>
        </td>
        <td>${decisionBadge}</td>
        <td>${badge}</td>
        <td style="color:var(--text-muted); font-size:13px;">${date}</td>
      </tr>`;
  }
});

function statusBadge(status) {
  const map = {
    SUCCESS: ["success", "✓ Success"],
    OTP_REQUIRED: ["warning", "⏳ OTP Pending"],
    BLOCKED: ["danger", "✗ Blocked"],
    FAILED: ["danger", "✗ Failed"],
    INITIATED: ["info", "⋯ Initiated"],
  };
  const [cls, label] = map[status] || ["info", status];
  return `<span class="badge badge-${cls}">${label}</span>`;
}

function decisionLabel(decision) {
  const map = {
    ALLOW: ["success", "✓ Allow"],
    CHALLENGE: ["warning", "⚡ Challenge"],
    DENY: ["danger", "✗ Deny"],
  };
  if (!decision) return `<span class="text-muted">—</span>`;
  const [cls, label] = map[decision] || ["info", decision];
  return `<span class="badge badge-${cls}">${label}</span>`;
}
