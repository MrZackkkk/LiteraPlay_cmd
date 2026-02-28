import contextlib
import json
import logging
import sys
import traceback
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
from literaplay.ai_service import AIService, validate_api_key_with_available_sdk
from literaplay.data import LIBRARY
from literaplay.response_parser import parse_ai_json_response, validate_story_response
from literaplay.story_state import StoryStateManager

UI_PATH = Path(__file__).parent / "ui" / "index.html"

# ================== WORKER THREAD ==================


class AIChatWorker(QThread):
    response_signal = Signal(dict)
    error_signal = Signal(str)

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
            traceback.print_exc()
            self.error_signal.emit(str(e))


class APIVerifyWorker(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, key: str):
        super().__init__()
        self.key = key

    def run(self):
        is_valid, message = validate_api_key_with_available_sdk(self.key)
        self.finished_signal.emit(is_valid, message)


# ================== BACKEND BRIDGE ==================


def _format_reply_messages(reply, default_character: str) -> list[dict]:
    """Normalise a reply (list-of-dicts or plain string) into message dicts."""
    if isinstance(reply, list):
        return [
            {
                "sender": msg.get("character", default_character),
                "text": msg.get("text", ""),
                "isUser": False,
                "isSystem": False,
            }
            for msg in reply
        ]
    return [
        {
            "sender": default_character,
            "text": str(reply),
            "isUser": False,
            "isSystem": False,
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
    chatEnded = Signal(str)  # final narrative text
    loadingStateChanged = Signal(bool)
    storyProgressUpdated = Signal(str)  # JSON: chapter_title, turn, progress_pct
    chapterTransition = Signal(str)  # chapter title for transition message

    def __init__(self, app_window):
        super().__init__()
        self.app_window = app_window

        self.ai_service = None
        self.chat_session = None
        self.current_work = None
        self.worker = None
        self.api_worker = None
        self.story_manager = None

        if config.API_KEY:
            with contextlib.suppress(Exception):
                self.ai_service = AIService(config.API_KEY, config.DEFAULT_MODEL)

    @Slot()
    def request_initial_state(self):
        """Called by JS when the page finishes loading."""
        if config.API_KEY and self.ai_service:
            # Skip straight to menu
            self.libraryLoaded.emit(json.dumps(LIBRARY))
        else:
            # JS stays on API screen by default
            pass

    @Slot(str)
    def verify_api_key(self, key):
        self.api_worker = APIVerifyWorker(key)
        self.api_worker.finished_signal.connect(self._on_api_validation_worker_done)
        self.api_worker.start()

    @Slot(bool, str)
    def _on_api_validation_worker_done(self, is_valid, message):
        self.apiValidationResult.emit(is_valid, message)

    @Slot(str, bool)
    def save_api_key_decision(self, key, should_save):
        if should_save:
            config.save_api_key(key)
        else:
            config.API_KEY = key

        try:
            self.ai_service = AIService(key, config.DEFAULT_MODEL)
            self.libraryLoaded.emit(json.dumps(LIBRARY))
        except Exception as e:
            self.apiValidationResult.emit(False, str(e))

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

        self.current_work = sit_data
        # Store the key inside work data so StoryStateManager can reference it
        self.current_work["_key"] = sit_key
        self.chat_session = None
        self.story_manager = StoryStateManager(self.current_work)

        if self.ai_service:
            try:
                self.chat_session = self.ai_service.create_chat(self.current_work["prompt"])
                self.chatStarted.emit(self.current_work["intro"], self.current_work.get("first_message", "Здравей!"))
                self.chatOptionsUpdated.emit(json.dumps(self.current_work.get("choices", [])))
                # Emit initial progress
                if self.story_manager.has_chapters:
                    self.storyProgressUpdated.emit(json.dumps(self.story_manager.get_progress_info()))
            except Exception as e:
                self.chatError.emit(str(e))

    @Slot(str)
    def send_user_message(self, text):
        if not self.ai_service or not self.chat_session:
            self.chatError.emit("Няма активна сесия.")
            return

        # Double-send guard: ignore if a worker is already running
        if self.worker is not None and self.worker.isRunning():
            return

        self.loadingStateChanged.emit(True)

        # Build context injection from story state
        context = ""
        if self.story_manager and self.story_manager.has_chapters:
            context = self.story_manager.build_context_injection()

        self.worker = AIChatWorker(self.ai_service, self.chat_session, text, context)
        self.worker.response_signal.connect(self._on_chat_response_worker)
        self.worker.error_signal.connect(self._on_chat_error_worker)
        self.worker.start()

    def _emit_reply_messages(self, reply):
        """Emit chatMessageReceived for each message in the reply."""
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
            advanced = self.story_manager.advance_chapter()
            if advanced:
                next_ch = self.story_manager.current_chapter()
                title = next_ch.title if next_ch else ""
                self.chapterTransition.emit(title)
                # Create a new chat session for the next chapter
                try:
                    self.chat_session = self.ai_service.create_chat(self.current_work["prompt"])
                except Exception as e:
                    self.chatError.emit(str(e))
                    return
                self.storyProgressUpdated.emit(json.dumps(self.story_manager.get_progress_info()))
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
        for worker in (self.backend.worker, self.backend.api_worker):
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
