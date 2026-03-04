import { getAuth, loginWithEmailAndPassword, signupWithEmailAndPassword } from "../lib/auth-store.js";
import { getDataStore, doc, setDoc } from "../lib/data-store.js";

const auth = getAuth();
const store = getDataStore();

let isLoginMode = true;
const form = document.getElementById("authForm");
const statusMsg = document.getElementById("status-msg");

function updateUI() {
    const nameField = document.getElementById("nameField");
    const roleField = document.getElementById("roleField");
    const formTitle = document.getElementById("formTitle");
    const submitBtn = document.getElementById("submitBtn");
    const toggleText = document.getElementById("toggleText");
    const toggleBtn = document.getElementById("toggleBtn");

    if (isLoginMode) {
        nameField.classList.add("hidden");
        roleField.classList.add("hidden");
        formTitle.textContent = "Welcome back, Sir.";
        submitBtn.textContent = "Sign In";
        toggleText.innerHTML = 'New here? <a href="#" id="toggleBtn" class="text-primary text-decoration-none fw-bold">Create Account</a>';
    } else {
        nameField.classList.remove("hidden");
        roleField.classList.remove("hidden");
        formTitle.textContent = "Create your Academic ID";
        submitBtn.textContent = "Sign Up";
        toggleText.innerHTML = 'Already have an account? <a href="#" id="toggleBtn" class="text-primary text-decoration-none fw-bold">Login</a>';
    }

    document.getElementById("toggleBtn").addEventListener("click", (event) => {
        event.preventDefault();
        isLoginMode = !isLoginMode;
        updateUI();
    });
    statusMsg.classList.add("d-none");
}

document.getElementById("toggleBtn").addEventListener("click", (event) => {
    event.preventDefault();
    isLoginMode = !isLoginMode;
    updateUI();
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const fullName = document.getElementById("fullName").value;
    const role = document.getElementById("role").value;

    statusMsg.classList.remove("d-none", "alert-danger", "alert-success");
    statusMsg.classList.add("alert-info");
    statusMsg.textContent = isLoginMode ? "Authenticating..." : "Creating Account...";

    try {
        if (isLoginMode) {
            await loginWithEmailAndPassword(email, password);
            statusMsg.classList.replace("alert-info", "alert-success");
            statusMsg.textContent = "Login Successful! Redirecting...";
            setTimeout(() => {
                window.location.href = "index.html";
            }, 1000);
            return;
        }

        if (!fullName) {
            throw new Error("Please enter your full name.");
        }

        const userCredential = await signupWithEmailAndPassword(email, password, {
            name: fullName,
            role,
        });

        const user = userCredential.user;
        await setDoc(doc(store, "users", user.uid), {
            name: fullName,
            email,
            role,
            createdAt: new Date(),
        }, { merge: true });

        statusMsg.classList.replace("alert-info", "alert-success");
        statusMsg.textContent = "Account Created! Redirecting...";
        setTimeout(() => {
            window.location.href = "index.html";
        }, 1200);
    } catch (error) {
        console.error(error);
        statusMsg.classList.replace("alert-info", "alert-danger");
        statusMsg.textContent = formatErrorMessage(error?.message || "Request failed");
    }
});

function formatErrorMessage(message) {
    const msg = String(message || "");
    if (msg.includes("Email already exists")) return "Email is already registered.";
    if (msg.includes("Invalid credentials")) return "Invalid Email or Password.";
    if (msg.includes("weak-password")) return "Password should be at least 6 characters.";
    return msg;
}
