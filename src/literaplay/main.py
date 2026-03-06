import contextlib
import copy
import json
import logging
import re
import sys
from pathlib import Path

# Allow direct execution from IDEs
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from literaplay import config
from literaplay.ai_service import AIService, APIOverloadedError, validate_api_key
from literaplay.data import LIBRARY
from literaplay.response_parser import parse_ai_json_response, validate_story_response
from literaplay.story_state import StoryStateManager

UI_PATH = Path(__file__).parent / "ui" / "index.html"


_LIBRARY_JSON_CACHE: str | None = None


def _build_library_json() -> str:
    """Build a JSON-serializable copy of LIBRARY (cached after first call)."""
    global _LIBRARY_JSON_CACHE
    if _LIBRARY_JSON_CACHE is not None:
        return _LIBRARY_JSON_CACHE
    lib = copy.deepcopy(LIBRARY)
    for _, work in lib.items():
        for sit in work.get("situations", []):
            if "user_character" not in sit:
                sit["user_character"] = "Разказвач"
    _LIBRARY_JSON_CACHE = json.dumps(lib)
    return _LIBRARY_JSON_CACHE


# ================== WORKER THREAD ==================


class AIChatWorker(QThread):
    response_signal = Signal(dict)
    error_signal = Signal(str)
    overload_signal = Signal()

    def __init__(self, ai_service, chat_session, user_text, context_injection=""):
        super().__init__()
        self.ai_service = ai_service
        self.chat_session = chat_session
        self.user_text = user_text
        self.context_injection = context_injection

    def run(self):
        try:
            response_text = self.ai_service.send_message_with_context(
                self.chat_session, self.user_text, self.context_injection
            )

            # Parse response
            data = parse_ai_json_response(response_text)
            if data and isinstance(data, dict):
                self.response_signal.emit(
                    {
                        "reply": data.get("reply", response_text),
                        "options": data.get("options", []),
                        "ended": data.get("ended", False),
                        "mood": data.get("mood", ""),
                        "location": data.get("location", ""),
                        "key_event": data.get("key_event", ""),
                    }
                )
            else:
                self.response_signal.emit(
                    {
                        "reply": response_text,
                        "options": [],
                        "ended": False,
                        "mood": "",
                        "location": "",
                        "key_event": "",
                    }
                )
        except Exception as e:
            logging.exception("AIChatWorker encountered an error")
            if isinstance(e, APIOverloadedError):
                self.overload_signal.emit()
            else:
                self.error_signal.emit(str(e))


class APIVerifyWorker(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, provider: str, key: str):
        super().__init__()
        self.provider = provider
        self.key = key

    def run(self):
        is_valid, message = validate_api_key(self.provider, self.key)
        self.finished_signal.emit(is_valid, message)


# ================== BACKEND BRIDGE ==================


def _format_reply_messages(reply, default_character: str) -> list[dict]:
    """Normalise a reply (list-of-dicts or plain string) into message dicts."""
    if isinstance(reply, list):
        results = []
        for msg in reply:
            results.append({
                "sender": msg.get("character", default_character),
                "text": msg.get("text", ""),
                "isUser": msg.get("type", "npc") == "user",
                "isSystem": msg.get("type", "npc") == "system"
            })
        return results
    else:
        final_reply_text = str(reply)
        return [
            {
                "sender": default_character,
                "text": final_reply_text,
                "isUser": False,
                "isSystem": False
            }
        ]


