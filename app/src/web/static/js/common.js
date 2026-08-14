const tokenKey = "ml_service_token";

function getToken() {
    return localStorage.getItem(tokenKey);
}

function saveToken(token) {
    localStorage.setItem(tokenKey, token);
}

function logout() {
    localStorage.removeItem(tokenKey);
    window.location.href = "/";
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = "/auth";
        return false;
    }
    return true;
}

async function apiRequest(path, options = {}, protectedRoute = true) {
    const headers = new Headers(options.headers || {});
    if (options.body) {
        headers.set("Content-Type", "application/json");
    }
    if (protectedRoute && getToken()) {
        headers.set("Authorization", `Bearer ${getToken()}`);
    }

    const response = await fetch(path, {...options, headers});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        if (response.status === 401 && protectedRoute) {
            localStorage.removeItem(tokenKey);
        }
        const error = new Error(data.error?.message || "Не удалось выполнить запрос");
        error.status = response.status;
        error.details = data.error?.details;
        throw error;
    }
    return data;
}

function showMessage(element, message, type = "danger") {
    element.className = `alert alert-${type}`;
    element.textContent = message;
    element.hidden = false;
}

function hideMessage(element) {
    element.hidden = true;
}

function formatDate(value) {
    return new Date(value).toLocaleString("ru-RU");
}

function addCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "—";
    row.appendChild(cell);
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-logout]").forEach((button) => {
        button.addEventListener("click", logout);
    });
    document.querySelectorAll("[data-auth-only]").forEach((element) => {
        element.hidden = !getToken();
    });
    document.querySelectorAll("[data-guest-only]").forEach((element) => {
        element.hidden = Boolean(getToken());
    });
});
