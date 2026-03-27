/**
 * ArgusAuth — JWT token management and authenticated fetch
 *
 * Storage keys:
 *   argus_access   — short-lived access token
 *   argus_refresh  — long-lived refresh token
 *   argus_user     — JSON string of { id, email, full_name, role }
 */

const ArgusAuth = (() => {
    const BASE = '';   // same origin

    // ── Storage helpers ────────────────────────────────────────────────────
    function getToken() { return localStorage.getItem('argus_access'); }
    function getRefresh() { return localStorage.getItem('argus_refresh'); }
    function getUser() {
        try { return JSON.parse(localStorage.getItem('argus_user')); }
        catch { return null; }
    }
    function setSession(data) {
        localStorage.setItem('argus_access', data.access);
        localStorage.setItem('argus_refresh', data.refresh);
        localStorage.setItem('argus_user', JSON.stringify(data.user));
    }
    function clearSession() {
        localStorage.removeItem('argus_access');
        localStorage.removeItem('argus_refresh');
        localStorage.removeItem('argus_user');
    }

    // ── Token refresh ──────────────────────────────────────────────────────
    async function refreshToken() {
        const refresh = getRefresh();
        if (!refresh) return false;
        try {
            const body = new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refresh,
                client_id: 'argus-frontend-client',
            });
            const res = await fetch(`${BASE}/api/auth/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body,
            });
            if (!res.ok) return false;
            const data = await res.json();
            // Server returns { access, refresh } — update both tokens
            if (data.access) localStorage.setItem('argus_access', data.access);
            if (data.refresh) localStorage.setItem('argus_refresh', data.refresh);
            return true;
        } catch {
            return false;
        }
    }

    // ── Authenticated fetch (auto-refresh on 401) ──────────────────────────
    async function authFetch(url, opts = {}) {
        const token = getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...(opts.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };
        let res = await fetch(`${BASE}${url}`, { ...opts, headers });

        if (res.status === 401) {
            const refreshed = await refreshToken();
            if (refreshed) {
                headers.Authorization = `Bearer ${getToken()}`;
                res = await fetch(`${BASE}${url}`, { ...opts, headers });
            } else {
                logout();
                return res;
            }
        }
        return res;
    }

    // ── Logout ─────────────────────────────────────────────────────────────
    function logout() {
        const token = getToken();
        if (token) {
            fetch(`${BASE}/api/auth/logout/`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            }).catch(() => { });
        }
        clearSession();
        window.location.href = '/';
    }

    // ── Navigation helpers ─────────────────────────────────────────────────
    function getDashboardUrl(role) {
        return role === 'ANALYST' ? '/dashboard/analyst/' : '/dashboard/auditor/';
    }

    /**
     * requireAuth(expectedRole)
     *   If not logged in  → redirect to /login/
     *   If wrong role     → redirect to correct dashboard
     */
    function requireAuth(expectedRole) {
        const user = getUser();
        if (!user || !getToken()) {
            window.location.href = '/login/';
            return;
        }
        if (expectedRole && user.role !== expectedRole) {
            window.location.href = getDashboardUrl(user.role);
        }
    }

    // ── Public API ─────────────────────────────────────────────────────────
    return {
        getToken,
        getRefresh,
        getUser,
        setSession,
        clearSession,
        authFetch,
        logout,
        requireAuth,
        getDashboardUrl,
    };
})();
