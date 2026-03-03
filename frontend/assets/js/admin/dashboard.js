    import { initializeApp } from "../lib/firebase-app-compat.js";
    import { getAuth, onAuthStateChanged, signOut } from "../lib/firebase-auth-compat.js";
    import { getFirestore, collection, getDocs, query, where, doc, getDoc, setDoc, addDoc, deleteDoc, serverTimestamp } from "../lib/firebase-firestore-compat.js";

    const firebaseConfig = {};

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    const db = getFirestore(app);

    const State = {
      me: null,
      students: [],
      predictionsByUser: new Map(),
      selected: null,
      courses: []
    };

    const UI = {
      status: document.getElementById("statusText"),
      hero: document.getElementById("heroLine"),
      table: document.getElementById("studentsTable"),
      search: document.getElementById("searchInput"),
      riskFilter: document.getElementById("riskFilter"),
      readinessFilter: document.getElementById("readinessFilter"),
      clearFilter: document.getElementById("clearFilterBtn"),
      
      // KPIs
      kStudents: document.getElementById("kStudents"),
      kPercent: document.getElementById("kPercent"),
      kRisk: document.getElementById("kRisk"),
      kReady: document.getElementById("kReady"),
      kStudentsSub: document.getElementById("kStudentsSub"),
      kPercentSub: document.getElementById("kPercentSub"),
      kRiskSub: document.getElementById("kRiskSub"),
      kReadySub: document.getElementById("kReadySub"),

      detail: document.getElementById("studentDetail"),
      selectedUid: document.getElementById("selectedUid"),
      detailRole: document.getElementById("detailRole"),
      saveRole: document.getElementById("saveRoleBtn"),
      note: document.getElementById("interventionNote"),
      saveNote: document.getElementById("saveNoteBtn"),
      
      // Actions
      refresh: document.getElementById("refreshBtn"),
      exportCsv: document.getElementById("exportBtn"),
      logout: document.getElementById("logoutBtn"),
      
      // Course Manager
      courseTopic: document.getElementById("courseTopic"),
      courseSubject: document.getElementById("courseSubject"),
      courseLink: document.getElementById("courseLink"),
      courseChannel: document.getElementById("courseChannel"),
      addCourse: document.getElementById("addCourseBtn"),
      courseList: document.getElementById("courseList")
    };

    const sanitize = (str) => {
      if (!str) return "";
      return String(str).replace(/[&<>"']/g, function(m) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
      });
    };

    const toNumber = (val, defaultVal = 0) => {
      const num = Number(val);
      return Number.isFinite(num) ? num : defaultVal;
    };

    const getAverage = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    const normalizeMarks = (userData) => {
      const raw = userData?.subject_marks ?? userData?.subjectMarks ?? userData?.marks;
      if (!raw) return [];
      
      if (Array.isArray(raw)) {
        return raw.map((e, i) => {
          if (e && typeof e === "object") {
            const mark = toNumber(e.mark ?? e.marks ?? e.score, NaN);
            return Number.isFinite(mark) ? { subject: String(e.subject ?? e.name ?? `Subject ${i + 1}`), mark } : null;
          }
          const mark = toNumber(e, NaN);
          return Number.isFinite(mark) ? { subject: `Subject ${i + 1}`, mark } : null;
        }).filter(Boolean);
      }
      
      if (typeof raw === "object") {
        return Object.entries(raw)
          .map(([s, m]) => ({ subject: String(s), mark: toNumber(m, NaN) }))
          .filter(x => Number.isFinite(x.mark));
      }
      return [];
    };

    const getPercentage = (user) => {
      const marks = normalizeMarks(user).map(x => x.mark);
      return marks.length ? getAverage(marks) : null;
    };

    const formatPercent = (val) => Number.isFinite(val) ? `${val.toFixed(1)}%` : "--";

    const getRiskClass = (risk) => {
      const r = String(risk || "").toUpperCase();
      if (r === "HIGH") return "status-risk";
      if (r === "MEDIUM") return "status-warn";
      return "status-ok";
    };

    const getReadinessClass = (status) => {
      const s = String(status || "").toUpperCase();
      if (s.includes("NOT")) return "status-risk";
      if (s.includes("MODERATE")) return "status-warn";
      return "status-ok";
    };


    function calculateKPIs() {
      const students = State.students.filter(u => String(u.role || "Student").toLowerCase().includes("student"));
      const marks = students.map(s => getPercentage(s)).filter(v => Number.isFinite(v));
      
      let highRiskCount = 0;
      let readyCount = 0;

      students.forEach(s => {
        const pred = State.predictionsByUser.get(s.uid);
        if (!pred) return;
        if (String(pred.risk_level || "").toUpperCase() === "HIGH") highRiskCount++;
        if (String(pred.placement_readiness || "").toUpperCase() === "READY") readyCount++;
      });

      UI.kStudents.textContent = students.length;
      UI.kPercent.textContent = formatPercent(getAverage(marks));
      UI.kRisk.textContent = highRiskCount;
      UI.kReady.textContent = readyCount;
      
      UI.kStudentsSub.textContent = `${students.length} student profiles loaded`;
      UI.kPercentSub.textContent = `${marks.length} profiles have marks data`;
      UI.kRiskSub.textContent = `${highRiskCount} flagged for intervention`;
      UI.kReadySub.textContent = `${readyCount} marked as Ready`;
    }

    function renderTable() {
      const query = UI.search.value.trim().toLowerCase();
      const riskFilter = UI.riskFilter.value;
      const readyFilter = UI.readinessFilter.value;

      const filtered = State.students.filter(u => {
        const pred = State.predictionsByUser.get(u.uid);
        const uRisk = String(pred?.risk_level || "").toLowerCase();
        const uReady = String(pred?.placement_readiness || "").toLowerCase();
        
        const searchBlob = `${u.uid} ${u.name || ""} ${u.email || ""}`.toLowerCase();
        
        if (query && !searchBlob.includes(query)) return false;
        if (riskFilter !== "all" && uRisk !== riskFilter) return false;
        if (readyFilter !== "all" && !uReady.includes(readyFilter)) return false;
        return true;
      });

      UI.table.innerHTML = "";
      
      if (filtered.length === 0) {
        UI.table.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No students match current filters.</td></tr>`;
        return;
      }

      filtered.forEach(u => {
        const pred = State.predictionsByUser.get(u.uid);
        const risk = String(pred?.risk_level || "--").toUpperCase();
        const readiness = String(pred?.placement_readiness || "--").toUpperCase();
        const pct = getPercentage(u);

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <div class="fw-bold text-dark">${sanitize(u.name || "Unknown")}</div>
            <div class="text-xs text-muted">${sanitize(u.email || u.uid)}</div>
          </td>
          <td><span class="badge bg-light text-dark border">${sanitize(u.role || "Student")}</span></td>
          <td class="fw-bold">${formatPercent(pct)}</td>
          <td><span class="badge-status ${getRiskClass(risk)}">${sanitize(risk)}</span></td>
          <td><span class="badge-status ${getReadinessClass(readiness)}">${sanitize(readiness)}</span></td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-primary view-btn" data-id="${u.uid}">View</button>
          </td>
        `;
        UI.table.appendChild(tr);
      });
    }

    function renderDetail() {
      if (!State.selected) {
        UI.selectedUid.textContent = "Select a student";
        UI.detail.innerHTML = `
           <div class="empty-state">
             <i class="bi bi-cursor text-muted fs-3 d-block mb-2"></i>
             Click a "View" button in the table to see detailed analytics here.
           </div>`;
        UI.note.value = "";
        UI.detailRole.value = "Student";
        UI.detailRole.disabled = true;
        UI.saveRole.disabled = true;
        return;
      }

      const u = State.selected;
      const p = State.predictionsByUser.get(u.uid);
      const marks = normalizeMarks(u);
      const avgP = getPercentage(u);

      const tracker = u.placement_tracker && typeof u.placement_tracker === 'object' ? u.placement_tracker : {};
      const tasks = Array.isArray(tracker.tasks) ? tracker.tasks : [];
      const doneCount = tasks.filter(t => t.done).length;
      const progress = tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0;
      const appCount = Array.isArray(tracker.applications) ? tracker.applications.length : 0;

      UI.selectedUid.textContent = u.uid;
      UI.note.value = u.hod_note || "";
      UI.detailRole.value = u.role || "Student";
      UI.detailRole.disabled = false;
      UI.saveRole.disabled = false;

      UI.detail.innerHTML = `
        <div class="mb-3">
          <h4 class="h6 fw-bold mb-0">${sanitize(u.name)}</h4>
          <span class="text-xs text-muted">${sanitize(u.email)}</span>
        </div>

        <div class="row g-2 mb-3">
          <div class="col-6">
            <div class="p-2 bg-light rounded border">
              <div class="text-xs text-muted text-uppercase">Agg. Score</div>
              <div class="fw-bold fs-5">${formatPercent(avgP)}</div>
            </div>
          </div>
          <div class="col-6">
            <div class="p-2 bg-light rounded border">
               <div class="text-xs text-muted text-uppercase">Predicted</div>
               <div class="fw-bold fs-5">${p?.predicted_score ? Number(p.predicted_score).toFixed(1) : "--"}</div>
            </div>
          </div>
        </div>

        <div class="detail-row">
          <span class="text-sm text-muted">Risk Assessment</span>
          <span class="badge-status ${getRiskClass(p?.risk_level)}">${sanitize(p?.risk_level || "N/A")}</span>
        </div>
        <div class="detail-row">
          <span class="text-sm text-muted">Readiness</span>
          <span class="badge-status ${getReadinessClass(p?.placement_readiness)}">${sanitize(p?.placement_readiness || "N/A")}</span>
        </div>

        <div class="mt-3">
           <div class="d-flex justify-content-between text-sm mb-1">
             <span>Placement Tasks (${doneCount}/${tasks.length})</span>
             <span class="fw-bold">${progress}%</span>
           </div>
           <div class="progress-track"><div class="progress-fill" style="width: ${progress}%"></div></div>
           <div class="text-xs text-muted mt-1 text-end">${appCount} Applications Submitted</div>
        </div>

        <div class="mt-3">
          <div class="text-xs fw-bold text-uppercase text-muted mb-2">Academic Breakdown</div>
          ${marks.length ? 
            marks.slice(0, 5).map(m => `
              <div class="d-flex justify-content-between text-sm border-bottom py-1">
                <span>${sanitize(m.subject)}</span>
                <span class="fw-bold">${m.mark}</span>
              </div>
            `).join('') 
            : '<div class="text-xs text-muted fst-italic">No subject marks available</div>'}
        </div>
      `;
    }

    function renderCourses() {
      UI.courseList.innerHTML = "";
      if (!State.courses.length) {
        UI.courseList.innerHTML = '<div class="text-center text-muted py-3 text-sm">No courses added.</div>';
        return;
      }
      
      State.courses.forEach(c => {
        const div = document.createElement('div');
        div.className = 'course-item';
        div.innerHTML = `
          <div class="d-flex justify-content-between align-items-start">
            <div>
               <div class="fw-bold text-sm text-primary">${sanitize(c.topic || c.videoTopic || "Untitled")}</div>
               <div class="text-xs text-muted">${sanitize(c.subject)} • ${sanitize(c.channel)}</div>
            </div>
            <button class="btn btn-link text-danger p-0 delete-course" data-id="${c.id}"><i class="bi bi-x-circle"></i></button>
          </div>
          <a href="${sanitize(c.link || c.videoLink)}" target="_blank" class="text-xs text-decoration-none text-muted mt-1 d-block text-truncate">
            <i class="bi bi-link-45deg"></i> Open Resource
          </a>
        `;
        UI.courseList.appendChild(div);
      });
    }


    async function loadData() {
      UI.refresh.innerHTML = '<i class="bi bi-arrow-clockwise me-1 spinner-border spinner-border-sm"></i> Syncing...';
      UI.status.textContent = "Syncing Data...";
      
      try {
        const [usersSnap, predSnap, coursesSnap] = await Promise.all([
          // Fetch only student profiles from backend store.

          getDocs(query(collection(db, "users"), where("role", "==", "Student"))),
          
          getDocs(collection(db, "predictions")),
          getDocs(collection(db, "courses"))
        ]);

        const users = [];
        usersSnap.forEach(d => users.push({ uid: d.id, ...d.data() }));
        State.students = users.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));

        const pMap = new Map();
        predSnap.forEach(d => {
          const data = d.data();
          const uid = data.user_id;
          if (!uid) return;
          const existing = pMap.get(uid);
          const currentMs = data.created_at?.toMillis ? data.created_at.toMillis() : 0;
          const existMs = existing?.created_at?.toMillis ? existing.created_at.toMillis() : -1;
          
          if (!existing || currentMs > existMs) {
            pMap.set(uid, data);
          }
        });
        State.predictionsByUser = pMap;

        const courses = [];
        coursesSnap.forEach(d => courses.push({ id: d.id, ...d.data() }));
        State.courses = courses;

        calculateKPIs();
        renderTable();
        renderDetail(); 
        renderCourses();
        
        UI.status.textContent = `Last synced: ${new Date().toLocaleTimeString()}`;
        UI.status.className = "badge bg-light text-secondary border";
      } catch (e) {
        console.error(e);
        UI.status.textContent = "Sync Error";
        UI.status.className = "badge bg-danger text-white";
        alert("Failed to load data. Check console.");
      } finally {
        UI.refresh.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i> Sync';
      }
    }

    async function handleSaveNote() {
      if (!State.selected) return;
      const btn = UI.saveNote;
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Saving...";

      try {
        const txt = UI.note.value.trim();
        await setDoc(doc(db, "users", State.selected.uid), {
          hod_note: txt,
          hod_note_updated_at: serverTimestamp()
        }, { merge: true });
        
        State.selected.hod_note = txt;
        btn.textContent = "Saved Successfully!";
        setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
      } catch (e) {
        console.error(e);
        btn.textContent = "Error Saving";
        setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
      }
    }

    async function handleAddCourse() {
      const topic = UI.courseTopic.value.trim();
      const link = UI.courseLink.value.trim();
      
      if (!topic || !link) {
        alert("Topic and Link are required.");
        return;
      }
      
      UI.addCourse.disabled = true;
      UI.addCourse.textContent = "Adding...";
      
      try {
        await addDoc(collection(db, "courses"), {
          topic, 
          link,
          subject: UI.courseSubject.value.trim(),
          channel: UI.courseChannel.value.trim(),
          createdAt: serverTimestamp()
        });

        UI.courseTopic.value = "";
        UI.courseLink.value = "";
        UI.courseSubject.value = "";
        UI.courseChannel.value = "";

        const snap = await getDocs(collection(db, "courses"));
        const courses = [];
        snap.forEach(d => courses.push({ id: d.id, ...d.data() }));
        State.courses = courses;
        renderCourses();
      } catch (e) {
        console.error(e);
        alert("Failed to add course");
      } finally {
        UI.addCourse.disabled = false;
        UI.addCourse.innerHTML = '<i class="bi bi-plus-lg"></i> Add Resource';
      }
    }

    function exportCSV() {
      const headers = ["UID", "Name", "Email", "Role", "Avg %", "Risk Level", "Readiness", "Tasks Completed", "Total Tasks", "Applications"];
      const rows = [headers.join(",")];
      
      State.students.forEach(u => {
        const p = State.predictionsByUser.get(u.uid) || {};
        const tr = u.placement_tracker || {};
        const tasks = Array.isArray(tr.tasks) ? tr.tasks : [];
        
        const row = [
          u.uid,
          u.name,
          u.email,
          u.role,
          formatPercent(getPercentage(u)),
          p.risk_level,
          p.placement_readiness,
          tasks.filter(t=>t.done).length,
          tasks.length,
          Array.isArray(tr.applications) ? tr.applications.length : 0
        ].map(f => `"${String(f || "").replace(/"/g, '""')}"`).join(",");
        
        rows.push(row);
      });
      
      const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hod_report_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }

    function bindEvents() {
      UI.refresh.addEventListener("click", loadData);
      UI.saveNote.addEventListener("click", handleSaveNote);
      UI.addCourse.addEventListener("click", handleAddCourse);
      UI.exportCsv.addEventListener("click", exportCSV);
      UI.logout.addEventListener("click", async () => {
        try {
          await signOut(auth);
        } finally {
          window.location.href = "../login.html";
        }
      });
      
      UI.search.addEventListener("input", renderTable);
      UI.riskFilter.addEventListener("change", renderTable);
      UI.readinessFilter.addEventListener("change", renderTable);
      UI.clearFilter.addEventListener("click", () => {
        UI.search.value = "";
        UI.riskFilter.value = "all";
        UI.readinessFilter.value = "all";
        renderTable();
      });

      UI.table.addEventListener("click", (e) => {
        const btn = e.target.closest(".view-btn");
        if (btn) {
          const uid = btn.dataset.id;
          State.selected = State.students.find(s => s.uid === uid);
          renderDetail();
        }
      });

      UI.courseList.addEventListener("click", async (e) => {
        const btn = e.target.closest(".delete-course");
        if (btn && confirm("Delete this resource?")) {
           try {
             await deleteDoc(doc(db, "courses", btn.dataset.id));
             State.courses = State.courses.filter(c => c.id !== btn.dataset.id);
             renderCourses();
           } catch(err) { console.error(err); alert("Delete failed"); }
        }
      });

      UI.saveRole.addEventListener("click", async () => {
        if (!State.selected) return;
        const newRole = UI.detailRole.value;
        try {
          await setDoc(doc(db,"users", State.selected.uid), { role: newRole }, { merge: true });
          State.selected.role = newRole;
          renderTable();
          alert("Role updated.");
        } catch(e) { alert("Failed to update role"); }
      });
    }

    bindEvents();
    
    onAuthStateChanged(auth, async (user) => {
      if (!user) {
        window.location.href = "../login.html";
        return;
      }
      const snap = await getDoc(doc(db, "users", user.uid));
      const role = String(snap.data()?.role || "").toLowerCase();
      
      if (role.includes("admin") || role.includes("hod")) {
        State.me = { uid: user.uid, ...snap.data() };
        loadData();
      } else {
        alert("Access Denied: HOD privileges required.");
        await signOut(auth);
        window.location.href = "../login.html";
      }
    });

  
