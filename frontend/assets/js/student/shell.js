function setActive(element) {
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            element.classList.add('active');
        }

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
                    document.getElementById('user-name').textContent = displayName;
                } catch (error) {
                    console.error("Role check failed:", error);
                    window.location.href = "../login.html";
                }
            } else {
                window.location.href = "../login.html";
            }
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            signOut(auth).then(() => {
                window.location.href = "../login.html";
            }).catch((error) => {
                console.error("Logout Error:", error);
            });
        });
