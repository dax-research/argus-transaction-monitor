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

    async function login(email, password) {
        const res = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
            let errMsg = 'Login failed.';
            try {
                const data = await res.json();
                const msgs = Object.values(data).flat();
                if (msgs.length) errMsg = msgs.join(' · ');
            } catch { /* ignore */ }
            throw new Error(errMsg);
        }
        return res.json();
    }

    async function register({ full_name, email, password, confirm_password, role }) {
        const res = await fetch('/api/auth/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name, email, password, confirm_password, role }),
        });
        if (!res.ok) {
            let errMsg = 'Registration failed.';
            try {
                const data = await res.json();
                const msgs = Object.entries(data)
                    .flatMap(([k, v]) =>
                        (Array.isArray(v) ? v : [v]).map(m =>
                            `${k !== 'non_field_errors' ? k + ': ' : ''}${m}`
                        )
                    );
                if (msgs.length) errMsg = msgs.join(' · ');
            } catch { /* ignore */ }
            throw new Error(errMsg);
        }
        return res.json();
    }

    return { getStats, getTransactions, getInvestigations, updateInvestigation, getAuditLog, login, register };
})();
