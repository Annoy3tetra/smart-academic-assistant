        if (window.top === window.self) {
            window.location.replace("../index.html");
        }

        import { getAuth, onAuthStateChanged } from "../../lib/auth-store.js";
        import { getDataStore, collection, getDocs, query, where, doc, getDoc, setDoc, serverTimestamp } from "../../lib/data-store.js";

        const auth = getAuth();
        const db = getDataStore();
        const marksEditor = document.getElementById("marks-editor");
        const marksEmptyState = document.getElementById("marks-empty-state");
        const marksStatus = document.getElementById("marks-status");
        const markRowTemplate = document.getElementById("mark-row-template");
        const learningList = document.getElementById("learning-list");
        const learningEmptyState = document.getElementById("learning-empty-state");
        const weakSubjectsChip = document.getElementById("weak-subjects-chip");
        const recommendationModelLabel = document.getElementById("recommendation-model-label");
        const API_BASES = [
            window.localStorage.getItem("apiBaseUrl"),
            "http://127.0.0.1:8000",
            "http://localhost:8000"
        ].filter(Boolean);
        let currentUserId = null;

        function setGreeting(user, userData) {
            const fallbackName = user?.email ? user.email.split("@")[0] : "Student";
            const displayName = String(userData?.name || user?.displayName || fallbackName || "Student").trim();
            document.getElementById("user-greeting").textContent = `Hello, ${displayName}!`;
        }

        function setMarksStatus(message, type = "muted") {
            marksStatus.className = "small mt-2";
            if (type === "error") marksStatus.classList.add("text-danger");
            else if (type === "success") marksStatus.classList.add("text-success");
            else marksStatus.classList.add("text-muted");
            marksStatus.textContent = message;
        }

        function setLearningStatus(message, model = "--") {
            learningEmptyState.textContent = message;
            learningEmptyState.classList.remove("d-none");
            recommendationModelLabel.textContent = `Model: ${model}`;
            weakSubjectsChip.classList.add("d-none");
            weakSubjectsChip.textContent = "";
            learningList.innerHTML = "";
        }

        function getLearningIcon(subject) {
            const value = String(subject || "").toLowerCase();
            if (value.includes("python") || value.includes("program")) return "bi-filetype-py text-primary";
            if (value.includes("math") || value.includes("algebra")) return "bi-calculator text-success";
            if (value.includes("dsa") || value.includes("algorithm")) return "bi-diagram-3 text-danger";
            if (value.includes("network")) return "bi-diagram-2 text-info";
            return "bi-journal-code text-secondary";
        }

        function getPriorityBadgeClass(priority) {
            if (priority === "High") return "bg-danger-subtle text-danger";
            if (priority === "Medium") return "bg-warning-subtle text-warning";
            return "bg-success-subtle text-success";
        }

        function renderLearningRecommendations(data) {
            const recommendations = Array.isArray(data?.recommendations) ? data.recommendations : [];
            if (!recommendations.length) {
                setLearningStatus("No recommendations returned. Update marks and try again.", data?.model_used || "--");
                return;
            }

            recommendationModelLabel.textContent = `Model: ${data?.model_used || "--"}`;
            learningEmptyState.classList.add("d-none");
            learningList.innerHTML = "";

            const weakSubjects = Array.isArray(data?.weak_subjects) ? data.weak_subjects.filter(Boolean) : [];
            if (weakSubjects.length) {
                weakSubjectsChip.classList.remove("d-none");
                weakSubjectsChip.textContent = `Weak subjects: ${weakSubjects.join(", ")}`;
            } else {
                weakSubjectsChip.classList.add("d-none");
                weakSubjectsChip.textContent = "";
            }

            recommendations.forEach((item) => {
                const wrapper = document.createElement("div");
                wrapper.className = "d-flex align-items-center p-3 rounded-3 bg-light";
                const safeUrl = item.course_url ? String(item.course_url) : "";
                const actionHtml = safeUrl
                    ? `<a class="btn btn-sm btn-dark rounded-pill px-3" href="${safeUrl}" target="_blank" rel="noopener noreferrer">Start</a>`
                    : `<button class="btn btn-sm btn-secondary rounded-pill px-3" disabled>Start</button>`;
                wrapper.innerHTML = `
                    <div class="bg-white p-2 rounded-3 shadow-sm me-3 fs-4"><i class="bi ${getLearningIcon(item.focus_subject)}"></i></div>
                    <div class="flex-grow-1">
                        <h6 class="fw-bold m-0">${item.title}</h6>
                        <small class="text-muted d-block">${item.reason}</small>
                        <small class="text-muted">Focus: ${item.focus_subject} | Provider: ${item.provider || "--"} | Level: ${item.level} | ${item.estimated_hours} hrs</small>
                    </div>
                    ${actionHtml}
                    <span class="badge rounded-pill ${getPriorityBadgeClass(item.priority)}">${item.priority}</span>
                `;
                learningList.appendChild(wrapper);
            });
        }

        function normalizeSubjectMarks(userData) {
            const raw = userData?.subject_marks ?? userData?.subjectMarks ?? userData?.marks;
            if (!raw) return [];

            if (Array.isArray(raw)) {
                return raw.map((entry, index) => {
                    if (typeof entry === "number" || typeof entry === "string") {
                        const parsed = Number(entry);
                        return { subject: `Subject ${index + 1}`, mark: Number.isFinite(parsed) ? parsed : "" };
                    }

                    if (entry && typeof entry === "object") {
                        const subject = String(entry.subject ?? entry.name ?? `Subject ${index + 1}`).trim();
                        const parsed = Number(entry.mark ?? entry.marks ?? entry.score);
                        return { subject, mark: Number.isFinite(parsed) ? parsed : "" };
                    }

                    return { subject: `Subject ${index + 1}`, mark: "" };
                });
            }

            if (typeof raw === "object") {
                return Object.entries(raw).map(([subject, value]) => {
                    const parsed = Number(value);
                    return { subject: String(subject), mark: Number.isFinite(parsed) ? parsed : "" };
                });
            }

            return [];
        }

        function renderCurrentPercentage(subjectMarks) {
            const percentageValue = document.getElementById("current-percentage-value");
            const percentageNote = document.getElementById("current-percentage-note");
            const validMarks = (subjectMarks || [])
                .map((item) => Number(item?.mark))
                .filter((value) => Number.isFinite(value));

            if (!validMarks.length) {
                percentageValue.textContent = "--";
                percentageNote.textContent = "Add subject marks to view percentage";
                return;
            }

            const average = validMarks.reduce((sum, value) => sum + value, 0) / validMarks.length;
            percentageValue.textContent = `${average.toFixed(1)}%`;
            percentageNote.textContent = `Based on ${validMarks.length} subject${validMarks.length > 1 ? "s" : ""}`;
        }

        function updateMarksEmptyState() {
            marksEmptyState.classList.toggle("d-none", marksEditor.children.length > 0);
        }

        function addMarkRow(subject = "", mark = "") {
            const row = markRowTemplate.content.firstElementChild.cloneNode(true);
            row.querySelector(".subject-name").value = subject;
            row.querySelector(".subject-score").value = mark === "" ? "" : Number(mark);
            marksEditor.appendChild(row);
            updateMarksEmptyState();
        }

        function renderMarksEditor(subjectMarks) {
            marksEditor.innerHTML = "";
            if (!subjectMarks.length) {
                updateMarksEmptyState();
                setMarksStatus("", "muted");
                return;
            }

            subjectMarks.forEach((item) => addMarkRow(item.subject, item.mark));
            setMarksStatus("", "muted");
        }

        function collectMarksPayload() {
            const rows = Array.from(marksEditor.querySelectorAll(".mark-row"));
            const payload = {};

            rows.forEach((row) => {
                const subject = row.querySelector(".subject-name").value.trim();
                const scoreValue = row.querySelector(".subject-score").value.trim();

                if (!subject && !scoreValue) return;
                if (!subject || !scoreValue) throw new Error("Both subject name and marks are required for each entry.");

                const score = Number(scoreValue);
                if (!Number.isFinite(score) || score < 0 || score > 100) {
                    throw new Error(`Invalid marks for ${subject}. Marks 0 se 100 ke beech hone chahiye.`);
                }

                payload[subject] = Number(score.toFixed(1));
            });

            return payload;
        }

        async function requestCourseRecommendations(subjects) {
            let lastError = null;

            for (const base of API_BASES) {
                try {
                    const response = await fetch(`${base}/students/recommend-courses`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            subjects,
                            top_n: 4
                        })
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(errorText || `Request failed with status ${response.status}`);
                    }

                    return await response.json();
                } catch (error) {
                    lastError = error;
                }
            }

            throw lastError || new Error("Recommendation service unavailable");
        }

        async function loadLearningRecommendations(subjectMarks) {
            const subjects = (subjectMarks || [])
                .filter((item) => item?.subject && Number.isFinite(Number(item?.mark)))
                .map((item) => ({ name: item.subject, score: Number(item.mark) }));

            if (!subjects.length) {
                setLearningStatus("Add your subject marks to get AI course recommendations.", "--");
                return;
            }

            setLearningStatus("Generating personalized recommendations...", "loading");
            try {
                const data = await requestCourseRecommendations(subjects);
                renderLearningRecommendations(data);
            } catch (error) {
                console.error("Failed to load course recommendations:", error);
                setLearningStatus("Recommendations unavailable right now. Try again after saving marks.", "error");
            }
        }

        async function saveSubjectMarks() {
            if (!currentUserId) {
                setMarksStatus("Couldn't Find User Session. Try logging again.", "error");
                return;
            }

            try {
                const subjectMarks = collectMarksPayload();
                await setDoc(doc(db, "users", currentUserId), {
                    subject_marks: subjectMarks,
                    marks_updated_at: serverTimestamp()
                }, { merge: true });

                const normalized = normalizeSubjectMarks({ subject_marks: subjectMarks });
                renderMarksEditor(normalized);
                renderCurrentPercentage(normalized);
                await loadLearningRecommendations(normalized);
                setMarksStatus("Marks successfully save ho gaye.", "success");
            } catch (error) {
                console.error("Failed to save marks:", error);
                setMarksStatus(error.message || "Couldn't save the Marks", "error");
            }
        }

        async function loadUserMarksAndProfile(user) {
            const snap = await getDoc(doc(db, "users", user.uid));
            const userData = snap.exists() ? snap.data() : {};
            setGreeting(user, userData);
            const normalized = normalizeSubjectMarks(userData);
            renderMarksEditor(normalized);
            renderCurrentPercentage(normalized);
            await loadLearningRecommendations(normalized);
        }

        function normalizeRiskLevel(riskLevel) {
            const normalized = String(riskLevel || "")
                .trim()
                .toUpperCase()
                .replace(/\s+/g, " ");
            return normalized;
        }

        function inferRiskFromScore(score) {
            if (!Number.isFinite(score)) return "";
            if (score >= 80) return "LOW";
            if (score >= 60) return "BALANCED";
            if (score >= 40) return "MEDIUM";
            if (score >= 20) return "HIGH";
            return "VERY HIGH";
        }

        function applyRiskBadge(riskLevel) {
            const riskBadge = document.getElementById("risk-level-badge");
            const normalizedRisk = normalizeRiskLevel(riskLevel);
            riskBadge.textContent = `Risk: ${normalizedRisk || "--"}`;
            riskBadge.classList.remove(
                "text-danger",
                "text-warning",
                "text-success",
                "text-high",
                "text-medium",
                "text-low",
                "text-balanced",
                "text-veryhigh",
                "text-white"
            );

            if (normalizedRisk === "HIGH") {
                riskBadge.classList.add("text-high");
            } else if (normalizedRisk === "MEDIUM") {
                riskBadge.classList.add("text-medium");
            } else if (normalizedRisk === "LOW") {
                riskBadge.classList.add("text-low");
            } else if (normalizedRisk === "BALANCED") {
                riskBadge.classList.add("text-balanced");
            } else if (normalizedRisk === "VERY HIGH") {
                riskBadge.classList.add("text-veryhigh");
            } else {
                riskBadge.classList.add("text-white");
            }
        }

        function applyPredictionCardGradient(riskLevel) {
            const predictionCard = document.getElementById("prediction-card");
            if (!predictionCard) return;
            const normalizedRisk = normalizeRiskLevel(riskLevel);

            predictionCard.classList.remove(
                "gradient-card-low",
                "gradient-card-balanced",
                "gradient-card-medium",
                "gradient-card-high",
                "gradient-card-very-high"
            );

            if (normalizedRisk === "LOW") {
                predictionCard.classList.add("gradient-card-low");
            } else if (normalizedRisk === "BALANCED") {
                predictionCard.classList.add("gradient-card-balanced");
            } else if (normalizedRisk === "MEDIUM") {
                predictionCard.classList.add("gradient-card-medium");
            } else if (normalizedRisk === "HIGH") {
                predictionCard.classList.add("gradient-card-high");
            } else if (normalizedRisk === "VERY HIGH") {
                predictionCard.classList.add("gradient-card-very-high");
            } else {
                predictionCard.classList.add("gradient-card-low");
            }
        }

        function renderPrediction(docData) {
            const predictedScore = document.getElementById("predicted-score");
            if (!predictedScore) return;

            const score = extractPredictedScore(docData);
            const resolvedRisk = normalizeRiskLevel(
                docData?.risk_level ?? docData?.riskLevel
            ) || inferRiskFromScore(score);

            predictedScore.textContent = Number.isFinite(score) ? `${score.toFixed(1)}%` : "No prediction yet";
            predictedScore.classList.add("text-dark");

            applyRiskBadge(resolvedRisk);
            applyPredictionCardGradient(resolvedRisk);
        }

        function renderPeerComparison(myScore, peerAverage, peerCount) {
            const peerAverageBadge = document.getElementById("peer-average-badge");
            const scoreDiffBadge = document.getElementById("score-diff-badge");
            if (!peerAverageBadge || !scoreDiffBadge) return;

            peerAverageBadge.className = "badge rounded-pill px-3 comparison-chip";
            scoreDiffBadge.className = "badge rounded-pill px-3 comparison-chip";

            if (!Number.isFinite(peerAverage)) {
                peerAverageBadge.textContent = "Peers Avg: --";
                scoreDiffBadge.textContent = "Diff: --";
                return;
            }

            const totalPeers = Number.isFinite(peerCount) ? peerCount : 0;
            peerAverageBadge.textContent = `Peers Avg: ${peerAverage.toFixed(1)}% (${totalPeers})`;

            if (!Number.isFinite(myScore)) {
                scoreDiffBadge.textContent = "Diff: --";
                return;
            }

            const diff = myScore - peerAverage;
            const sign = diff > 0 ? "+" : "";
            scoreDiffBadge.textContent = `Diff: ${sign}${diff.toFixed(1)}%`;

            if (diff > 0) {
                scoreDiffBadge.classList.add("comparison-chip-positive");
            } else if (diff < 0) {
                scoreDiffBadge.classList.add("comparison-chip-negative");
            }
        }

        function parseNumeric(value) {
            if (typeof value === "number") return Number.isFinite(value) ? value : null;
            if (typeof value === "string") {
                const cleaned = value.trim();
                const direct = Number(cleaned);
                if (Number.isFinite(direct)) return direct;
                const match = cleaned.match(/-?\d+(\.\d+)?/);
                if (match) {
                    const parsed = Number(match[0]);
                    return Number.isFinite(parsed) ? parsed : null;
                }
            }
            return null;
        }

        function extractPredictedScore(data) {
            const candidates = [
                data?.predicted_score,
                data?.predictedScore,
                data?.latest_prediction?.predicted_score
            ];

            for (const value of candidates) {
                const parsed = parseNumeric(value);
                if (Number.isFinite(parsed)) return parsed;
            }

            return null;
        }

        async function getLatestPredictionFromPredictionsCollection(uid) {
            try {
                const pickLatest = (snapshot) => {
                    let latest = null;
                    let latestMs = -1;

                    snapshot.forEach((docSnap) => {
                        const data = docSnap.data() || {};
                        const score = extractPredictedScore(data);
                        if (!Number.isFinite(score)) return;

                        const createdAtMs = data?.created_at?.toMillis ? data.created_at.toMillis() : 0;
                        if (!latest || createdAtMs >= latestMs) {
                            latest = data;
                            latestMs = createdAtMs;
                        }
                    });

                    return latest;
                };

                const predQuery = query(collection(db, "predictions"), where("user_id", "==", uid));
                let snapshot = await getDocs(predQuery);
                let latest = snapshot.empty ? null : pickLatest(snapshot);

                if (!latest) {
                    snapshot = await getDocs(collection(db, "predictions"));
                    const fallbackDocs = [];
                    snapshot.forEach((docSnap) => {
                        const data = docSnap.data() || {};
                        const ownerId = String(
                            data?.user_id ?? data?.uid ?? data?.userId ?? data?.student_uid ?? ""
                        ).trim();
                        if (ownerId === uid) fallbackDocs.push(docSnap);
                    });

                    latest = pickLatest({
                        forEach: (callback) => fallbackDocs.forEach(callback)
                    });
                }

                if (!latest) return null;
                return {
                    predicted_score: extractPredictedScore(latest),
                    risk_level: latest?.risk_level ?? latest?.riskLevel
                };
            } catch (error) {
                console.warn("Predictions collection fallback unavailable:", error);
                return null;
            }
        }

        function getPredictionFromLocalCache(uid) {
            try {
                const raw = window.localStorage.getItem("studentLatestPrediction");
                if (!raw) return null;
                const parsed = JSON.parse(raw);
                if (!parsed || String(parsed.uid || "").trim() !== String(uid || "").trim()) return null;
                const score = extractPredictedScore(parsed);
                if (!Number.isFinite(score)) return null;
                return {
                    predicted_score: score,
                    risk_level: parsed.risk_level ?? parsed.riskLevel
                };
            } catch (error) {
                console.warn("Invalid cached prediction:", error);
                return null;
            }
        }

        async function loadLatestPrediction(uid) {
            let currentPrediction = {
                predicted_score: null,
                risk_level: null
            };

            const cachedPrediction = getPredictionFromLocalCache(uid);
            if (cachedPrediction) currentPrediction = cachedPrediction;

            try {
                const currentUserDoc = await getDoc(doc(db, "users", uid));
                const currentUserData = currentUserDoc.exists() ? currentUserDoc.data() : null;
                const scoreFromUser = extractPredictedScore(currentUserData);
                if (Number.isFinite(scoreFromUser)) {
                    currentPrediction = {
                        predicted_score: scoreFromUser,
                        risk_level: currentUserData?.risk_level ?? currentUserData?.riskLevel
                    };
                }
            } catch (error) {
                console.warn("Could not load prediction from users doc:", error);
            }

            if (!Number.isFinite(currentPrediction.predicted_score)) {
                const fallbackPrediction = await getLatestPredictionFromPredictionsCollection(uid);
                if (fallbackPrediction) currentPrediction = fallbackPrediction;
            }

            const normalizedCurrentScore = extractPredictedScore(currentPrediction);
            renderPrediction(currentPrediction);
            renderPeerComparison(Number(normalizedCurrentScore), null, 0);

            let snapshot = null;
            try {
                snapshot = await getDocs(collection(db, "users"));
            } catch (error) {
                console.warn("Peer comparison unavailable:", error);
                return;
            }

            if (!snapshot || snapshot.empty) return;

            const peerScores = [];
            snapshot.forEach((docSnap) => {
                const userId = String(docSnap.id || "").trim();
                if (!userId || userId === uid) return;
                const predictedScore = extractPredictedScore(docSnap.data());
                if (Number.isFinite(predictedScore)) peerScores.push(predictedScore);
            });

            if (!peerScores.length) {
                renderPeerComparison(Number(normalizedCurrentScore), null, 0);
                return;
            }

            const peerAverage = peerScores.reduce((sum, value) => sum + value, 0) / peerScores.length;
            renderPeerComparison(Number(normalizedCurrentScore), peerAverage, peerScores.length);
        }

        onAuthStateChanged(auth, async (user) => {
            if (!user) {
                currentUserId = null;
                setGreeting(null, null);
                renderMarksEditor([]);
                renderCurrentPercentage([]);
                setLearningStatus("Login required for recommendations.", "--");
                renderPrediction(null);
                return;
            }

            try {
                currentUserId = user.uid;
                await Promise.all([
                    loadLatestPrediction(user.uid),
                    loadUserMarksAndProfile(user)
                ]);
            } catch (error) {
                console.error("Failed to load dashboard data:", error);
                renderPrediction(null);
                setMarksStatus("Could not load marks.", "error");
            }
        });

        document.getElementById("add-mark-row-btn").addEventListener("click", () => addMarkRow());
        document.getElementById("save-marks-btn").addEventListener("click", saveSubjectMarks);
        marksEditor.addEventListener("click", (event) => {
            const removeBtn = event.target.closest(".remove-mark-btn");
            if (!removeBtn) return;
            removeBtn.closest(".mark-row")?.remove();
            updateMarksEmptyState();
        });
    
