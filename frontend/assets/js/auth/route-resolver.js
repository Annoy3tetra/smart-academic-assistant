    import { initializeApp } from "../lib/firebase-app-compat.js";
    import { getAuth, onAuthStateChanged, signOut } from "../lib/firebase-auth-compat.js";
    import { getFirestore, doc, getDoc } from "../lib/firebase-firestore-compat.js";

    const firebaseConfig = {};

    const statusEl = document.getElementById("status");
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    const db = getFirestore(app);

    function go(path) {
      window.location.href = path;
    }

    async function resolveRoute(user) {
      try {
        const snap = await getDoc(doc(db, "users", user.uid));
        const userData = snap.exists() ? snap.data() : {};
        const role = String(userData?.role || "Student").toLowerCase();

        if (role.includes("admin") || role.includes("prof") || role.includes("hod")) {
          go("admin/index.html");
          return;
        }

        go("student/index.html");
      } catch (error) {
        console.error("Route resolve failed:", error);
        statusEl.textContent = "Unable to load role. Please login again.";
        await signOut(auth);
        setTimeout(() => go("login.html"), 800);
      }
    }

    onAuthStateChanged(auth, (user) => {
      if (!user) {
        go("login.html");
        return;
      }
      resolveRoute(user);
    });
  
