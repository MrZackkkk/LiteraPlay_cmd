let backend = null;
let currentCharacterName = "";
let currentUserCharacter = "Анонимен";
let currentColor = "";
let libraryData = {};
// H-04: Cache the validated key at the moment it is confirmed valid.
let _validatedApiKey = "";

let previousScreen = "menu";
let currentFontSize = 16;
let _isLoading = false;


/** Escape HTML special characters to prevent XSS. */
function sanitizeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Apply lightweight markdown transforms to already-sanitized HTML.
 * Handles **bold**, *italic*, and "> blockquote" lines.
 * Must run after sanitizeHtml() so that > is already &gt;.
 */
function renderMarkdown(html) {
    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic: *text* — bold was already replaced, so remaining * are singles
    html = html.replace(/\*([^*\n<>]+?)\*/g, "<em>$1</em>");
    // Blockquote: "> text" at start of a line (> is escaped to &gt;)
    html = html.replace(/(^|<br>)&gt; (.+?)(?=<br>|$)/g, "$1<blockquote class=\"md-quote\">$2</blockquote>");
    return html;
}

/** Copy text to clipboard via the Python backend (Qt WebEngine has no reliable JS clipboard API). */
function copyToClipboard(text) {
    backend.copy_to_clipboard(text);
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
        backend.chatOverloaded.connect(showOverloadModal);
        backend.chatEnded.connect(handleChatEnded);

        backend.chapterTransition.connect(handleChapterTransition);
        backend.currentModel.connect(handleCurrentModel);

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
        _validatedApiKey = "";
        backend.verify_api_key(key);
    });

    document.getElementById("btn-dialog-no").addEventListener("click", () => {
        document.getElementById("dialog-overlay").classList.add("hidden");
        if (_validatedApiKey) backend.save_api_key_decision(_validatedApiKey, false);
    });

    document.getElementById("btn-dialog-yes").addEventListener("click", () => {
        document.getElementById("dialog-overlay").classList.add("hidden");
        if (_validatedApiKey) backend.save_api_key_decision(_validatedApiKey, true);
    });

    // Situation Screen
    document.getElementById("btn-sit-back").addEventListener("click", () => showScreen("menu"));

    // Chat Screen
    document.getElementById("btn-back").addEventListener("click", () => showScreen("menu"));

    // Settings Screen — track which screen opened settings so Back returns correctly
    document.getElementById("btn-open-settings").addEventListener("click", () => {
        previousScreen = "menu";
        showScreen("settings");
    });

    document.getElementById("btn-chat-settings").addEventListener("click", () => {
        previousScreen = "chat";
        showScreen("settings");
    });

    document.getElementById("btn-close-settings").addEventListener("click", () => {
        showScreen(previousScreen);
        previousScreen = "menu";
    });

    document.getElementById("btn-save-settings").addEventListener("click", () => {
        const selectedModel = document.getElementById("model-picker").value;
        const status = document.getElementById("settings-status");

        status.innerText = "Запазване...";
        status.style.color = "var(--text-secondary)";
        backend.save_model(selectedModel);

        setTimeout(() => {
            status.innerText = "Запазено!";
            status.style.color = "var(--success)";
            setTimeout(() => { status.innerText = ""; }, 2000);
        }, 500);
    });

    // Chat input
    document.getElementById("btn-send").addEventListener("click", sendInputMsg);
    document.getElementById("chat-input").addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendInputMsg();
    });
    // Gray out send button when input is empty
    document.getElementById("chat-input").addEventListener("input", updateSendButton);

    // Font size controls
    document.getElementById("btn-font-decrease").addEventListener("click", () => changeFontSize(-1));
    document.getElementById("btn-font-increase").addEventListener("click", () => changeFontSize(1));

    // Scroll-to-bottom floating button
    initScrollToBottom();

    // Keyboard shortcuts: press 1–9 to click the corresponding option button
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !document.getElementById("overload-modal").classList.contains("hidden")) {
            hideOverloadModal();
            return;
        }
        if (document.getElementById("chat-screen").classList.contains("hidden")) return;
        if (document.activeElement === document.getElementById("chat-input")) return;
        const num = parseInt(e.key);
        if (num >= 1 && num <= 9) {
            const options = document.querySelectorAll("#chat-options .btn-option:not([disabled])");
            if (options[num - 1]) {
                e.preventDefault();
                options[num - 1].click();
            }
        }
    });

    document.getElementById("btn-overload-dismiss").addEventListener("click", hideOverloadModal);

    setupCustomSelect();
    updateSendButton();
}

