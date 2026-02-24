import sys
import json
import traceback
from pathlib import Path

# Allow direct execution from IDEs
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QUrl, QObject, Slot, Signal, QThread

from literaplay import config
from literaplay.ai_service import AIService, validate_api_key_with_available_sdk
from literaplay.data import LIBRARY
from literaplay.response_parser import parse_ai_json_response

UI_PATH = Path(__file__).parent / "ui" / "index.html"

# ================== WORKER THREAD ==================

class AIChatWorker(QThread):
    response_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, ai_service, chat_session, user_text):
        super().__init__()
        self.ai_service = ai_service
        self.chat_session = chat_session
        self.user_text = user_text

    def run(self):
        try:
            response_text = self.ai_service.send_message(self.chat_session, self.user_text)

            # Parse response
            data = parse_ai_json_response(response_text)
            if data and isinstance(data, dict):
                self.response_signal.emit({
                    "reply": data.get("reply", response_text),
                    "options": data.get("options", [])
                })
            else:
                self.response_signal.emit({
                    "reply": response_text,
                    "options": []
                })
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

class BackendBridge(QObject):
    """Bridge between JS frontend and Python backend."""
    
    # Signals to JS
    apiValidationResult = Signal(bool, str)
    libraryLoaded = Signal(str)
    chatMessageReceived = Signal(str)  # JSON string {sender, text, isUser, isSystem}
    chatOptionsUpdated = Signal(str)  # JSON string — QWebChannel cannot serialize Python lists
    chatStarted = Signal(str, str) # intro, first_message
    chatError = Signal(str)
    loadingStateChanged = Signal(bool)

    def __init__(self, app_window):
        super().__init__()
        self.app_window = app_window
        
        self.ai_service = None
        self.chat_session = None
        self.current_work = None
        self.worker = None
        self.api_worker = None
        
        if config.API_KEY:
            try:
                self.ai_service = AIService(config.API_KEY, config.DEFAULT_MODEL)
                print("AIService Initialized.")
            except Exception as e:
                print(f"Error init AIService: {e}")

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

    def _on_api_validation_worker_done(self, is_valid, message):
        # We are now executing in the main thread (thanks to default AutoConnection acting as Queued across threads)
        # But to be absolutely safe with QWebChannel, we defer the emit to the next event loop cycle
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.apiValidationResult.emit(is_valid, message))

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

    @Slot(str)
    def start_chat_session(self, work_key):
        self.current_work = LIBRARY[work_key]
        self.chat_session = None
        
        if self.ai_service:
            try:
                self.chat_session = self.ai_service.create_chat(self.current_work['prompt'])
                self.chatStarted.emit(self.current_work['intro'], self.current_work.get('first_message', 'Здравей!'))
                self.chatOptionsUpdated.emit(json.dumps(self.current_work.get('choices', [])))
            except Exception as e:
                self.chatError.emit(str(e))

    @Slot(str)
    def send_user_message(self, text):
        print(f"[DEBUG] send_user_message called with: {text!r}")
        if not self.ai_service or not self.chat_session:
            print("[DEBUG] No active ai_service or chat_session!")
            self.chatError.emit("Няма активна сесия.")
            return

        self.loadingStateChanged.emit(True)

        self.worker = AIChatWorker(self.ai_service, self.chat_session, text)
        self.worker.response_signal.connect(self._on_chat_response_worker)
        self.worker.error_signal.connect(self._on_chat_error_worker)
        self.worker.start()

    def _on_chat_response_worker(self, data):
        reply = data.get('reply', '')
        options = data.get('options', [])
        print(f"[DEBUG] AI response received. Reply length: {len(reply)}, Options: {options}")
        
        from PySide6.QtCore import QTimer
        def trigger_ui():
            print("[DEBUG] trigger_ui fired — pushing to JS via runJavaScript")
            self.loadingStateChanged.emit(False)

            # WORKAROUND: QWebChannel signals don't reliably deliver to JS,
            # so we call JS functions directly via runJavaScript instead.
            page = self.app_window.browser.page()
            msg_json = json.dumps({"sender": self.current_work['character'], "text": reply, "isUser": False, "isSystem": False}, ensure_ascii=False)
            opts_json = json.dumps(options, ensure_ascii=False)
            # Escape backticks/backslashes for JS template safety
            safe_msg = msg_json.replace('\\', '\\\\').replace('`', '\\`')
            safe_opts = opts_json.replace('\\', '\\\\').replace('`', '\\`')
            js_code = f"handleChatMessageJson(`{safe_msg}`); renderChatOptions(`{safe_opts}`);"
            page.runJavaScript(js_code)
            print("[DEBUG] runJavaScript executed successfully")
            
        QTimer.singleShot(0, trigger_ui)

    def _on_chat_error_worker(self, message):
        print(f"[DEBUG] AI error: {message}")
        from PySide6.QtCore import QTimer
        def trigger_error():
            self.loadingStateChanged.emit(False)
            # WORKAROUND: Call JS directly instead of using QWebChannel signal
            page = self.app_window.browser.page()
            msg_json = json.dumps({"sender": "System", "text": "Грешка: " + message, "isUser": False, "isSystem": True}, ensure_ascii=False)
            safe_msg = msg_json.replace('\\', '\\\\').replace('`', '\\`')
            page.runJavaScript(f"handleChatMessageJson(`{safe_msg}`);")
            
        QTimer.singleShot(0, trigger_error)


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