class BackendBridge(QObject):
    """Bridge between JS frontend and Python backend."""

    # Signals to JS
    apiValidationResult = Signal(bool, str)
    libraryLoaded = Signal(str)
    chatMessageReceived = Signal(str)  # JSON string {sender, text, isUser, isSystem}
    chatOptionsUpdated = Signal(str)  # JSON string — QWebChannel cannot serialize Python lists
    chatStarted = Signal(str, str)  # intro, first_message
    chatError = Signal(str)
    chatOverloaded = Signal()
    chatEnded = Signal(str)  # final narrative text
    loadingStateChanged = Signal(bool)
    storyProgressUpdated = Signal(str)  # JSON: chapter_title, turn, progress_pct
    chapterTransition = Signal(str)  # chapter title for transition message
    currentModel = Signal(str)  # Let JS know the current active model
    currentProvider = Signal(str)  # Let JS know the current provider
    providerModelsLoaded = Signal(str)  # JSON: {default, models[]}

    def __init__(self, app_window):
        super().__init__()
        self.app_window = app_window

        self.ai_service: AIService | None = None
        self.chat_session = None
        self.current_work: dict | None = None
        self.worker: AIChatWorker | None = None
        self.api_worker: APIVerifyWorker | None = None
        self.story_manager: StoryStateManager | None = None
        # Keep strong references to running workers to prevent premature GC;
        # finished workers are removed automatically via _cleanup_worker.
        self._active_workers: list = []

        if config.API_KEY and config.PROVIDER:
            with contextlib.suppress(Exception):
                self.ai_service = AIService(config.PROVIDER, config.API_KEY, config.DEFAULT_MODEL)

    @Slot()
    def request_initial_state(self):
        """Called by JS when the page finishes loading."""
        self.currentModel.emit(config.DEFAULT_MODEL)

        if config.PROVIDER:
            self.currentProvider.emit(config.PROVIDER)
            self.providerModelsLoaded.emit(config.get_models_json(config.PROVIDER))

        if config.API_KEY and config.PROVIDER and self.ai_service:
            # Skip straight to menu
            self.libraryLoaded.emit(_build_library_json())
        else:
            # JS stays on API screen by default
            pass

    @Slot(str, str)
    def verify_api_key(self, provider, key):
        # Guard against concurrent verification requests
        if self.api_worker is not None and self.api_worker.isRunning():
            return
        self.api_worker = APIVerifyWorker(provider, key)
        self.api_worker.finished_signal.connect(self._on_api_validation_worker_done)
        self._track_worker(self.api_worker)
        self.api_worker.start()

    @Slot(bool, str)
    def _on_api_validation_worker_done(self, is_valid, message):
        self.apiValidationResult.emit(is_valid, message)

    @Slot(str, str, bool)
    def save_api_key_decision(self, provider, key, should_save):
        if should_save:
            config.save_provider(provider)
            config.save_api_key(key)
        else:
            config.PROVIDER = provider
            config.API_KEY = key

        # Set default model for this provider if current model doesn't belong to it
        provider_model_values = [m["value"] for m in config.PROVIDER_MODELS.get(provider, {}).get("models", [])]
        if not config.DEFAULT_MODEL or config.DEFAULT_MODEL not in provider_model_values:
            default_model = config.get_default_model_for_provider(provider)
            config.DEFAULT_MODEL = default_model
            if should_save:
                config.save_model_name(default_model)

        try:
            self.ai_service = AIService(provider, key, config.DEFAULT_MODEL)
            self.currentModel.emit(config.DEFAULT_MODEL)
            self.currentProvider.emit(provider)
            self.providerModelsLoaded.emit(config.get_models_json(provider))
            self.libraryLoaded.emit(_build_library_json())
        except Exception as e:
            self.apiValidationResult.emit(False, str(e))

    @Slot(str)
    def set_provider(self, provider):
        """Called by JS when user selects a provider on the landing screen."""
        self.providerModelsLoaded.emit(config.get_models_json(provider))

    @Slot(str)
    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)

    @Slot(str)
    def save_model(self, model_name):
        config.save_model_name(model_name)
        if config.API_KEY and config.PROVIDER:
            try:
                self.ai_service = AIService(config.PROVIDER, config.API_KEY, config.DEFAULT_MODEL)
                if self.current_work and self.chat_session:
                    self.chat_session = self.ai_service.create_chat(self.current_work["prompt"])
                self.currentModel.emit(config.DEFAULT_MODEL)
            except Exception as e:
                self.chatError.emit(str(e))

    @Slot(str, str)
    def start_chat_session(self, work_key, sit_key):
        work_data = LIBRARY.get(work_key)
        if not work_data:
            self.chatError.emit("Work not found.")
            return

        sit_data = next((s for s in work_data.get("situations", []) if s.get("key") == sit_key), None)
        if not sit_data:
            self.chatError.emit("Situation not found.")
            return

        # Deep-copy sit_data so nested structures (e.g. chapters list)
        # are not shared with the original LIBRARY dict.
        self.current_work = copy.deepcopy(sit_data)
        assert self.current_work is not None
        self.current_work["_key"] = sit_key
        self.chat_session = None
        self.story_manager = StoryStateManager(self.current_work)

        if self.ai_service:
            try:
                self.chat_session = self.ai_service.create_chat(self.current_work["prompt"])
                self.chatStarted.emit(
                    self.current_work["intro"],
                    self.current_work.get("first_message", "Здравей!"),
                )
                self.chatOptionsUpdated.emit(json.dumps(self.current_work.get("choices", [])))
                # Emit initial progress
                if self.story_manager.has_chapters:
                    self.storyProgressUpdated.emit(json.dumps(self.story_manager.get_progress_info()))
            except Exception as e:
                self.chatError.emit(str(e))

    # Maximum number of characters accepted from the user in a single message.
    # Prevents context-window exhaustion and prompt-injection via huge payloads.
    _MAX_USER_MESSAGE_CHARS = 2000

    # Patterns commonly used in prompt-injection attempts
    _INJECTION_RE = re.compile(
        r"(ignore\s+(all\s+)?previous\s+instructions"
        r"|system\s*prompt"
        r"|you\s+are\s+now"
        r"|\boverride\b"
        r"|\breset\b.*\binstructions\b)",
        re.IGNORECASE,
    )

    def _track_worker(self, worker) -> None:
        """Keep a strong ref to *worker* and auto-remove it when finished."""
        self._active_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))

    def _cleanup_worker(self, worker) -> None:
        """Remove a finished worker from the active list."""
        with contextlib.suppress(ValueError):
            self._active_workers.remove(worker)

    @Slot(str)
    def send_user_message(self, text):
        if not self.ai_service or not self.chat_session:
            self.chatError.emit("Няма активна сесия.")
            return

        # Double-send guard: ignore if a worker is already running
        if self.worker is not None and self.worker.isRunning():
            return

        # Validate and cap input length
        if not text or not text.strip():
            return
        if len(text) > self._MAX_USER_MESSAGE_CHARS:
            text = text[: self._MAX_USER_MESSAGE_CHARS]
            logging.warning("User message truncated to %d characters", self._MAX_USER_MESSAGE_CHARS)

        # Basic prompt-injection defence: strip known attack patterns
        text = self._INJECTION_RE.sub("", text).strip()
        if not text:
            return

        self.loadingStateChanged.emit(True)

        # Build context injection from story state
        context = ""
        if self.story_manager and self.story_manager.has_chapters:
            context = self.story_manager.build_context_injection()

        self.worker = AIChatWorker(self.ai_service, self.chat_session, text, context)
        self.worker.response_signal.connect(self._on_chat_response_worker)
        self.worker.error_signal.connect(self._on_chat_error_worker)
        self.worker.overload_signal.connect(self._on_chat_overload_worker)
        self._track_worker(self.worker)
        self.worker.start()

    def _emit_reply_messages(self, reply):
        """Emit chatMessageReceived for each message in the reply."""
        if self.current_work is None:
            return
        for msg in _format_reply_messages(reply, self.current_work["character"]):
            self.chatMessageReceived.emit(json.dumps(msg))

    def _emit_ended(self, reply):
        """Emit chatEnded with the final narrative text."""
        if isinstance(reply, list):
            self.chatEnded.emit("\n\n".join(msg.get("text", "") for msg in reply))
        else:
            self.chatEnded.emit(str(reply))

    @Slot(dict)
    def _on_chat_response_worker(self, data):
        self.loadingStateChanged.emit(False)

        # Validate & sanitize against story state
        if self.story_manager and self.story_manager.has_chapters:
            data = validate_story_response(
                data,
                state=self.story_manager.get_state(),
                chapter=self.story_manager.current_chapter(),
                is_last_chapter=self.story_manager.is_last_chapter(),
            )
            # Record the turn so state updates
            self.story_manager.record_turn(data)

        reply = data.get("reply", "")
        options = data.get("options", [])
        ended = data.get("ended", False)
        chapter_ended = data.get("_chapter_ended", False)

        if ended:
            self._emit_ended(reply)
        elif chapter_ended:
            self._emit_reply_messages(reply)
            story_manager = self.story_manager
            ai_service = self.ai_service
            current_work = self.current_work
            if story_manager is None or ai_service is None or current_work is None:
                return
            advanced = story_manager.advance_chapter()
            if advanced:
                next_ch = story_manager.current_chapter()
                title = next_ch.title if next_ch else ""
                self.chapterTransition.emit(title)
                # Create a new chat session for the next chapter
                try:
                    self.chat_session = ai_service.create_chat(current_work["prompt"])
                except Exception as e:
                    self.chatError.emit(str(e))
                    return
                self.storyProgressUpdated.emit(json.dumps(story_manager.get_progress_info()))
                self.chatOptionsUpdated.emit(json.dumps(options))
            else:
                # No more chapters — story is over
                self._emit_ended(reply)
        else:
            self._emit_reply_messages(reply)
            self.chatOptionsUpdated.emit(json.dumps(options))
            # Update progress
            if self.story_manager and self.story_manager.has_chapters:
                self.storyProgressUpdated.emit(json.dumps(self.story_manager.get_progress_info()))

    @Slot(str)
    def _on_chat_error_worker(self, message):
        self.loadingStateChanged.emit(False)
        self.chatError.emit(message)

    @Slot()
    def _on_chat_overload_worker(self):
        self.loadingStateChanged.emit(False)
        self.chatOverloaded.emit()


# ================== MAIN APP ==================


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LiteraPlay - Интерактивна Литература")
        self.setMinimumSize(940, 760)

        # WebEngine View
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # Setup WebChannel
        self.channel = QWebChannel()
        self.backend = BackendBridge(self)
        self.channel.registerObject("backend", self.backend)
        self.browser.page().setWebChannel(self.channel)

        # Load UI
        url = QUrl.fromLocalFile(str(UI_PATH.resolve()))
        self.browser.load(url)

    def closeEvent(self, event):
        """Ensure running QThread workers are stopped before exit."""
        for worker in list(self.backend._active_workers):
            if worker is not None and worker.isRunning():
                worker.quit()
                worker.wait(3000)
        super().closeEvent(event)


def main():
    """Application entry point (referenced by pyproject.toml console_scripts)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
