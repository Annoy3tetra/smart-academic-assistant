    import { initializeApp } from "../../lib/firebase-app-compat.js";
    import { getAuth, onAuthStateChanged } from "../../lib/firebase-auth-compat.js";
    import { getFirestore, doc, getDoc, onSnapshot, setDoc, serverTimestamp } from "../../lib/firebase-firestore-compat.js";

    const firebaseConfig = {};

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
  
