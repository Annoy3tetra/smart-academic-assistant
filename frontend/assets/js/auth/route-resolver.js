    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
    import { getAuth, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
    import { getFirestore, doc, getDoc } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

    const firebaseConfig = {
      apiKey: "AIzaSyDJlQru_9q4kcnDmK6sFX0W-_GP3n0YYrA",
      authDomain: "testing-c2417.firebaseapp.com",
      projectId: "testing-c2417",
      storageBucket: "testing-c2417.firebasestorage.app",
      messagingSenderId: "27724276111",
      appId: "1:27724276111:web:a289d7642e1227818d6bfa",
      measurementId: "G-KTK16HRSX4"
    };

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
  
