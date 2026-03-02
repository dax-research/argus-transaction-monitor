/**
 * api.js — Argus Transaction Monitor API Client
 * Base URL points to the Django backend running locally.
 */

const API_BASE = "http://127.0.0.1:8001";

/**
 * Login and retrieve auth token.
 */
async function apiLogin(username, password) {
  const res = await fetch(`${API_BASE}/api-token-auth/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.non_field_errors?.[0] || "Invalid credentials");
  return data;
}

/**
 * Submit a transaction for fraud analysis.
 */
async function apiProcessTransaction(txnData) {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/transaction/process/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Token ${token}`,
    },
    body: JSON.stringify(txnData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Transaction failed");
  return data;
}

/**
 * Verify OTP for a challenged transaction.
 */
async function apiVerifyOTP(txnId, otp) {
  const res = await fetch(`${API_BASE}/api/verify-otp/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ txn_id: txnId, otp }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "OTP verification failed");
  return data;
}

/**
 * Fetch paginated transaction history from the backend.
 */
async function apiGetHistory(page = 1, pageSize = 20) {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/transactions/?page=${page}&page_size=${pageSize}`, {
    headers: { Authorization: `Token ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load history");
  return data;
}

/**
 * Fetch current user's profile and account balance.
 */
async function apiGetProfile() {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");

  const res = await fetch(`${API_BASE}/api/profile/`, {
    headers: { Authorization: `Token ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load profile");
  return data;
}

// ---- Auth Helpers ----
function getToken() { return localStorage.getItem("argus_token"); }
function getUsername() { return localStorage.getItem("argus_username"); }

function saveSession(token, username) {
  localStorage.setItem("argus_token", token);
  localStorage.setItem("argus_username", username);
}

function clearSession() {
  localStorage.removeItem("argus_token");
  localStorage.removeItem("argus_username");
  localStorage.removeItem("argus_balance");
  localStorage.removeItem("argus_txn_history");
  localStorage.removeItem("argus_pending_otp");
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "index.html";
    return false;
  }
  return true;
}

// ---- Transaction History Helpers (local cache for dashboard recent list) ----
function getHistory() {
  try { return JSON.parse(localStorage.getItem("argus_txn_history") || "[]"); }
  catch { return []; }
}

function saveToHistory(txn) {
  const history = getHistory();
  history.unshift({ ...txn, timestamp: new Date().toISOString() });
  localStorage.setItem("argus_txn_history", JSON.stringify(history.slice(0, 50)));
}

// ---- Pending OTP State ----
function savePendingOTP(txnId, otpCode, amount) {
  localStorage.setItem("argus_pending_otp", JSON.stringify({ txnId, otpCode, amount }));
}

function getPendingOTP() {
  try { return JSON.parse(localStorage.getItem("argus_pending_otp") || "null"); }
  catch { return null; }
}

function clearPendingOTP() {
  localStorage.removeItem("argus_pending_otp");
}

// ---- Inactivity Auto-Logout (15 minutes) ----
(function setupInactivityLogout() {
  const TIMEOUT_MS = 15 * 60 * 1000;   // 15 minutes
  const WARN_MS = 13 * 60 * 1000;      // warn at 13 minutes (2 min before logout)
  let logoutTimer, warnTimer, toastEl;

  function resetTimers() {
    clearTimeout(logoutTimer);
    clearTimeout(warnTimer);
    if (toastEl) { toastEl.remove(); toastEl = null; }

    warnTimer = setTimeout(() => {
      toastEl = document.createElement("div");
      toastEl.id = "inactivity-toast";
      toastEl.innerHTML = `⏰ You'll be logged out in 2 minutes due to inactivity. <button onclick="document.getElementById('inactivity-toast').remove()" style="margin-left:12px;background:transparent;border:1px solid #fff;color:#fff;padding:2px 10px;border-radius:6px;cursor:pointer;">Stay</button>`;
      Object.assign(toastEl.style, {
        position: "fixed", bottom: "24px", left: "50%", transform: "translateX(-50%)",
        background: "#b45309", color: "#fff", padding: "14px 20px", borderRadius: "10px",
        zIndex: "9999", fontSize: "14px", boxShadow: "0 4px 20px rgba(0,0,0,0.4)"
      });
      document.body.appendChild(toastEl);
    }, WARN_MS);

    logoutTimer = setTimeout(() => {
      clearSession();
      window.location.href = "index.html";
    }, TIMEOUT_MS);
  }

  // Only activate if user is logged in
  if (getToken()) {
    ["mousemove", "keydown", "click", "touchstart", "scroll"].forEach(evt =>
      document.addEventListener(evt, resetTimers, { passive: true })
    );
    resetTimers();
  }
})();
