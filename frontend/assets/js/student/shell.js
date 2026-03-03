import { initializeApp } from "../lib/firebase-app-compat.js";
import { getAuth, onAuthStateChanged, signOut } from "../lib/firebase-auth-compat.js";
import { getFirestore, doc, getDoc } from "../lib/firebase-firestore-compat.js";

const firebaseConfig = {};

const navLinks = Array.from(document.querySelectorAll(".sidebar .nav-link"));
const contentFrame = document.querySelector('iframe[name="content-frame"]');

function normalizeRoute(value) {
    if (!value) return "";
    try {
        const url = new URL(value, window.location.href);
        const segments = url.pathname.split("/");
        return String(segments[segments.length - 1] || "").toLowerCase();
    } catch {
        return String(value).split(/[?#]/)[0].split("/").pop().toLowerCase();
    }
}

function setActiveLink(activeLink) {
    navLinks.forEach((link) => link.classList.remove("active"));
    if (activeLink) activeLink.classList.add("active");
}

function setActiveByPath(pathLike) {
    const targetRoute = normalizeRoute(pathLike);
    if (!targetRoute) return;

    const matched = navLinks.find((link) => normalizeRoute(link.getAttribute("href")) === targetRoute);
    if (matched) setActiveLink(matched);
}

function bindSidebarNavigation() {
    navLinks.forEach((link) => {
        link.addEventListener("click", () => setActiveLink(link));
    });

    if (contentFrame) {
        contentFrame.addEventListener("load", () => {
            try {
                setActiveByPath(contentFrame.contentWindow?.location?.href || contentFrame.getAttribute("src"));
            } catch {
                setActiveByPath(contentFrame.getAttribute("src"));
            }
        });
    }

    setActiveByPath(contentFrame?.getAttribute("src"));
}

// Backward compatibility for inline onclick="setActive(this)" usage.
window.setActive = setActiveLink;

bindSidebarNavigation();

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

onAuthStateChanged(auth, async (user) => {
    if (user) {
        try {
            const userSnap = await getDoc(doc(db, "users", user.uid));
            const userData = userSnap.exists() ? userSnap.data() : {};
            const roleValue = String(userData?.role || "Student").toLowerCase();

            if (roleValue.includes("admin") || roleValue.includes("prof") || roleValue.includes("hod")) {
                window.location.href = "../admin/index.html";
                return;
            }

            const displayName = String(userData?.name || user.email.split("@")[0] || "Student").trim();
            document.getElementById("user-name").textContent = displayName;
        } catch (error) {
            console.error("Role check failed:", error);
            window.location.href = "../login.html";
        }
    } else {
        window.location.href = "../login.html";
    }
});

document.getElementById("logout-btn").addEventListener("click", () => {
    signOut(auth).then(() => {
        window.location.href = "../login.html";
    }).catch((error) => {
        console.error("Logout Error:", error);
    });
});
