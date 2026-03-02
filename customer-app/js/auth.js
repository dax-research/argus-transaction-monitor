// auth.js — Login page logic
document.addEventListener("DOMContentLoaded", () => {
    // Redirect if already logged in
    if (getToken()) {
        window.location.href = "dashboard.html";
        return;
    }

    const form = document.getElementById("login-form");
    const btn = document.getElementById("login-btn");
    const alertBox = document.getElementById("alert-box");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        setAlert(null);
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div> Signing in…`;

        try {
            const data = await apiLogin(username, password);
            saveSession(data.token, username);
            // Set a default mock balance
            localStorage.setItem("argus_balance", "250000.00");
            window.location.href = "dashboard.html";
        } catch (err) {
            setAlert("error", "⚠️ " + err.message);
            btn.disabled = false;
            btn.innerHTML = "Sign In";
        }
    });

    function setAlert(type, message) {
        if (!type) { alertBox.style.display = "none"; return; }
        alertBox.className = `alert alert-${type}`;
        alertBox.textContent = message;
        alertBox.style.display = "flex";
    }
});
