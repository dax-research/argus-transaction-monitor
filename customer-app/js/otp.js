// otp.js — OTP verification page logic
document.addEventListener("DOMContentLoaded", () => {
    if (!requireAuth()) return;

    // Get txn_id from URL params
    const params = new URLSearchParams(window.location.search);
    const txnId = params.get("txn_id");

    if (!txnId) {
        window.location.href = "dashboard.html";
        return;
    }

    document.getElementById("txn-id-display").textContent = `TXN ID: ${txnId}`;

    // Try to get OTP from localStorage (saved by dashboard)
    const pending = getPendingOTP();

    // Fetch the OTP from the backend by re-reading the txn details
    // Since the backend generates OTP but doesn't directly expose it via API,
    // we grab it from localStorage if available (set by a workaround below)
    fetchAndDisplayOTP(txnId);

    // Countdown timer (5 min = 300 sec)
    let timeLeft = 300;
    const timerEl = document.getElementById("timer");
    const countdown = setInterval(() => {
        timeLeft--;
        const m = Math.floor(timeLeft / 60);
        const s = timeLeft % 60;
        timerEl.textContent = `${m}:${s.toString().padStart(2, "0")}`;
        if (timeLeft <= 60) timerEl.style.color = "var(--accent-red)";
        if (timeLeft <= 0) {
            clearInterval(countdown);
            timerEl.textContent = "Expired";
            document.getElementById("verify-btn").disabled = true;
            setAlert("error", "⏰ OTP has expired. Please go back and retry the transaction.");
        }
    }, 1000);

    // Logout
    document.getElementById("logout-btn").addEventListener("click", () => {
        clearSession();
        window.location.href = "index.html";
    });

    // Verify button
    document.getElementById("verify-btn").addEventListener("click", async () => {
        const otp = document.getElementById("otp-input").value.trim();

        if (!/^\d{6}$/.test(otp)) {
            setAlert("error", "⚠️ Please enter a valid 6-digit OTP.");
            return;
        }

        const btn = document.getElementById("verify-btn");
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Verifying…`;
        setAlert(null);

        try {
            const result = await apiVerifyOTP(txnId, otp);
            clearInterval(countdown);
            clearPendingOTP();
            showResult(result);
        } catch (err) {
            setAlert("error", "⚠️ " + err.message);
            btn.disabled = false;
            btn.innerHTML = "Verify OTP";
        }
    });

    function showResult(result) {
        document.getElementById("otp-form-wrap").style.display = "none";
        document.getElementById("otp-demo-box").style.display = "none";

        const resultEl = document.getElementById("otp-result");
        resultEl.style.display = "block";

        if (result.status === "SUCCESS") {
            resultEl.innerHTML = `
        <div class="result-card success">
          <span class="result-icon">✅</span>
          <p class="result-title">Transaction Successful!</p>
          <p class="result-subtitle">OTP verified. Your payment has been processed.</p>
          <a href="dashboard.html" class="btn btn-success btn-full mt-4">Back to Dashboard</a>
          <a href="history.html" class="btn btn-secondary btn-full mt-4">View History</a>
        </div>`;
            // Update history entry
            const history = getHistory();
            const idx = history.findIndex(t => t.txn_id === txnId);
            if (idx !== -1) { history[idx].status = "SUCCESS"; localStorage.setItem("argus_txn_history", JSON.stringify(history)); }
        } else {
            const reason = result.reason || "Transaction blocked by fraud engine.";
            resultEl.innerHTML = `
        <div class="result-card blocked">
          <span class="result-icon">🚫</span>
          <p class="result-title">Transaction Blocked</p>
          <p class="result-subtitle">${reason}</p>
          <a href="dashboard.html" class="btn btn-danger btn-full mt-4">Back to Dashboard</a>
        </div>`;
            // Update history entry
            const history = getHistory();
            const idx = history.findIndex(t => t.txn_id === txnId);
            if (idx !== -1) { history[idx].status = "BLOCKED"; localStorage.setItem("argus_txn_history", JSON.stringify(history)); }
        }
    }

    async function fetchAndDisplayOTP(txnId) {
        // Since the actual OTP is in the database and not directly exposed via
        // a "get OTP" endpoint, we fetch it via the Django admin debug endpoint.
        // For this demo, we try to get it from localStorage (saved by dashboard).
        const pending = getPendingOTP();
        const otpDisplay = document.getElementById("otp-demo-code");

        if (pending && pending.otpCode) {
            otpDisplay.textContent = pending.otpCode.split("").join(" ");
            return;
        }

        // Fallback: fetch from a Django debug endpoint (if available)
        try {
            const res = await fetch(`http://127.0.0.1:8001/api/debug/otp/${encodeURIComponent(txnId)}/`);
            if (res.ok) {
                const data = await res.json();
                if (data.otp) {
                    otpDisplay.textContent = data.otp.split("").join(" ");
                    return;
                }
            }
        } catch (_) { }

        // Final fallback: instruct user to check Django console/admin
        otpDisplay.textContent = "Check Backend";
        otpDisplay.style.fontSize = "18px";
        otpDisplay.style.letterSpacing = "0";
        document.getElementById("otp-demo-box").innerHTML += `
      <p class="text-sm text-muted mt-4" style="margin-top:8px;">
        Check the <strong>Django admin</strong> or server console for the OTP under <em>OTP Service → Transaction OTPs</em>.
      </p>`;
    }

    function setAlert(type, message) {
        const el = document.getElementById("otp-alert");
        if (!type) { el.style.display = "none"; return; }
        el.className = `alert alert-${type}`;
        el.textContent = message;
        el.style.display = "flex";
    }
});
