// Client-side script for Math Solver

document.addEventListener("DOMContentLoaded", () => {
    const solveForm = document.getElementById("solveForm");
    const problemText = document.getElementById("problemText");
    const difficultySelect = document.getElementById("difficultySelect");
    const languageSelect = document.getElementById("languageSelect");
    const solveBtn = document.getElementById("solveBtn");
    const statusMessage = document.getElementById("statusMessage");

    const resultsSection = document.getElementById("resultsSection");
    const displayProblem = document.getElementById("displayProblem");
    const topicBadge = document.getElementById("topicBadge");
    const stepsList = document.getElementById("stepsList");
    const finalAnswer = document.getElementById("finalAnswer");
    const videosContainer = document.getElementById("videosContainer");

    // Form submit listener
    solveForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const textValue = problemText.value.trim();

        // Ensure user provided question text
        if (!textValue) {
            statusMessage.textContent = "Please enter a math question.";
            statusMessage.style.color = "#dc2626";
            return;
        }

        // Prepare JSON payload matching SolveRequest schema
        const payload = {
            question: textValue,
            difficulty: difficultySelect.value,
            language: languageSelect.value,
        };

        // Set loading state
        solveBtn.disabled = true;
        solveBtn.textContent = "Solving...";
        statusMessage.textContent = "Analyzing problem and generating solution...";
        statusMessage.style.color = "#4b5563";
        resultsSection.classList.add("hidden");

        try {
            const response = await fetch("/solve", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                const msg = errData && errData.message 
                    ? errData.message 
                    : `Server returned status ${response.status}`;
                throw new Error(msg);
            }

            const data = await response.json();

            // Populate Solution details
            displayProblem.textContent = data.problem;
            topicBadge.textContent = data.topic || "General Math";

            // Populate Steps
            stepsList.innerHTML = "";
            if (data.steps && data.steps.length > 0) {
                data.steps.forEach((step) => {
                    const li = document.createElement("li");
                    li.textContent = step;
                    stepsList.appendChild(li);
                });
            }

            // Populate Final Answer
            finalAnswer.textContent = data.final_answer;

            // Populate Recommended Videos
            videosContainer.innerHTML = "";
            if (data.videos && data.videos.length > 0) {
                data.videos.forEach((video) => {
                    const card = document.createElement("div");
                    card.className = "video-card";
                    card.innerHTML = `
                        <a href="${video.url}" target="_blank" rel="noopener noreferrer">
                            <img src="${video.thumbnail}" alt="${video.title}">
                            <div class="video-info">
                                <p class="video-title">${video.title}</p>
                            </div>
                        </a>
                    `;
                    videosContainer.appendChild(card);
                });
            } else {
                videosContainer.innerHTML = "<p class='help-text'>Video recommendations will be added in Day 4.</p>";
            }

            // Reveal results
            resultsSection.classList.remove("hidden");
            statusMessage.textContent = "";

            // Render LaTeX formulas using KaTeX if auto-render is loaded
            if (window.renderMathInElement) {
                window.renderMathInElement(resultsSection, {
                    delimiters: [
                        { left: "$$", right: "$$", display: true },
                        { left: "$", right: "$", display: false },
                        { left: "\\[", right: "\\]", display: true },
                        { left: "\\(", right: "\\)", display: false }
                    ],
                    throwOnError: false
                });
            }
        } catch (error) {
            console.error("Error solving problem:", error);
            statusMessage.textContent = error.message || "Failed to solve problem. Please try again.";
            statusMessage.style.color = "#dc2626";
        } finally {
            solveBtn.disabled = false;
            solveBtn.textContent = "Solve Problem";
        }
    });
});