function changeFontSize(delta) {
    currentFontSize = Math.max(12, Math.min(22, currentFontSize + delta));
    document.documentElement.style.setProperty("--chat-font-size", currentFontSize + "px");
}

function updateSendButton() {
    if (_isLoading) return;
    const btn = document.getElementById("btn-send");
    const hasText = document.getElementById("chat-input").value.trim().length > 0;
    btn.disabled = !hasText;
}

function initScrollToBottom() {
    const history = document.getElementById("chat-history");
    const btn = document.getElementById("btn-scroll-bottom");

    history.addEventListener("scroll", updateScrollButton);
    btn.addEventListener("click", () => {
        history.scrollTop = history.scrollHeight;
    });
}

function updateScrollButton() {
    const history = document.getElementById("chat-history");
    const btn = document.getElementById("btn-scroll-bottom");
    if (!btn) return;
    const distFromBottom = history.scrollHeight - history.scrollTop - history.clientHeight;
    btn.classList.toggle("hidden", distFromBottom < 80);
}

function setupCustomSelect() {
    const selected = document.querySelector(".select-selected");
    const items = document.querySelector(".select-items");
    const hiddenInput = document.getElementById("model-picker");

    if (!selected || !items || !hiddenInput) return;

    selected.addEventListener("click", function (e) {
        e.stopPropagation();
        this.classList.toggle("select-arrow-active");
        items.classList.toggle("select-hide");

        // Flip the dropdown upward if there isn't enough space below
        if (!items.classList.contains("select-hide")) {
            const rect = selected.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            const itemsHeight = items.scrollHeight + 16;
            if (spaceBelow < itemsHeight) {
                items.style.top = "auto";
                items.style.bottom = "calc(100% + 8px)";
                items.style.borderRadius = "16px 16px 4px 4px";
            } else {
                items.style.top = "calc(100% + 8px)";
                items.style.bottom = "auto";
                items.style.borderRadius = "16px";
            }
        }
    });

    const options = items.querySelectorAll("div");
    options.forEach(option => {
        option.addEventListener("click", function (e) {
            e.stopPropagation();
            hiddenInput.value = this.getAttribute("data-value");
            // M-05: Use textContent (not innerHTML) to avoid XSS from model names
            selected.textContent = this.textContent;
            options.forEach(opt => opt.classList.remove("same-as-selected"));
            this.classList.add("same-as-selected");
            selected.classList.remove("select-arrow-active");
            items.classList.add("select-hide");
        });
    });

    document.addEventListener("click", function (e) {
        if (e.target !== selected && e.target !== items) {
            selected.classList.remove("select-arrow-active");
            items.classList.add("select-hide");
        }
    });
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    if (name === "api") document.getElementById("api-screen").classList.remove("hidden");
    if (name === "menu") document.getElementById("menu-screen").classList.remove("hidden");
    if (name === "settings") document.getElementById("settings-screen").classList.remove("hidden");
    if (name === "situation") document.getElementById("situation-screen").classList.remove("hidden");
    if (name === "chat") document.getElementById("chat-screen").classList.remove("hidden");
}

// === Python Signal Handlers ===

function handleApiValidation(isValid, message) {
    document.getElementById("btn-verify").disabled = false;
    document.getElementById("btn-verify").innerText = "Verify & Save";

    if (isValid) {
        // H-04: Cache the key at the moment we know it is valid
        _validatedApiKey = document.getElementById("api-key-input").value.trim();
        document.getElementById("api-status").innerText = "";
        document.getElementById("dialog-overlay").classList.remove("hidden");
    } else {
        _validatedApiKey = "";
        document.getElementById("api-status").style.color = "var(--error)";
        document.getElementById("api-status").innerText = message;
    }
}

function handleCurrentModel(modelName) {
    const hiddenInput = document.getElementById("model-picker");
    if (!hiddenInput) return;
    hiddenInput.value = modelName;

    const items = document.querySelectorAll(".select-items div");
    const selected = document.querySelector(".select-selected");
    items.forEach(item => {
        if (item.getAttribute("data-value") === modelName) {
            // M-05: Use textContent (not innerHTML) to avoid XSS from model names
            selected.textContent = item.textContent;
            items.forEach(opt => opt.classList.remove("same-as-selected"));
            item.classList.add("same-as-selected");
        }
    });
}

