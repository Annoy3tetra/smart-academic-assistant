import { apiRequest, clearSession, getStoredUser, getToken, setSession } from "./backend-client.js";

const listeners = new Set();
const authState = {
    currentUser: getStoredUser(),
};
let bootstrapped = false;

function emitAuthState() {
    listeners.forEach((listener) => {
        try {
            listener(authState.currentUser);
        } catch (error) {
            console.error("Auth listener error:", error);
        }
    });
}

async function refreshCurrentUser() {
    const token = getToken();
    if (!token) {
        authState.currentUser = null;
        emitAuthState();
        return;
    }

    try {
        const data = await apiRequest("/students/me", { auth: true });
        authState.currentUser = data?.user ?? null;
        if (authState.currentUser) {
            setSession(token, authState.currentUser);
        }
    } catch {
        clearSession();
        authState.currentUser = null;
    }
    emitAuthState();
}

export function getAuth() {
    return authState;
}

export function onAuthStateChanged(auth, callback) {
    listeners.add(callback);
    const token = getToken();
    if (auth.currentUser) {
        Promise.resolve().then(() => callback(auth.currentUser));
    } else if (!token) {
        Promise.resolve().then(() => callback(null));
    }

    if (!bootstrapped) {
        bootstrapped = true;
        refreshCurrentUser();
    }

    return () => listeners.delete(callback);
}

export async function loginWithEmailAndPassword(email, password) {
    const data = await apiRequest("/students/login-json", {
        method: "POST",
        auth: false,
        body: { email, password },
    });

    const user = data?.user ?? null;
    if (!data?.access_token || !user) {
        throw new Error("Invalid login response");
    }

    setSession(data.access_token, user);
    authState.currentUser = user;
    emitAuthState();
    return { user };
}

export async function signupWithEmailAndPassword(email, password, profile = {}) {
    const name = String(profile?.name || email.split("@")[0] || "Student").trim();
    const role = String(profile?.role || "Student").trim();

    const data = await apiRequest("/students/signup", {
        method: "POST",
        auth: false,
        body: { email, password, name, role },
    });

    const user = data?.user ?? null;
    if (!data?.access_token || !user) {
        throw new Error("Invalid signup response");
    }

    setSession(data.access_token, user);
    authState.currentUser = user;
    emitAuthState();
    return { user };
}

export async function signOut(auth) {
    clearSession();
    auth.currentUser = null;
    emitAuthState();
}
