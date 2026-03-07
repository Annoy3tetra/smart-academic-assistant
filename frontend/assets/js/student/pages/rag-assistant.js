        import { getApiBases } from "../../lib/backend-client.js";

        const API_BASES = getApiBases();

        const queryInput = document.getElementById("query");
        const askBtn = document.getElementById("ask-btn");
        const askBtnText = document.getElementById("ask-btn-text");
        const askLoader = document.getElementById("ask-loader");
        const statusText = document.getElementById("status-text");
        const answerBox = document.getElementById("answer-box");

        function setLoading(loading) {
            askBtn.disabled = loading;
            askLoader.classList.toggle("d-none", !loading);
            askBtnText.textContent = loading ? "Thinking..." : "Ask RAG Model";
        }

        async function callRagEndpoint(payload) {
            let lastError = null;

            for (const base of API_BASES) {
                try {
                    const response = await fetch(`${base}/students/rag-query`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) {
                        const text = await response.text();
                        throw new Error(text || `Request failed with status ${response.status}`);
                    }

                    return await response.json();
                } catch (error) {
                    lastError = error;
                }
            }

            throw lastError || new Error("RAG endpoint unavailable");
        }

        async function askQuestion() {
            const query = queryInput.value.trim();
            if (query.length < 3) {
                statusText.textContent = "Enter at least 3 characters.";
                statusText.className = "text-danger";
                return;
            }

            setLoading(true);
            statusText.textContent = "Sending query to RAG model...";
            statusText.className = "text-muted";
            answerBox.textContent = "Generating answer...";
            answerBox.className = "text-muted";

            try {
                const data = await callRagEndpoint({ query });
                const answer = String(data?.answer || "").trim();
                answerBox.textContent = answer || "No answer returned.";
                answerBox.className = "text-dark";
                statusText.textContent = "Response generated successfully.";
                statusText.className = "text-success";
            } catch (error) {
                console.error("RAG request failed:", error);
                answerBox.textContent = "Could not fetch answer from RAG model.";
                answerBox.className = "text-danger";
                statusText.textContent = error.message || "Request failed.";
                statusText.className = "text-danger";
            } finally {
                setLoading(false);
            }
        }

        askBtn.addEventListener("click", askQuestion);
        queryInput.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                askQuestion();
            }
        });
    
