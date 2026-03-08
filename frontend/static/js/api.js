/**
 * ArgusAPI — typed wrappers for all Django REST endpoints.
 * Requires auth.js loaded first (for ArgusAuth.authFetch).
 */

const ArgusAPI = (() => {

    async function _fetch(url, opts = {}) {
        const res = await ArgusAuth.authFetch(url, opts);
        if (!res.ok) {
            let errMsg = `HTTP ${res.status}`;
            try {
                const data = await res.json();
                const msgs = Object.entries(data)
                    .flatMap(([k, v]) =>
                        (Array.isArray(v) ? v : [v]).map(m =>
                            `${k !== 'detail' && k !== 'non_field_errors' ? k + ': ' : ''}${m}`
                        )
                    );
                if (msgs.length) errMsg = msgs.join(' · ');
            } catch { /* ignore */ }
            throw new Error(errMsg);
        }
        return res.json();
    }

    // ── Dashboard ──────────────────────────────────────────────────────────

    async function getStats() {
        return _fetch('/api/dashboard/stats/');
    }

    async function getTransactions(statusFilter = '', riskFilter = '') {
        const params = new URLSearchParams();
        if (statusFilter) params.set('status', statusFilter);
        if (riskFilter) params.set('risk_level', riskFilter);
        const qs = params.toString() ? `?${params}` : '';
        return _fetch(`/api/dashboard/transactions/${qs}`);
    }

    async function getInvestigations() {
        return _fetch('/api/dashboard/investigations/');
    }

    async function updateInvestigation(id, data) {
        return _fetch(`/api/dashboard/investigations/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    async function getAuditLog() {
        return _fetch('/api/dashboard/audit-log/');
    }

    // ── Auth ───────────────────────────────────────────────────────────────

    const OAUTH_CLIENT_ID = 'argus-frontend-client';

    /** Decode a JWT payload WITHOUT verification (signature is checked server-side). */
    function _decodeJwtPayload(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            return JSON.parse(atob(base64));
        } catch {
            return {};
        }
    }

    async function login(email, password) {
        // OAuth2 Resource Owner Password Credentials grant
        const body = new URLSearchParams({
            grant_type: 'password',
            username: email,       // DOT uses 'username' field; our validator maps email→username
            password: password,
            client_id: OAUTH_CLIENT_ID,
            scope: 'read write',
        });

        const res = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        });

        if (!res.ok) {
            let errMsg = 'Login failed.';
            try {
                const data = await res.json();
                const msgs = Object.values(data).flat();
                if (msgs.length) errMsg = msgs.join(' \u00b7 ');
            } catch { /* ignore */ }
            throw new Error(errMsg);
        }

        // Server returns { access, refresh, user } — same shape as before
        return res.json();
    }

    // Self-service registration: auditors only; analysts are provisioned by admins.

    return { getStats, getTransactions, getInvestigations, updateInvestigation, getAuditLog, login, register };
})();
