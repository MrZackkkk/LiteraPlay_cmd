let backend = null;
let currentCharacterName = "";
let currentColor = "#3B82F6";

function escapeHTML(str) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// Initialize QWebChannel
document.addEventListener("DOMContentLoaded", () => {
    new QWebChannel(qt.webChannelTransport, (channel) => {
        backend = channel.objects.backend;

        // Connect Python Signals to JS functions
        backend.apiValidationResult.connect(handleApiValidation);
        backend.libraryLoaded.connect(renderLibrary);
        backend.chatMessageReceived.connect(renderChatMessage);
        backend.chatOptionsUpdated.connect(renderChatOptions);
        backend.chatStarted.connect(handleChatStarted);
        backend.loadingStateChanged.connect(toggleLoading);
        backend.chatError.connect((msg) => renderChatMessage("System", "Грешка: " + msg, false, true));

        // Tell Python we are ready
        backend.request_initial_state();
    });

    setupEventListeners();
});

function setupEventListeners() {
    // API Screen
    document.getElementById("btn-verify").addEventListener("click", submitApiKey);
    document.getElementById("api-key-input").addEventListener("keypress", (e) => {
        if (e.key === "Enter") submitApiKey();
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

    // Chat Screen
    document.getElementById("btn-back").addEventListener("click", () => {
        showScreen("menu");
    });

    document.getElementById("btn-send").addEventListener("click", sendInputMsg);
    document.getElementById("chat-input").addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendInputMsg();
    });
}

function submitApiKey() {
    const key = document.getElementById("api-key-input").value.trim();
    if (!key) return;

    document.getElementById("btn-verify").disabled = true;
    document.getElementById("btn-verify").innerText = "Checking...";
    document.getElementById("api-status").style.color = "var(--text-secondary)";
    document.getElementById("api-status").innerText = "Проверка на API ключ...";
    backend.verify_api_key(key);
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    if (name === "api") document.getElementById("api-screen").classList.remove("hidden");
    if (name === "menu") document.getElementById("menu-screen").classList.remove("hidden");
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

    const lib = JSON.parse(libraryJson);
    const container = document.getElementById("library-cards-container");
    container.innerHTML = "";

    for (const [key, data] of Object.entries(lib)) {
        const card = document.createElement("div");
        card.className = "library-card glass-card";

        const safeColor = data.color || "var(--accent)";

        card.innerHTML = `
            <h2>${escapeHTML(data.title)}</h2>
            <p class="char-info" style="color: ${safeColor}">Герой: ${escapeHTML(data.character)}</p>
            <button class="btn-card" style="background-color: ${safeColor}" onclick="startChat('${escapeHTML(key)}', '${escapeHTML(data.character)}', '${safeColor}')">Започни разговор</button>
        `;
        container.appendChild(card);
    }
}

function startChat(key, charName, color) {
    currentCharacterName = charName;
    currentColor = color;
    document.getElementById("chat-title").innerText = charName;

    document.getElementById("chat-history").innerHTML = "";
    document.getElementById("chat-options").innerHTML = "";
    document.getElementById("api-status").innerText = ""; // reset status

    showScreen("chat");
    backend.start_chat_session(key);
}

function handleChatStarted(intro, firstMessage) {
    renderChatMessage("System", intro, false, true);
    renderChatMessage(currentCharacterName, firstMessage, false, false);
}

function renderChatMessage(sender, text, isUser, isSystem) {
    const history = document.getElementById("chat-history");
    const wrapper = document.createElement("div");
    wrapper.className = `msg-wrapper ${isSystem ? 'system' : (isUser ? 'user' : 'ai')}`;

    let html = "";
    if (!isSystem) {
        html += `<span class="sender-name">${escapeHTML(sender)}</span>`;
    }

    // Sanitize and convert newlines to breaks
    const safeText = escapeHTML(text);
    const formattedText = safeText.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
    html += `<div class="bubble">${formattedText}</div>`;

    wrapper.innerHTML = html;
    history.appendChild(wrapper);

    // Scroll to bottom
    setTimeout(() => { history.scrollTop = history.scrollHeight; }, 50);
}

function renderChatOptions(optionsArray) {
    const container = document.getElementById("chat-options");
    container.innerHTML = "";

    optionsArray.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "btn-option";
        btn.innerText = opt;
        btn.onmouseover = () => btn.style.borderColor = currentColor;
        btn.onmouseout = () => btn.style.borderColor = "var(--border)";
        btn.onclick = () => {
            renderChatMessage("Ти", opt, true, false);
            container.innerHTML = ""; // Clear options
            backend.send_user_message(opt);
        };
        container.appendChild(btn);
    });
}

function sendInputMsg() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    renderChatMessage("Ти", text, true, false);
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