function renderLibrary(libraryJson) {
    showScreen("menu");

    libraryData = JSON.parse(libraryJson);
    const container = document.getElementById("library-cards-container");
    container.innerHTML = "";

    let cardIndex = 0;
    for (const [key, data] of Object.entries(libraryData)) {
        const card = document.createElement("div");
        card.className = "library-card glass-card";
        card.style.setProperty("--card-index", cardIndex++);

        const safeColor = data.color || "var(--accent)";

        const h2 = document.createElement("h2");
        h2.textContent = data.title;
        card.appendChild(h2);

        if (data.situations && data.situations.length > 0) {
            const p = document.createElement("p");
            p.className = "char-info";
            p.style.color = safeColor;
            p.textContent = `Ситуации: ${data.situations.length}`;
            card.appendChild(p);
        }

        const btn = document.createElement("button");
        btn.className = "btn-card";
        btn.style.backgroundColor = safeColor;
        btn.textContent = "Избери";
        btn.addEventListener("click", () => showSituations(key));
        card.appendChild(btn);

        container.appendChild(card);
    }
}

function showSituations(workKey) {
    const workData = libraryData[workKey];
    if (!workData || !workData.situations) return;

    document.getElementById("situation-title").innerText = workData.title;

    const container = document.getElementById("situation-cards-container");
    container.innerHTML = "";

    workData.situations.forEach((sit, idx) => {
        const card = document.createElement("div");
        card.className = "library-card glass-card";
        card.style.setProperty("--card-index", idx);

        const safeColor = sit.color || workData.color || "var(--accent)";
        const charDisplay = sit.characters
            ? `Герои: ${sit.characters}`
            : `Герой: ${sit.character}`;

        const h2 = document.createElement("h2");
        h2.textContent = sit.title;
        card.appendChild(h2);

        const p = document.createElement("p");
        p.className = "char-info";
        p.style.color = safeColor;
        p.textContent = charDisplay;
        card.appendChild(p);

        const btn = document.createElement("button");
        btn.className = "btn-card";
        btn.style.backgroundColor = safeColor;
        btn.textContent = "Започни разговор";
        btn.addEventListener("click", () => startChat(workKey, sit.key));
        card.appendChild(btn);

        container.appendChild(card);
    });

    showScreen("situation");
}

function startChat(workKey, sitKey) {
    const workData = libraryData[workKey];
    const sitData = workData.situations.find(s => s.key === sitKey);
    if (!sitData) return;

    currentCharacterName = sitData.character;
    currentUserCharacter = sitData.user_character || "Анонимен";
    currentColor = sitData.color || workData.color || "var(--accent)";
    document.getElementById("chat-title").innerText = sitData.character;

    document.getElementById("chat-history").innerHTML = "";
    document.getElementById("chat-options").innerHTML = "";
    document.getElementById("api-status").innerText = "";

    const typingInd = document.getElementById("typing-indicator");
    if (typingInd) {
        typingInd.classList.add("hidden");
        typingInd.style.display = "none";
    }

    // Reset scroll-to-bottom button and chat footer
    document.getElementById("btn-scroll-bottom").classList.add("hidden");
    document.querySelector(".chat-footer").style.display = "";

    showScreen("chat");

    updateSendButton();
    backend.start_chat_session(workKey, sitKey);
}

function handleChatStarted(intro, firstMessage) {
    _renderChatMessage("System", intro, false, true);
    _renderChatMessage(currentCharacterName, firstMessage, false, false);
}

