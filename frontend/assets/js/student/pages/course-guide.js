        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
        import { getFirestore, collection, getDocs } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

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

        const statusEl = document.getElementById("status");
        const gridEl = document.getElementById("courses-grid");
        const cardColors = ["color-1", "color-2", "color-3", "color-4", "color-5", "color-6"];
        const colorByClass = {
            "bg-coa": "linear-gradient(140deg, #7c3aed, #a855f7)",
            "bg-dsa": "linear-gradient(140deg, #0f766e, #14b8a6)",
            "bg-dbms": "linear-gradient(140deg, #1d4ed8, #3b82f6)",
            "bg-os": "linear-gradient(140deg, #be123c, #f43f5e)",
            "bg-python": "linear-gradient(140deg, #b45309, #f59e0b)"
        };

        function normalizeDoc(raw) {
            const topic = String(raw.videoTopic || raw.topic || raw.title || "").trim();
            const link = String(raw.videoLink || raw.link || raw.url || "").trim();
            const subject = String(raw.subject || raw.channel || "").trim();
            const icon = String(raw.icon || "bi-play-circle-fill").trim();
            const colorClass = String(raw.colorClass || "").trim();
            if (!topic || !link) return null;
            return { topic, link, subject, icon, colorClass };
        }

        function safeLink(url) {
            const candidate = /^https?:\/\//i.test(url) ? url : `https://${url}`;
            try {
                const parsed = new URL(candidate);
                if (parsed.protocol === "http:" || parsed.protocol === "https:") return parsed.href;
            } catch (error) {
                console.warn("Invalid link skipped:", error);
            }
            return null;
        }

        function renderCourses(courses) {
            gridEl.innerHTML = "";
            let rendered = 0;
            courses.forEach((course, index) => {
                const href = safeLink(course.link);
                if (!href) return;
                const col = document.createElement("div");
                col.className = "col-12 col-sm-6 col-lg-4";
                const colorClass = cardColors[index % cardColors.length];
                const card = document.createElement("article");
                card.className = `video-card ${colorClass}`;
                if (course.colorClass && colorByClass[course.colorClass]) {
                    card.style.background = colorByClass[course.colorClass];
                }

                const head = document.createElement("div");
                head.className = "video-head";
                const icon = document.createElement("i");
                icon.className = `bi ${course.icon || "bi-play-circle-fill"} video-icon`;
                const meta = document.createElement("div");
                if (course.subject) {
                    const subject = document.createElement("p");
                    subject.className = "video-subject";
                    subject.textContent = course.subject;
                    meta.appendChild(subject);
                }
                const topic = document.createElement("p");
                topic.className = "video-topic";
                topic.textContent = course.topic;
                meta.appendChild(topic);
                const link = document.createElement("a");
                link.className = "video-link";
                link.href = href;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = "Open Video";
                head.appendChild(icon);
                head.appendChild(meta);
                card.appendChild(head);
                card.appendChild(link);
                col.appendChild(card);
                gridEl.appendChild(col);
                rendered += 1;
            });
            return rendered;
        }

        async function loadCourses() {
            try {
                const snapshot = await getDocs(collection(db, "courses"));
                const courses = [];
                snapshot.forEach((docSnap) => {
                    const normalized = normalizeDoc(docSnap.data());
                    if (normalized) courses.push(normalized);
                });

                if (!courses.length) {
                    statusEl.textContent = "No course videos found in Firestore collection: courses";
                    return;
                }

                const rendered = renderCourses(courses);
                if (!rendered) {
                    statusEl.textContent = "Courses found, but no valid video links were available.";
                    statusEl.classList.remove("d-none");
                    return;
                }

                statusEl.classList.add("d-none");
            } catch (error) {
                console.error("Course fetch failed:", error);
                statusEl.textContent = "Failed to load courses from Firestore.";
                statusEl.classList.remove("d-none");
            }
        }

        onAuthStateChanged(auth, (user) => {
            if (!user) {
                statusEl.textContent = "Please login to view course videos.";
                return;
            }
            loadCourses();
        });
    
