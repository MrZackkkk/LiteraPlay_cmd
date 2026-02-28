let backend = null; // Global state
let currentCharacterName = "";
let currentUserCharacter = "Ти"; // Default
let currentColor = "";
let libraryData = {};

/** Escape HTML special characters to prevent XSS. */
function sanitizeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// Initialize QWebChannel
document.addEventListener("DOMContentLoaded", () => {
    new QWebChannel(qt.webChannelTransport, (channel) => {
        backend = channel.objects.backend;

        // Connect Python Signals to JS functions
        backend.apiValidationResult.connect(handleApiValidation);
        backend.libraryLoaded.connect(renderLibrary);
        backend.chatMessageReceived.connect(handleChatMessageJson);
        backend.chatOptionsUpdated.connect(renderChatOptions);
        backend.chatStarted.connect(handleChatStarted);
        backend.loadingStateChanged.connect(toggleLoading);
        backend.chatError.connect((msg) => _renderChatMessage("System", "Грешка: " + msg, false, true));
        backend.chatEnded.connect(handleChatEnded);
        backend.storyProgressUpdated.connect(handleStoryProgress);
        backend.chapterTransition.connect(handleChapterTransition);

        // Tell Python we are ready
        backend.request_initial_state();
    });

    setupEventListeners();
});

function setupEventListeners() {
    // API Screen
    document.getElementById("btn-verify").addEventListener("click", () => {
        const key = document.getElementById("api-key-input").value.trim();
        if (!key) return;

        document.getElementById("btn-verify").disabled = true;
        document.getElementById("btn-verify").innerText = "Checking...";
        document.getElementById("api-status").innerText = "Проверка на API ключ...";
        backend.verify_api_key(key);
    });

    document.getElementById("btn-dialog-no").addEventListener("click", () => {
        document.getElementById("dialog-overlay").classList.add("hidden");
        const key = document.getElementById("api-key-input").value.trim();
        backend.save_api_key_decision(key, false);
    });

    document.getElementById("btn-dialog-yes").addEventListener("click", () => {
        document.getElementById("dialog-overlay").classList.add("hidden");
        const key = document.getElementById("api-key-input").value.trim();
        backend.save_api_key_decision(key, true);
    });

    // Situation Screen
    document.getElementById("btn-sit-back").addEventListener("click", () => {
        showScreen("menu");
    });

    // Chat Screen
    document.getElementById("btn-back").addEventListener("click", () => {
        showScreen("menu");
    });

    document.getElementById("btn-send").addEventListener("click", sendInputMsg);
    document.getElementById("chat-input").addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendInputMsg();
    });
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    if (name === "api") document.getElementById("api-screen").classList.remove("hidden");
    if (name === "menu") document.getElementById("menu-screen").classList.remove("hidden");
    if (name === "situation") document.getElementById("situation-screen").classList.remove("hidden");
    if (name === "chat") document.getElementById("chat-screen").classList.remove("hidden");
}

// === Python Signal Handlers ===

function handleApiValidation(isValid, message) {
    document.getElementById("btn-verify").disabled = false;
    document.getElementById("btn-verify").innerText = "Verify & Save";

    if (isValid) {
        document.getElementById("api-status").innerText = "";
        document.getElementById("dialog-overlay").classList.remove("hidden");
    } else {
        document.getElementById("api-status").style.color = "var(--error)";
        document.getElementById("api-status").innerText = message;
    }
}

function renderLibrary(libraryJson) {
    // Transition to Menu if it's the first time
    showScreen("menu");

    libraryData = JSON.parse(libraryJson);
    const container = document.getElementById("library-cards-container");
    container.innerHTML = "";

    for (const [key, data] of Object.entries(libraryData)) {
        const card = document.createElement("div");
        card.className = "library-card glass-card";

        const safeColor = data.color || "var(--accent)";
        let numSituations = "";
        if (data.situations && data.situations.length > 0) {
            numSituations = `Ситуации: ${data.situations.length}`;
        }

        card.innerHTML = `
            <h2>${data.title}</h2>
            <p class="char-info" style="color: ${safeColor}">${numSituations}</p>
            <button class="btn-card" style="background-color: ${safeColor}" onclick="showSituations('${key}')">Избери</button>
        `;
        container.appendChild(card);
    }
}

function showSituations(workKey) {
    const workData = libraryData[workKey];
    if (!workData || !workData.situations) return;

    document.getElementById("situation-title").innerText = workData.title;

    const container = document.getElementById("situation-cards-container");
    container.innerHTML = "";

    workData.situations.forEach((sit) => {
        const card = document.createElement("div");
        card.className = "library-card glass-card";

        const safeColor = sit.color || workData.color || "var(--accent)";

        const charDisplay = sit.characters
            ? `Герои: ${sit.characters}`
            : `Герой: ${sit.character}`;

        card.innerHTML = `
            <h2>${sit.title}</h2>
            <p class="char-info" style="color: ${safeColor}">${charDisplay}</p>
            <button class="btn-card" style="background-color: ${safeColor}" onclick="startChat('${workKey}', '${sit.key}')">Започни разговор</button>
        `;
        container.appendChild(card);
    });

    showScreen("situation");
}