function handleChatEnded(finalText) {
    _renderChatMessage("System", "\n" + finalText, false, true);

    document.getElementById("chat-options").innerHTML = "";
    document.querySelector(".chat-footer").style.display = "none";

    const history = document.getElementById("chat-history");
    const btnWrapper = document.createElement("div");
    btnWrapper.className = "msg-wrapper system";
    btnWrapper.style.textAlign = "center";
    btnWrapper.style.padding = "1.5rem 0";

    const btn = document.createElement("button");
    btn.className = "btn-primary";
    btn.innerText = "Назад към менюто";
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
    wrapper.className = `msg-wrapper ${isSystem ? "system" : (isUser ? "user" : "ai")}`;

    const msgContent = document.createElement("div");
    msgContent.className = "msg-content";

    if (!isSystem) {
        const senderEl = document.createElement("span");
        senderEl.className = "sender-name";
        senderEl.textContent = sender;
        msgContent.appendChild(senderEl);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const safeText = sanitizeHtml(text);
    let formattedText = safeText.replace(/\n/g, "<br>");
    if (!isUser && !isSystem) {
        formattedText = renderMarkdown(formattedText);
    }
    bubble.innerHTML = formattedText;
    msgContent.appendChild(bubble);

    // Footer: timestamp (all non-system) + copy button (AI only)
    if (!isSystem) {
        const msgFooter = document.createElement("div");
        msgFooter.className = "msg-footer";

        const tsEl = document.createElement("span");
        tsEl.className = "msg-timestamp";
        tsEl.textContent = new Date().toLocaleTimeString("bg-BG", { hour: "2-digit", minute: "2-digit" });
        msgFooter.appendChild(tsEl);

        if (!isUser) {
            const copyBtn = document.createElement("button");
            copyBtn.className = "btn-copy";
            copyBtn.title = "Копирай";
            copyBtn.textContent = "⧉";
            copyBtn.onclick = () => {
                copyToClipboard(text);
                copyBtn.textContent = "✓";
                setTimeout(() => { copyBtn.textContent = "⧉"; }, 1500);
            };
            msgFooter.appendChild(copyBtn);
        }

        msgContent.appendChild(msgFooter);
    }

    wrapper.appendChild(msgContent);
    history.appendChild(wrapper);

    // Only auto-scroll if the user is already near the bottom
    const distFromBottom = history.scrollHeight - history.scrollTop - history.clientHeight;
    if (distFromBottom < 120) {
        setTimeout(() => { history.scrollTop = history.scrollHeight; }, 50);
    }
    updateScrollButton();
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

    optionsArray.forEach((opt, idx) => {
        const isCanonical = opt.includes("[Канонично]");
        const displayText = opt.replace("[Канонично]", "").trim();

        const btn = document.createElement("button");
        btn.className = "btn-option";
        if (isCanonical) btn.classList.add("canonical-option");

        // Keyboard shortcut hint badge (1–9)
        if (idx < 9) {
            const keyHint = document.createElement("span");
            keyHint.className = "option-key-hint";
            keyHint.textContent = String(idx + 1);
            btn.appendChild(keyHint);
        }

        const labelSpan = document.createElement("span");
        labelSpan.textContent = isCanonical ? `📖 ${displayText}` : displayText;
        btn.appendChild(labelSpan);

        btn.onmouseover = () => { if (!isCanonical) btn.style.borderColor = currentColor; };
        btn.onmouseout = () => { if (!isCanonical) btn.style.borderColor = "var(--border)"; };
        btn.onclick = () => {
            _renderChatMessage(currentUserCharacter, displayText, true, false);
            container.innerHTML = "";
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
    updateSendButton();
    _renderChatMessage(currentUserCharacter, text, true, false);
    document.getElementById("chat-options").innerHTML = "";

    backend.send_user_message(text);
}

function showOverloadModal() {
    document.getElementById("overload-modal").classList.remove("hidden");
}

function hideOverloadModal() {
    document.getElementById("overload-modal").classList.add("hidden");
}

function toggleLoading(isLoading) {
    _isLoading = isLoading;
    const ind = document.getElementById("typing-indicator");
    const input = document.getElementById("chat-input");
    const btn = document.getElementById("btn-send");
    const statusEl = document.getElementById("status-indicator");
    const statusLabel = document.getElementById("status-label");

    if (isLoading) {
        ind.classList.remove("hidden");
        ind.style.display = "block";
        input.disabled = true;
        btn.disabled = true;
        statusEl.classList.add("busy");
        statusLabel.textContent = "Мисли...";
    } else {
        ind.classList.add("hidden");
        ind.style.display = "none";
        input.disabled = false;
        updateSendButton();
        input.focus();
        statusEl.classList.remove("busy");
        statusLabel.textContent = "На линия";
    }
    document.getElementById("chat-history").scrollTop = document.getElementById("chat-history").scrollHeight;
}


function handleChapterTransition(chapterTitle) {
    _renderChatMessage("System", `— ${chapterTitle} —`, false, true);
}
