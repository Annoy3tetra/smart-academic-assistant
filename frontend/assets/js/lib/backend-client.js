const TOKEN_KEY = "edumint_jwt_token";
const USER_KEY = "edumint_auth_user";

function getApiBases() {
    return [
        window.localStorage.getItem("apiBaseUrl"),
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ].filter(Boolean);
}

function safeJsonParse(raw, fallback = null) {
    try {
        return JSON.parse(raw);
    } catch {
        return fallback;
    }
}

async function parseResponse(response) {
    const text = await response.text();
    const json = safeJsonParse(text, null);
    return { text, json };
}

function errorFromPayload(payload, fallback) {
    if (!payload) return fallback;
    if (typeof payload === "string") return payload;
    if (typeof payload.detail === "string") return payload.detail;
    return fallback;
}

export function getToken() {
    return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
    const raw = window.localStorage.getItem(USER_KEY);
    return safeJsonParse(raw, null);
}

export function setSession(token, user) {
    if (token) {
        window.localStorage.setItem(TOKEN_KEY, token);
    }
    if (user) {
        window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
}

export function clearSession() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
}

export async function apiRequest(path, options = {}) {
    const {
        method = "GET",
        body = undefined,
        headers = {},
        auth = true,
        allow404 = false,
    } = options;

    const token = getToken();
    const mergedHeaders = { ...headers };

    if (body !== undefined && !("Content-Type" in mergedHeaders)) {
        mergedHeaders["Content-Type"] = "application/json";
    }

    if (auth && token) {
        mergedHeaders.Authorization = `Bearer ${token}`;
    }

    const payload = body === undefined ? undefined : JSON.stringify(body);

    let lastError = null;
    for (const base of getApiBases()) {
        try {
            const response = await fetch(`${base}${path}`, {
                method,
                headers: mergedHeaders,
                body: payload,
            });

            const { text, json } = await parseResponse(response);

            if (response.ok) {
                return json ?? {};
            }

            if (allow404 && response.status === 404) {
                return null;
            }

            const fallback = `Request failed with status ${response.status}`;
            throw new Error(errorFromPayload(json ?? text, fallback));
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error("API request failed");
}