function startChat(workKey, sitKey) {
    const workData = libraryData[workKey];
    const sitData = workData.situations.find(s => s.key === sitKey);
    if (!sitData) return;

    currentCharacterName = sitData.character;
    currentUserCharacter = sitData.user_character || "Ти";
    currentColor = sitData.color || workData.color || "var(--accent)";
    document.getElementById("chat-title").innerText = sitData.character;

    document.getElementById("chat-history").innerHTML = "";
    document.getElementById("chat-options").innerHTML = "";
    document.getElementById("api-status").innerText = ""; // reset status

    showScreen("chat");

    // Reset progress bar
    const prog = document.getElementById("story-progress");
    prog.classList.add("hidden");
    document.getElementById("chapter-label").innerText = "";
    document.getElementById("progress-bar-fill").style.width = "0%";

    backend.start_chat_session(workKey, sitKey);
}

function handleChatStarted(intro, firstMessage) {
    _renderChatMessage("System", intro, false, true);
    _renderChatMessage(currentCharacterName, firstMessage, false, false);
}

function handleChatEnded(finalText) {
    // Render the final narrative as a system message
    _renderChatMessage("System", "\n" + finalText, false, true);

    // Hide options and input area
    document.getElementById("chat-options").innerHTML = "";
    document.querySelector(".chat-footer").style.display = "none";

    // Show a "Back to menu" button
    const history = document.getElementById("chat-history");
    const btnWrapper = document.createElement("div");
    btnWrapper.className = "msg-wrapper system";
    btnWrapper.style.textAlign = "center";
    btnWrapper.style.padding = "1.5rem 0";

    const btn = document.createElement("button");
    btn.className = "btn-primary";
    btn.innerText = "\u041D\u0430\u0437\u0430\u0434 \u043A\u044A\u043C \u043C\u0435\u043D\u044E\u0442\u043E";
    btn.style.fontSize = "1rem";
    btn.style.padding = "0.75rem 2rem";
    btn.onclick = () => {
        document.querySelector(".chat-footer").style.display = "";
        showScreen("menu");
    };

    btnWrapper.appendChild(btn);
    history.appendChild(btnWrapper);

    setTimeout(() => { history.scrollTop = history.scrollHeight; }, 50);
}

// handleStoryTransition is removed because consecutive stories are selected from UI now

function handleChatMessageJson(jsonStr) {
    try {
        const data = JSON.parse(jsonStr);
        _renderChatMessage(data.sender, data.text, data.isUser, data.isSystem);
    } catch (e) {
        console.error("Failed to parse chat message JSON:", e);
    }
}

function _renderChatMessage(sender, text, isUser, isSystem) {
    const history = document.getElementById("chat-history");
    const wrapper = document.createElement("div");
    wrapper.className = `msg-wrapper ${isSystem ? 'system' : (isUser ? 'user' : 'ai')}`;

    let html = "";
    if (!isSystem) {
        html += `<span class="sender-name">${sender}</span>`;
    }

    // Convert newlines to breaks (sanitize first to prevent XSS)
    const safeText = sanitizeHtml(text);
    const formattedText = safeText.replace(/\n/g, '<br>');
    html += `<div class="bubble">${formattedText}</div>`;

    wrapper.innerHTML = html;
    history.appendChild(wrapper);

    // Scroll to bottom
    setTimeout(() => { history.scrollTop = history.scrollHeight; }, 50);
}

function renderChatOptions(optionsJson) {
    const container = document.getElementById("chat-options");
    container.innerHTML = "";

    let optionsArray = [];
    try {
        optionsArray = JSON.parse(optionsJson);
    } catch (e) {
        console.error("Failed to parse chat options:", e);
        return;
    }

    optionsArray.forEach(opt => {
        const isCanonical = opt.includes("[Канонично]");
        const displayText = opt.replace("[Канонично]", "").trim();

        const btn = document.createElement("button");
        btn.className = "btn-option";
        if (isCanonical) {
            btn.classList.add("canonical-option");
            btn.innerHTML = `📖 ${displayText}`;
        } else {
            btn.innerText = displayText;
        }

        btn.onmouseover = () => {
            if (!isCanonical) btn.style.borderColor = currentColor;
        };
        btn.onmouseout = () => {
            if (!isCanonical) btn.style.borderColor = "var(--border)";
        };
        btn.onclick = () => {
            _renderChatMessage(currentUserCharacter, displayText, true, false);
            container.innerHTML = ""; // Clear options
            backend.send_user_message(opt); // Send the full original text to backend!
        };
        container.appendChild(btn);
    });
}

function sendInputMsg() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    _renderChatMessage(currentUserCharacter, text, true, false);
    document.getElementById("chat-options").innerHTML = ""; // Clear options

    backend.send_user_message(text);
}

function toggleLoading(isLoading) {
    const ind = document.getElementById("typing-indicator");
    const input = document.getElementById("chat-input");
    const btn = document.getElementById("btn-send");

    if (isLoading) {
        ind.classList.remove("hidden");
        input.disabled = true;
        btn.disabled = true;
    } else {
        ind.classList.add("hidden");
        input.disabled = false;
        btn.disabled = false;
        input.focus();
    }
    document.getElementById("chat-history").scrollTop = document.getElementById("chat-history").scrollHeight;
}

function handleStoryProgress(jsonStr) {
    try {
        const info = JSON.parse(jsonStr);
        const prog = document.getElementById("story-progress");
        prog.classList.remove("hidden");

        const label = document.getElementById("chapter-label");
        label.innerText = `${info.chapter_title}  (${info.chapter_index + 1}/${info.total_chapters})`;

        const fill = document.getElementById("progress-bar-fill");
        fill.style.width = `${Math.min(info.progress_pct, 100)}%`;
    } catch (e) {
        console.error("Failed to parse story progress:", e);
    }
}

function handleChapterTransition(chapterTitle) {
    _renderChatMessage("System", `— ${chapterTitle} —`, false, true);
}
