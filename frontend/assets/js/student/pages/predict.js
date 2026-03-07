        import { getAuth, onAuthStateChanged } from "../../lib/auth-store.js";
        import { getDataStore, collection, addDoc, serverTimestamp, doc, getDoc, setDoc } from "../../lib/data-store.js";
        import { getApiBases } from "../../lib/backend-client.js";

        const auth = getAuth();
        const db = getDataStore();

        const API_BASES = getApiBases();

        async function savePredictionToUserCollection(prediction, inputData) {
            const user = auth.currentUser;
            if (!user) throw new Error("User not logged in.");

            await setDoc(doc(db, "users", user.uid), {
                input_data: inputData,
                average_score: prediction.average_score ?? null,
                total_subjects: prediction.total_subjects ?? null,
                predicted_score: prediction.predicted_score,
                risk_level: prediction.risk_level,
                placement_readiness: prediction.placement_readiness ?? null,
                prediction_updated_at: serverTimestamp()
            }, { merge: true });

            try {
                await addDoc(collection(db, "predictions"), {
                    user_id: user.uid,
                    average_score: prediction.average_score ?? null,
                    total_subjects: prediction.total_subjects ?? null,
                    predicted_score: prediction.predicted_score,
                    risk_level: prediction.risk_level,
                    placement_readiness: prediction.placement_readiness ?? null,
                    input_data: inputData,
                    created_at: serverTimestamp()
                });
            } catch (error) {
                console.warn("Failed to save prediction history:", error);
            }

            try {
                window.localStorage.setItem("studentLatestPrediction", JSON.stringify({
                    uid: user.uid,
                    predicted_score: prediction.predicted_score,
                    risk_level: prediction.risk_level,
                    placement_readiness: prediction.placement_readiness ?? null,
                    updated_at: new Date().toISOString()
                }));
            } catch (error) {
                console.warn("Failed to cache latest prediction locally:", error);
            }
        }

        function normalizeUserSubjectMarks(userData) {
            const raw = userData?.subject_marks ?? userData?.subjectMarks ?? userData?.marks;
            if (!raw) return [];

            if (Array.isArray(raw)) {
                return raw.map((entry, index) => {
                    if (typeof entry === "number" || typeof entry === "string") {
                        const parsed = Number(entry);
                        return Number.isFinite(parsed) ? { subject: `Subject ${index + 1}`, mark: parsed } : null;
                    }
                    if (entry && typeof entry === "object") {
                        const subject = String(entry.subject ?? entry.name ?? `Subject ${index + 1}`).trim();
                        const parsed = Number(entry.mark ?? entry.marks ?? entry.score);
                        return Number.isFinite(parsed) ? { subject, mark: parsed } : null;
                    }
                    return null;
                }).filter((value) => value !== null);
            }

            if (typeof raw === "object") {
                return Object.entries(raw).map(([subject, value]) => {
                    const parsed = Number(value);
                    return Number.isFinite(parsed) ? { subject, mark: parsed } : null;
                }).filter((value) => value !== null);
            }

            return [];
        }

        async function saveMarksToUserCollection(subjectEntries, attendance, totalSubjects) {
            const user = auth.currentUser;
            if (!user) return;

            const subjectMarksObject = {};
            subjectEntries.forEach((entry, index) => {
                const subjectKey = (entry.subject || `Subject ${index + 1}`).trim();
                subjectMarksObject[subjectKey] = Number(entry.mark.toFixed(1));
            });

            await setDoc(doc(db, "users", user.uid), {
                subject_marks: subjectMarksObject,
                last_prediction_input: {
                    attendance: Number(attendance.toFixed(1)),
                    total_subjects: totalSubjects
                },
                marks_updated_at: serverTimestamp()
            }, { merge: true });
        }

        async function prefillInputsFromUserCollection(user) {
            const userDoc = await getDoc(doc(db, "users", user.uid));
            if (!userDoc.exists()) return;

            const userData = userDoc.data();
            const savedEntries = normalizeUserSubjectMarks(userData);
            if (!savedEntries.length) return;

            const totalSubjects = Math.min(Math.max(savedEntries.length, 4), 7);
            document.getElementById("totalSubjects").value = totalSubjects;
            buildSubjectInputs(totalSubjects, savedEntries);

            const subjectInputs = Array.from(document.querySelectorAll(".subject-name"));
            const markInputs = Array.from(document.querySelectorAll(".subject-mark"));
            subjectInputs.forEach((input, index) => {
                input.value = savedEntries[index]?.subject || "";
            });
            markInputs.forEach((input, index) => {
                const value = savedEntries[index]?.mark;
                input.value = Number.isFinite(value) ? value : "";
            });

            const savedAttendance = Number(userData?.last_prediction_input?.attendance);
            if (Number.isFinite(savedAttendance) && savedAttendance >= 0 && savedAttendance <= 100) {
                document.getElementById("attendance").value = savedAttendance;
            }
        }

        async function requestPrediction(payload) {
            let lastError = null;

            for (const base of API_BASES) {
                try {
                    const response = await fetch(`${base}/students/predict-direct`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
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

            throw lastError || new Error("Prediction service is unavailable");
        }

        async function handlePrediction(event) {
            event.preventDefault();

            const btn = document.querySelector(".btn-predict");
            const loader = document.getElementById("loader");
            const btnText = document.getElementById("btn-text");
            const resultCard = document.getElementById("result-card");

            btn.disabled = true;
            loader.classList.remove("d-none");
            btnText.textContent = "Consulting AI Model...";
            resultCard.style.display = "none";

            const attendance = parseFloat(document.getElementById("attendance").value);
            const totalSubjects = parseInt(document.getElementById("totalSubjects").value, 10);
            const subjectNameInputs = Array.from(document.querySelectorAll(".subject-name"));
            const markInputs = Array.from(document.querySelectorAll(".subject-mark"));
            const subjectNames = subjectNameInputs.map((input) => input.value.trim());
            const subjectMarks = markInputs.map((input) => parseFloat(input.value));

            try {
                if (
                    Number.isNaN(attendance) || Number.isNaN(totalSubjects) ||
                    attendance < 0 || attendance > 100 ||
                    totalSubjects < 4 || totalSubjects > 7 ||
                    subjectNames.length !== totalSubjects ||
                    subjectNames.some((name) => !name) ||
                    subjectMarks.length !== totalSubjects ||
                    subjectMarks.some((mark) => Number.isNaN(mark) || mark < 0 || mark > 100)
                ) {
                    throw new Error("Please enter valid values: attendance 0-100, subjects 4-7, subject name required, and each mark 0-100.");
                }

                const subjectEntries = subjectNames.map((subject, index) => ({ subject, mark: subjectMarks[index] }));

                const data = await requestPrediction({
                    subject_marks: subjectMarks,
                    attendance,
                });

                const averageScore = Number(data.average_score);
                const subjectCount = Number(data.total_subjects);

                await savePredictionToUserCollection(
                    {
                        ...data,
                        average_score: Number.isFinite(averageScore) ? averageScore : null,
                        total_subjects: Number.isFinite(subjectCount) ? subjectCount : totalSubjects
                    },
                    {
                        subjects: subjectNames,
                        subject_marks: subjectMarks,
                        attendance
                    }
                );
                await saveMarksToUserCollection(subjectEntries, attendance, totalSubjects);

                showResult(Number(data.predicted_score).toFixed(1));
            } catch (error) {
                console.error("Prediction Failed:", error);
                alert(error.message || "Something went wrong with the calculation.");
            } finally {
                btn.disabled = false;
                loader.classList.add("d-none");
                btnText.textContent = "Predict Future";
            }
        }

        function buildSubjectInputs(totalSubjects, presetEntries = []) {
            const container = document.getElementById("subjectMarksContainer");
            container.innerHTML = "";

            for (let i = 0; i < totalSubjects; i++) {
                const col = document.createElement("div");
                col.className = "col-12";

                const row = document.createElement("div");
                row.className = "row g-2";

                const subjectCol = document.createElement("div");
                subjectCol.className = "col-md-7";

                const subjectInput = document.createElement("input");
                subjectInput.type = "text";
                subjectInput.className = "form-control subject-name";
                subjectInput.placeholder = `Subject ${i + 1} name`;
                subjectInput.required = true;
                subjectInput.value = presetEntries[i]?.subject || "";

                subjectCol.appendChild(subjectInput);

                const marksCol = document.createElement("div");
                marksCol.className = "col-md-5";

                const input = document.createElement("input");
                input.type = "number";
                input.className = "form-control subject-mark";
                input.placeholder = `Subject ${i + 1} marks`;
                input.min = "0";
                input.max = "100";
                input.step = "0.1";
                input.required = true;
                input.value = Number.isFinite(presetEntries[i]?.mark) ? presetEntries[i].mark : "";

                marksCol.appendChild(input);
                row.appendChild(subjectCol);
                row.appendChild(marksCol);
                col.appendChild(row);
                container.appendChild(col);
            }
        }

        function setupSubjectInputs() {
            const totalSubjectsInput = document.getElementById("totalSubjects");

            const render = () => {
                const totalSubjects = parseInt(totalSubjectsInput.value, 10);
                if (!Number.isNaN(totalSubjects) && totalSubjects >= 4 && totalSubjects <= 7) {
                    buildSubjectInputs(totalSubjects);
                }
            };

            totalSubjectsInput.addEventListener("change", render);
            totalSubjectsInput.addEventListener("input", render);
            render();
        }

        setupSubjectInputs();
        onAuthStateChanged(auth, async (user) => {
            if (!user) return;
            try {
                await prefillInputsFromUserCollection(user);
            } catch (error) {
                console.error("Could not prefill marks from user collection:", error);
            }
        });
        window.handlePrediction = handlePrediction;

        function getScoreColor(score) {
            if (score >= 80) return "#16a34a";
            if (score >= 60) return "#2563eb";
            if (score >= 40) return "#f59e0b";
            return "#dc2626";
        }

        function showResult(percentage) {
            const resultCard = document.getElementById("result-card");
            const scoreVal = document.getElementById("scoreValue");
            const circle = document.getElementById("scoreCircle");
            const numericScore = Number(percentage);
            const score = Number.isFinite(numericScore) ? numericScore : 0;
            const accent = getScoreColor(score);

            resultCard.style.display = "block";
            resultCard.style.borderTop = `5px solid ${accent}`;

            let start = 0;
            let end = Math.min(Math.round(score), 100);

            if (end <= 0) {
                scoreVal.textContent = "0.0%";
                scoreVal.style.color = accent;
                circle.style.background = `conic-gradient(${accent} 0deg, #f0f0f0 0deg)`;
                return;
            }

            const duration = 1500;
            const stepTime = Math.max(10, Math.abs(Math.floor(duration / end)));

            const timer = setInterval(function () {
                start++;
                scoreVal.textContent = start + "%";
                scoreVal.style.color = accent;
                circle.style.background = `conic-gradient(${accent} ${start * 3.6}deg, #f0f0f0 0deg)`;

                if (start >= end) {
                    clearInterval(timer);
                    scoreVal.textContent = `${score.toFixed(1)}%`;
                }
            }, stepTime);
        }

    
