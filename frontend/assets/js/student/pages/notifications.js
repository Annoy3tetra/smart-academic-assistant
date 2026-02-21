    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
    import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
    import { getFirestore, doc, getDoc, onSnapshot, setDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

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

    const noteContainer = document.getElementById("noteContainer");
    const emptyState = document.getElementById("emptyState");
    const noteText = document.getElementById("noteText");
    const updatedAt = document.getElementById("updatedAt");
    const noteStatus = document.getElementById("noteStatus");
    const refreshBtn = document.getElementById("refreshBtn");

    let stopListening = null;
    let currentUser = null;

    function formatDate(value) {
      if (!value) return "--";
      if (typeof value.toDate === "function") return value.toDate().toLocaleString();
      const parsed = new Date(value);
      return Number.isFinite(parsed.getTime()) ? parsed.toLocaleString() : "--";
    }

    function renderRemark(data) {
      const remark = String(data?.hod_note || "").trim();
      if (!remark) {
        noteContainer.classList.add("d-none");
        emptyState.classList.remove("d-none");
        noteStatus.textContent = "No New Remark";
        noteStatus.className = "status-pill status-none";
        updatedAt.textContent = "Updated: --";
        return;
      }

      noteText.textContent = remark;
      noteContainer.classList.remove("d-none");
      emptyState.classList.add("d-none");
      noteStatus.textContent = "New Remark";
      noteStatus.className = "status-pill status-new";
      updatedAt.textContent = `Updated: ${formatDate(data?.hod_note_updated_at)}`;
    }

    async function loadOnce(uid) {
      const snap = await getDoc(doc(db, "users", uid));
      renderRemark(snap.exists() ? snap.data() : {});
    }

    function listenRemark(uid) {
      if (stopListening) stopListening();
      stopListening = onSnapshot(doc(db, "users", uid), (snap) => {
        renderRemark(snap.exists() ? snap.data() : {});
      }, (error) => {
        console.error("Notification listener error:", error);
      });
    }

    refreshBtn.addEventListener("click", async () => {
      if (!currentUser) return;
      await loadOnce(currentUser.uid);
      await setDoc(doc(db, "users", currentUser.uid), {
        hod_notification_seen_at: serverTimestamp()
      }, { merge: true });
    });

    onAuthStateChanged(auth, async (user) => {
      if (!user) {
        window.location.href = "../../login.html";
        return;
      }
      currentUser = user;
      await loadOnce(user.uid);
      listenRemark(user.uid);
    });
  
