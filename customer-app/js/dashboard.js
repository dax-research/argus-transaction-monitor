// dashboard.js — Send Money logic & recent transactions
document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;

  const username = getUsername();

  // Greeting
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  document.getElementById("greeting").textContent = `${greet}, ${username} 👋`;
  document.getElementById("account-id").textContent = username;

  // Load real balance from API
  let balance = parseFloat(localStorage.getItem("argus_balance") || "250000");
  try {
    const profile = await apiGetProfile();
    balance = parseFloat(profile.account_balance);
    localStorage.setItem("argus_balance", balance);
  } catch (_) { /* use cached balance if API fails */ }

  updateBalanceDisplay(balance);
  document.getElementById("balance").value = balance;

  // Logout
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "index.html";
  });

  // Recent transactions from API
  await renderRecent();

  // Send Money form
  const form = document.getElementById("send-form");
  const btn = document.getElementById("send-btn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const amount = parseFloat(document.getElementById("amount").value);
    const device_type = document.getElementById("device-type").value;
    const bal = parseFloat(document.getElementById("balance").value);
    const city = document.getElementById("city").value;
    const payment_type = document.getElementById("payment-type").value;

    setAlert(null);
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Processing…`;

    try {
      const result = await apiProcessTransaction({ amount, device_type, balance: bal, city, payment_type });
      handleResult(result, amount);
    } catch (err) {
      setAlert("error", "⚠️ " + err.message);
      btn.disabled = false;
      btn.innerHTML = "Send Transaction";
    }
  });

  function handleResult(result, amount) {
    // Save to local cache (for fallback)
    saveToHistory({
      txn_id: result.txn_id,
      amount,
      status: result.status,
      risk_score: result.risk,
      decision: result.decision,
    });

    // Update balance if returned from API
    if (result.balance !== undefined) {
      balance = parseFloat(result.balance);
      localStorage.setItem("argus_balance", balance);
      updateBalanceDisplay(balance);
      document.getElementById("balance").value = balance;
    }

    const resultArea = document.getElementById("result-area");
    resultArea.style.display = "block";

    btn.disabled = false;
    btn.innerHTML = "Send Transaction";

    if (result.decision === "ALLOW") {
      resultArea.innerHTML = buildResultCard("success", "✅", "Transaction Approved!", "Your payment was processed successfully.", result);
    } else if (result.decision === "CHALLENGE") {
      savePendingOTP(result.txn_id, null, amount);
      resultArea.innerHTML = buildChallengeCard(result);
    } else {
      resultArea.innerHTML = buildResultCard("blocked", "🚫", "Transaction Blocked", "Our fraud engine flagged this transaction.", result);
    }

    renderRecent();
  }

  function updateBalanceDisplay(bal) {
    document.getElementById("balance-display").textContent =
      `₹${bal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  }

  function buildResultCard(type, icon, title, subtitle, result) {
    const riskPct = Math.round(result.risk * 100);
    const riskColor = riskPct < 30 ? "#10b981" : riskPct < 65 ? "#f59e0b" : "#ef4444";
    return `
      <div class="result-card ${type}">
        <span class="result-icon">${icon}</span>
        <p class="result-title">${title}</p>
        <p class="result-subtitle">${subtitle}</p>
        <div class="result-meta">
          <div class="result-meta-item">
            <p class="meta-label">TXN ID</p>
            <p class="meta-value" style="font-size:11px;">${result.txn_id}</p>
          </div>
          <div class="result-meta-item">
            <p class="meta-label">Decision</p>
            <p class="meta-value">${result.decision}</p>
          </div>
          <div class="result-meta-item">
            <p class="meta-label">Risk Score</p>
            <p class="meta-value" style="color:${riskColor}">${riskPct}%</p>
          </div>
        </div>
        <div class="risk-meter">
          <div class="risk-bar-track">
            <div class="risk-bar-fill" style="width:${riskPct}%; background: linear-gradient(90deg, #10b981, ${riskColor});"></div>
          </div>
        </div>
        <button class="btn btn-secondary btn-full mt-4" onclick="resetForm()">New Transaction</button>
      </div>`;
  }

  function buildChallengeCard(result) {
    return `
      <div class="result-card challenge">
        <span class="result-icon">🔐</span>
        <p class="result-title">Verification Required</p>
        <p class="result-subtitle">This transaction needs OTP verification (Risk: ${Math.round(result.risk * 100)}%)</p>
        <div class="result-meta">
          <div class="result-meta-item">
            <p class="meta-label">TXN ID</p>
            <p class="meta-value" style="font-size:11px;">${result.txn_id}</p>
          </div>
          <div class="result-meta-item">
            <p class="meta-label">Status</p>
            <p class="meta-value">OTP_REQUIRED</p>
          </div>
        </div>
        <a href="otp.html?txn_id=${encodeURIComponent(result.txn_id)}" class="btn btn-primary btn-full">
          Verify with OTP →
        </a>
      </div>`;
  }

  window.resetForm = function () {
    document.getElementById("result-area").style.display = "none";
    document.getElementById("send-form").reset();
    document.getElementById("balance").value = balance;
  };

  async function renderRecent() {
    const list = document.getElementById("recent-list");
    let transactions = [];

    try {
      const data = await apiGetHistory(1, 5);
      transactions = data.results || [];
    } catch (_) {
      // Fallback to localStorage cache
      transactions = getHistory().slice(0, 5).map(t => ({
        txn_id: t.txn_id,
        amount: t.amount,
        status: t.status,
        created_at: t.timestamp,
      }));
    }

    if (!transactions.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No transactions yet.<br>Send money to get started!</p></div>`;
      return;
    }

    list.innerHTML = transactions.map(txn => {
      const badge = statusBadge(txn.status);
      const date = new Date(txn.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" });
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--border);">
          <div>
            <p class="txn-id">${txn.txn_id}</p>
            <p class="text-sm text-muted">${date}</p>
          </div>
          <div style="text-align:right;">
            <p style="font-weight:600; margin-bottom:4px;">₹${parseFloat(txn.amount).toLocaleString("en-IN")}</p>
            ${badge}
          </div>
        </div>`;
    }).join("");
  }

  function setAlert(type, message) {
    const el = document.getElementById("send-alert");
    if (!type) { el.style.display = "none"; return; }
    el.className = `alert alert-${type}`;
    el.textContent = message;
    el.style.display = "flex";
  }
});

function statusBadge(status) {
  const map = {
    SUCCESS: ["success", "✓ Success"],
    OTP_REQUIRED: ["warning", "⏳ OTP Required"],
    BLOCKED: ["danger", "✗ Blocked"],
    FAILED: ["danger", "✗ Failed"],
    INITIATED: ["info", "⋯ Initiated"],
  };
  const [cls, label] = map[status] || ["info", status];
  return `<span class="badge badge-${cls}">${label}</span>`;
}
