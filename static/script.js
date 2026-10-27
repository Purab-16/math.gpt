// Client-side script for math.gpt

// Image upload settings
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;       // Server limit (10 MB)
const MAX_IMAGE_DIMENSION = 2048;               // Longest side after resize
const SKIP_COMPRESSION_BYTES = 1024 * 1024;     // Small images are sent as they are
const JPEG_QUALITY = 0.85;
const ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

// Question settings
const MAX_QUESTION_LENGTH = 2000;
const PREVIEW_DELAY_MS = 150;

// KaTeX delimiters used everywhere on the page
const MATH_DELIMITERS = [
    { left: "$$", right: "$$", display: true },
    { left: "$", right: "$", display: false },
    { left: "\\[", right: "\\]", display: true },
    { left: "\\(", right: "\\)", display: false },
];

// Return true only for valid https:// URLs
function isSafeHttpsUrl(value) {
    try {
        return new URL(value).protocol === "https:";
    } catch {
        return false;
    }
}

// If the model forgot $...$ around LaTeX, wrap the whole text so KaTeX renders it.
// Text that already has delimiters or has no LaTeX is returned unchanged.
function ensureMathDelimiters(text) {
    if (!text) {
        return text;
    }
    const hasDelimiters = /\$|\\\(|\\\[/.test(text);
    const looksLikeLatex = /\\[a-zA-Z]+|[\^_]/.test(text);
    return !hasDelimiters && looksLikeLatex ? `\\(${text}\\)` : text;
}

// Render LaTeX inside an element, if KaTeX has finished loading
function renderMath(element) {
    if (window.renderMathInElement) {
        window.renderMathInElement(element, { delimiters: MATH_DELIMITERS, throwOnError: false });
    }
}

// Resize and convert an image to JPEG in the browser to make uploads smaller.
// Returns the original file if it is already small or if compression fails.
async function compressImage(file) {
    try {
        const bitmap = await createImageBitmap(file);
        const longestSide = Math.max(bitmap.width, bitmap.height);

        if (file.size <= SKIP_COMPRESSION_BYTES && longestSide <= MAX_IMAGE_DIMENSION) {
            bitmap.close();
            return file;
        }

        const scale = Math.min(1, MAX_IMAGE_DIMENSION / longestSide);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(bitmap.width * scale);
        canvas.height = Math.round(bitmap.height * scale);

        const context = canvas.getContext("2d");
        // White background so transparent PNGs do not turn black in JPEG
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        bitmap.close();

        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));

        // Keep the original if compression did not help
        if (!blob || blob.size >= file.size) {
            return file;
        }
        return blob;
    } catch (error) {
        console.warn("Image compression failed, sending original image.");
        return file;
    }
}

// Switch between light and dark mode and remember the choice
function setupThemeToggle() {
    const themeToggle = document.getElementById("themeToggle");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

    themeToggle.addEventListener("click", () => {
        const current = document.documentElement.dataset.theme || (systemDark.matches ? "dark" : "light");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        try {
            localStorage.setItem("theme", next);
        } catch (error) {
            // Storage blocked: the theme still changes for this visit
        }
    });
}

// ---------- History storage (this browser only) ----------

const HISTORY_KEY = "mathgpt.history.v1";
const MAX_HISTORY_ITEMS = 50;

// localStorage can be edited by anyone with access to the browser,
// so every saved entry is checked before it is used.
function isValidHistoryEntry(entry) {
    // Checked first because typeof null is also "object"
    if (typeof entry !== "object" || entry === null) {
        return false;
    }
    const result = entry.result;
    return (
        typeof entry.id === "string" &&
        typeof entry.savedAt === "number" &&
        typeof entry.question === "string" &&
        typeof entry.hadImage === "boolean" &&
        typeof entry.difficulty === "string" &&
        typeof entry.language === "string" &&
        typeof result === "object" &&
        result !== null &&
        typeof result.problem === "string" &&
        typeof result.final_answer === "string" &&
        typeof result.topic === "string" &&
        Array.isArray(result.steps) &&
        result.steps.every((step) => typeof step === "string") &&
        Array.isArray(result.videos)
    );
}

function loadHistory() {
    try {
        const items = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
        return Array.isArray(items) ? items.filter(isValidHistoryEntry).slice(0, MAX_HISTORY_ITEMS) : [];
    } catch (error) {
        return [];
    }
}

// Save the list. If the browser storage is full, drop the oldest items and try again.
function saveHistory(items) {
    let toSave = items.slice(0, MAX_HISTORY_ITEMS);
    while (toSave.length > 0) {
        try {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(toSave));
            return toSave;
        } catch (error) {
            toSave = toSave.slice(0, -1);
        }
    }
    try {
        localStorage.removeItem(HISTORY_KEY);
    } catch (error) {
        // Storage blocked: history only lasts for this visit
    }
    return toSave;
}

function makeHistoryId() {
    if (window.crypto && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// Add a solved question to the top of the list. The same question with the
// same options replaces the older copy instead of adding a duplicate.
// Photos are not saved, only a flag that the question had one.
function addToHistory(items, { question, hadImage, difficulty, language, result }) {
    const entry = {
        id: makeHistoryId(),
        savedAt: Date.now(),
        question,
        hadImage,
        difficulty,
        language,
        result: {
            problem: result.problem || "",
            steps: result.steps || [],
            final_answer: result.final_answer || "",
            topic: result.topic || "",
            videos: result.videos || [],
        },
    };

    const isSameQuestion = (item) =>
        !hadImage &&
        !item.hadImage &&
        item.question === question &&
        item.difficulty === difficulty &&
        item.language === language;

    return [entry, ...items.filter((item) => !isSameQuestion(item))].slice(0, MAX_HISTORY_ITEMS);
}

// This script is loaded at the end of <body>, so the page elements already exist.
// We set up right away instead of waiting for DOMContentLoaded, which also waits
// for the KaTeX CDN files. Otherwise a quick click could submit the form as a
// normal page reload with the question in the URL.
function initApp() {
    const solveForm = document.getElementById("solveForm");
    const problemText = document.getElementById("problemText");
    const charCount = document.getElementById("charCount");
    const symbolBar = document.getElementById("symbolBar");
    const mathPreview = document.getElementById("mathPreview");
    const mathPreviewContent = document.getElementById("mathPreviewContent");
    const solveBtn = document.getElementById("solveBtn");
    const solveBtnLabel = document.getElementById("solveBtnLabel");
    const solveSpinner = document.getElementById("solveSpinner");
    const statusMessage = document.getElementById("statusMessage");

    const imageInput = document.getElementById("imageInput");
    const dropzone = document.getElementById("dropzone");
    const imagePreviewBox = document.getElementById("imagePreviewBox");
    const imagePreview = document.getElementById("imagePreview");
    const removeImageBtn = document.getElementById("removeImageBtn");

    const sheet = document.getElementById("sheet");
    const emptyState = document.getElementById("emptyState");
    const loadingState = document.getElementById("loadingState");
    const resultsSection = document.getElementById("resultsSection");
    const displayProblem = document.getElementById("displayProblem");
    const topicBadge = document.getElementById("topicBadge");
    const stepsList = document.getElementById("stepsList");
    const finalAnswer = document.getElementById("finalAnswer");
    const copyAnswerBtn = document.getElementById("copyAnswerBtn");
    const videosContainer = document.getElementById("videosContainer");

    const historyPanel = document.getElementById("historyPanel");
    const historyCount = document.getElementById("historyCount");
    const historyEmpty = document.getElementById("historyEmpty");
    const historyList = document.getElementById("historyList");
    const clearHistoryBtn = document.getElementById("clearHistoryBtn");

    let selectedImage = null;
    let previewUrl = null;
    let previewTimer = null;
    let hasResult = false;
    let lastAnswer = "";
    let historyItems = loadHistory();
    let activeHistoryId = null;
    let clearConfirmTimer = null;

    const dateFormat = new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "short",
        hour: "numeric",
        minute: "2-digit",
    });

    setupThemeToggle();

    // History starts open on desktop and closed on phones, so it does not push the sheet down
    historyPanel.open = window.innerWidth >= 980;

    // ---------- Status and views ----------

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `status is-${type}`;
        statusMessage.hidden = !message;
    }

    // Show one of the three sheet states: "empty", "loading", or "results"
    function showView(view) {
        emptyState.hidden = view !== "empty";
        loadingState.hidden = view !== "loading";
        resultsSection.hidden = view !== "results";
    }

    function setLoading(isLoading) {
        solveBtn.disabled = isLoading;
        solveSpinner.hidden = !isLoading;
        solveBtnLabel.textContent = isLoading ? "Solving" : "Solve";
    }

    // ---------- Question box ----------

    function updateCharCount() {
        const length = problemText.value.length;
        charCount.textContent = `${length} / ${MAX_QUESTION_LENGTH}`;
        charCount.classList.toggle("near-limit", length > MAX_QUESTION_LENGTH * 0.9);
    }

    // Live preview: only shown when the question contains LaTeX
    function updatePreview() {
        const text = problemText.value.trim();
        const hasMath = /[\\^_$]/.test(text);

        if (!text || !hasMath) {
            mathPreview.hidden = true;
            return;
        }

        mathPreviewContent.textContent = ensureMathDelimiters(text);
        mathPreview.hidden = false;
        renderMath(mathPreviewContent);
    }

    function onQuestionChange() {
        updateCharCount();
        clearTimeout(previewTimer);
        previewTimer = setTimeout(updatePreview, PREVIEW_DELAY_MS);
    }

    problemText.addEventListener("input", onQuestionChange);

    // Ctrl + Enter (or Cmd + Enter on Mac) solves the question
    problemText.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            solveForm.requestSubmit();
        }
    });

    // Symbol bar: insert LaTeX at the cursor. "|" in the snippet marks where the cursor goes.
    symbolBar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-insert]");
        if (!button) {
            return;
        }

        const snippet = button.dataset.insert;
        const cursorOffset = snippet.indexOf("|");
        const text = snippet.replace("|", "");
        const start = problemText.selectionStart;

        problemText.setRangeText(text, start, problemText.selectionEnd, "end");
        if (cursorOffset >= 0) {
            problemText.setSelectionRange(start + cursorOffset, start + cursorOffset);
        }
        problemText.focus();
        onQuestionChange();
    });

    // Example questions fill the box (they do not solve right away, to save quota)
    emptyState.addEventListener("click", (event) => {
        const button = event.target.closest("[data-example]");
        if (!button) {
            return;
        }
        problemText.value = button.dataset.example;
        problemText.focus();
        onQuestionChange();
    });

    // ---------- Photo upload ----------

    function clearImage() {
        selectedImage = null;
        imageInput.value = "";
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        imagePreview.removeAttribute("src");
        imagePreviewBox.hidden = true;
        dropzone.hidden = false;
    }

    function selectImage(file) {
        clearImage();

        if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
            showStatus("This file type is not supported. Use a PNG, JPEG, or WEBP photo.", "error");
            return;
        }

        selectedImage = file;
        previewUrl = URL.createObjectURL(file);
        imagePreview.src = previewUrl;
        imagePreviewBox.hidden = false;
        dropzone.hidden = true;
        showStatus("", "info");
    }

    imageInput.addEventListener("change", () => {
        const file = imageInput.files[0];
        if (file) {
            selectImage(file);
        }
    });

    removeImageBtn.addEventListener("click", () => {
        clearImage();
        imageInput.focus();
    });

    // Drag and drop
    dropzone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropzone.classList.add("is-dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("is-dragover");
    });

    dropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragover");
        const file = event.dataTransfer.files[0];
        if (file) {
            selectImage(file);
        }
    });

    // Paste a screenshot anywhere on the page (text paste still works normally)
    document.addEventListener("paste", (event) => {
        const file = Array.from(event.clipboardData.files).find((item) => item.type.startsWith("image/"));
        if (file) {
            event.preventDefault();
            selectImage(file);
        }
    });

    // ---------- Showing a solution ----------

    function renderVideos(videos) {
        videosContainer.innerHTML = "";

        // Videos can come from saved history, so check every field
        const safeVideos = (videos || []).filter(
            (video) =>
                video &&
                typeof video.title === "string" &&
                isSafeHttpsUrl(video.url) &&
                isSafeHttpsUrl(video.thumbnail)
        );

        if (safeVideos.length === 0) {
            const message = document.createElement("p");
            message.className = "no-videos";
            message.textContent = "No videos found for this topic.";
            videosContainer.appendChild(message);
            return;
        }

        // Build elements with textContent so titles are never parsed as HTML
        safeVideos.forEach((video) => {
            const link = document.createElement("a");
            link.className = "video";
            link.href = video.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";

            const img = document.createElement("img");
            img.src = video.thumbnail;
            img.alt = "";
            img.loading = "lazy";

            const title = document.createElement("span");
            title.className = "video-title";
            title.textContent = video.title;

            link.appendChild(img);
            link.appendChild(title);
            videosContainer.appendChild(link);
        });
    }

    function renderSolution(data) {
        displayProblem.textContent = ensureMathDelimiters(data.problem);
        topicBadge.textContent = data.topic || "Math";

        stepsList.innerHTML = "";
        (data.steps || []).forEach((step, index) => {
            const li = document.createElement("li");
            // Used by CSS to reveal steps one after another
            li.style.setProperty("--i", index);

            const text = document.createElement("span");
            text.className = "step-text";
            text.textContent = step;

            li.appendChild(text);
            stepsList.appendChild(li);
        });

        lastAnswer = data.final_answer || "";
        finalAnswer.textContent = ensureMathDelimiters(lastAnswer);
        copyAnswerBtn.textContent = "Copy answer";

        renderVideos(data.videos);
        showView("results");
        renderMath(resultsSection);
    }

    copyAnswerBtn.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(lastAnswer);
            copyAnswerBtn.textContent = "Copied";
        } catch (error) {
            copyAnswerBtn.textContent = "Copy failed. Select the answer to copy it.";
        }
    });

    // ---------- History panel ----------

    function historyTitle(entry) {
        const title = entry.result.problem || entry.question || "Photo question";
        return entry.hadImage ? `Photo: ${title}` : title;
    }

    function renderHistory() {
        historyList.innerHTML = "";
        historyCount.textContent = String(historyItems.length);
        historyEmpty.hidden = historyItems.length > 0;
        clearHistoryBtn.hidden = historyItems.length === 0;

        // Built with textContent so saved text is never parsed as HTML
        historyItems.forEach((entry) => {
            const item = document.createElement("li");
            item.className = "history-item";
            item.dataset.id = entry.id;
            if (entry.id === activeHistoryId) {
                item.setAttribute("aria-current", "true");
            }

            const openBtn = document.createElement("button");
            openBtn.type = "button";
            openBtn.className = "history-open";
            openBtn.dataset.action = "open";

            const title = document.createElement("span");
            title.className = "history-title";
            title.textContent = ensureMathDelimiters(historyTitle(entry));

            const meta = document.createElement("span");
            meta.className = "history-meta";
            const topic = entry.result.topic ? `${entry.result.topic}, ` : "";
            meta.textContent = `${topic}${dateFormat.format(new Date(entry.savedAt))}`;

            openBtn.appendChild(title);
            openBtn.appendChild(meta);

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "history-delete";
            deleteBtn.dataset.action = "delete";
            deleteBtn.setAttribute("aria-label", "Delete from history");
            deleteBtn.title = "Delete from history";
            deleteBtn.textContent = "×";

            item.appendChild(openBtn);
            item.appendChild(deleteBtn);
            historyList.appendChild(item);
        });

        renderMath(historyList);
    }

    function saveAndRenderHistory(items) {
        historyItems = saveHistory(items);
        renderHistory();
    }

    // Open or delete a saved question
    historyList.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button) {
            return;
        }

        const id = button.closest(".history-item").dataset.id;
        const entry = historyItems.find((item) => item.id === id);
        if (!entry) {
            return;
        }

        if (button.dataset.action === "delete") {
            if (activeHistoryId === id) {
                activeHistoryId = null;
            }
            saveAndRenderHistory(historyItems.filter((item) => item.id !== id));
            return;
        }

        // Show the saved solution without calling the API again
        activeHistoryId = id;
        hasResult = true;
        showStatus("", "info");
        renderSolution(entry.result);
        renderHistory();

        if (window.innerWidth < 980) {
            sheet.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    });

    // Clear all needs two clicks, so it cannot happen by accident
    clearHistoryBtn.addEventListener("click", () => {
        if (!clearConfirmTimer) {
            clearHistoryBtn.textContent = "Click again to clear all";
            clearConfirmTimer = setTimeout(() => {
                clearConfirmTimer = null;
                clearHistoryBtn.textContent = "Clear history";
            }, 4000);
            return;
        }

        clearTimeout(clearConfirmTimer);
        clearConfirmTimer = null;
        clearHistoryBtn.textContent = "Clear history";
        activeHistoryId = null;
        saveAndRenderHistory([]);
    });

    // Keep tabs in sync: history changed in another tab of this site
    window.addEventListener("storage", (event) => {
        if (event.key === HISTORY_KEY) {
            historyItems = loadHistory();
            renderHistory();
        }
    });

    // ---------- Sending the question ----------

    function getChoice(name) {
        return solveForm.querySelector(`input[name="${name}"]:checked`).value;
    }

    // Build the fetch request: JSON for text, form data for photos
    async function buildRequest(textValue) {
        const difficulty = getChoice("difficulty");
        const language = getChoice("language");

        if (!selectedImage) {
            return {
                url: "/solve",
                options: {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: textValue, difficulty, language }),
                },
            };
        }

        const imageToSend = await compressImage(selectedImage);

        if (imageToSend.size > MAX_IMAGE_BYTES) {
            throw new Error("This photo is larger than 10 MB. Use a smaller photo or crop it.");
        }

        const formData = new FormData();
        const fileName = imageToSend === selectedImage ? selectedImage.name : "image.jpg";
        formData.append("image", imageToSend, fileName);
        formData.append("question", textValue);
        formData.append("difficulty", difficulty);
        formData.append("language", language);

        return { url: "/solve/image", options: { method: "POST", body: formData } };
    }

    solveForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const textValue = problemText.value.trim();
        // Remember what was sent, in case the user changes options while waiting
        const sentOptions = {
            hadImage: Boolean(selectedImage),
            difficulty: getChoice("difficulty"),
            language: getChoice("language"),
        };

        if (!textValue && !selectedImage) {
            showStatus("Type a question or add a photo first.", "error");
            problemText.focus();
            return;
        }

        setLoading(true);
        showStatus("", "info");
        showView("loading");

        // On phones the sheet is below the form, so bring it into view
        if (window.innerWidth < 980) {
            sheet.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        try {
            const request = await buildRequest(textValue);
            const response = await fetch(request.url, request.options);

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                const msg = errData && errData.message
                    ? errData.message
                    : `The server returned an error (${response.status}). Try again in a moment.`;
                throw new Error(msg);
            }

            const data = await response.json();
            hasResult = true;
            renderSolution(data);

            // Save to history (the photo itself is never saved)
            historyItems = addToHistory(historyItems, { question: textValue, ...sentOptions, result: data });
            activeHistoryId = historyItems[0].id;
            saveAndRenderHistory(historyItems);
        } catch (error) {
            console.error("Error solving problem:", error);
            // Keep the previous solution on screen if there was one
            showView(hasResult ? "results" : "empty");
            showStatus(error.message || "Could not solve the question. Try again.", "error");
        } finally {
            setLoading(false);
        }
    });

    // KaTeX loads after this script, so render math in the examples and history once it is ready
    document.addEventListener("DOMContentLoaded", () => {
        renderMath(emptyState);
        renderMath(historyList);
        updatePreview();
    });

    updateCharCount();
    renderHistory();
}

initApp();
