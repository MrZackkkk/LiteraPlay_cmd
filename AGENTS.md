# AGENTS.md — LiteraPlay Developer Guide

## Project Overview

**LiteraPlay** is an interactive Bulgarian literature desktop app. Users pick a classic novel, enter a scene, and role-play with AI-powered literary characters via Google Gemini. The UI is a PySide6 native window hosting a Chromium-based web frontend (`QWebEngineView`) — Python handles AI and state; HTML/CSS/JS handles rendering.

**Language:** Python 3.10+ · **UI toolkit:** PySide6 + Qt WebEngine · **AI backend:** Google Gemini (dual SDK support)

---

## Architecture

```
PySide6 QMainWindow
 └─ QWebEngineView (Chromium)
     └─ HTML / CSS / JS   ←── QWebChannel ──→  BackendBridge (QObject)
                                                  │
                                           QThread workers
                                                  │
                                              AIService
                                           (google-genai SDK)
```

- **Frontend** (`src/literaplay/ui/`): `index.html`, `style.css`, `script.js` — renders API-key screen, library menu, and chat. Communicates with Python via `QWebChannel`.
- **BackendBridge** (`main.py`): QObject exposed to JS. Handles `verify_api_key()`, `start_chat_session()`, `send_user_message()`. Dispatches work to `QThread` workers so the UI never blocks.
- **AIService** (`ai_service.py`): Initialises the Gemini client via the `google-genai` SDK, creates chat sessions with system instructions, sends messages with exponential-backoff retry on 429 errors.
- **Data layer** (`data.py`): `LIBRARY` dictionary defining each literary scenario — title, character, prompt, initial choices, and optional full-text context loaded from `books/`.

---

## Project Structure

```
LiteraPlay_cmd/
├── src/literaplay/           # Main package (all source lives here)
│   ├── main.py               # Entry point — MainWindow, BackendBridge, QThread workers
│   ├── ai_service.py         # AIService class, dual-SDK init, retry logic
│   ├── config.py             # Env config — API key, model name, UI defaults
│   ├── data.py               # LIBRARY dict — scenarios, character prompts, text loading
│   ├── response_parser.py    # JSON response parser (plain / fenced / embedded)
│   ├── dependency_compat.py  # Fallback implementations for python-dotenv
│   ├── pdf_loader.py         # PDF text extraction (pypdf)
│   ├── check_models.py       # CLI utility — list available Gemini models
│   └── ui/
│       ├── index.html        # Frontend markup (3 screens: API key, menu, chat)
│       ├── style.css         # Dark theme, glassmorphism, animations
│       └── script.js         # Frontend logic, QWebChannel signals, DOM rendering
├── books/                    # Source novel texts (.txt)
├── tests/                    # Pytest test suites (one per module)
├── requirements.txt          # PySide6, google-genai, python-dotenv, pypdf
├── pyrightconfig.json        # Pyright type-checker config (extraPaths: src)
└── .env                      # GOOGLE_API_KEY (not tracked in git)
```

---

## Developer Workflows

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Create .env with: GOOGLE_API_KEY=your_key_here
```

### Run the app
```bash
$env:PYTHONPATH = "src"          # PowerShell (or export PYTHONPATH=src)
python -m literaplay.main
```

### Run tests
```bash
$env:PYTHONPATH = "src"
pytest tests/ -v
pytest tests/ --cov=src/literaplay --cov-report=term-missing
```

### List available Gemini models
```bash
python -m literaplay.check_models
```

### Important: PYTHONPATH
The package lives under `src/literaplay`. Always set `PYTHONPATH=src` (or configure your IDE's extra paths) before running or testing.

---

## Patterns & Conventions

### Adding a new literary work
Add an entry to the `LIBRARY` dict in `data.py`:
```python
"new_key": {
    "title": "Заглавие",
    "character": "Герой",
    "color": "#RRGGBB",
    "intro": "Scene intro shown before chat starts",
    "first_message": "Character's opening line",
    "choices": ["Option 1", "Option 2", "Option 3"],
    "prompt": f"""{COMMON_RULES}\n\nYour detailed character prompt...""",
    "pdf_context": ""   # or load_text_content("books/filename.txt")
}
```
The frontend auto-generates the menu card and choice buttons from this data.

### AI response format
The AI is instructed to return JSON: `{"reply": "...", "options": [...]}`. The `response_parser.py` module handles plain JSON, markdown-fenced JSON, and JSON embedded in free text.

### Threading model
All AI calls run on `QThread` workers (`AIChatWorker`, `APIVerifyWorker`). Results are delivered back to the main thread via Qt `Signal`s. **Never** call AI or network APIs on the UI thread.

### Configuration
- **API key**: `GOOGLE_API_KEY` env var, read by `config.py` via `python-dotenv` (with built-in fallback in `dependency_compat.py`).
- **Default model**: `DEFAULT_MODEL` in `config.py` (currently `gemini-3.0-flash-preview`).
- **Rate-limit retry**: up to 5 retries with exponential backoff, handled in `AIService.send_message()`.

---

## Testing

Tests are in `tests/`, one file per module. They use `pytest` with `unittest.mock` for patching SDK calls. Key test files:

| Test file | Covers |
|-----------|--------|
| `test_ai_service.py` | SDK init, chat creation, send_message retry |
| `test_main.py` | BackendBridge and worker threads |
| `test_data.py` | LIBRARY structure validation |
| `test_response_parser.py` | JSON parsing edge cases |
| `test_pdf_loader.py` | PDF extraction |
| `test_pdf_integration.py` | End-to-end PDF context loading |
| `test_dependency_compat.py` | dotenv fallback logic |
| `test_check_models.py` | CLI model listing |

---

## Key Pitfalls

1. **Missing PYTHONPATH** — Running without `PYTHONPATH=src` causes `ModuleNotFoundError: No module named 'literaplay'`.
2. **Qt SDK** — The app requires `PySide6-WebEngine` in addition to `PySide6`. Both are listed in `requirements.txt`.
3. **UI thread safety** — Qt signals/slots handle cross-thread communication. Never manipulate `QWebEngineView` from a worker thread.
4. **API key verification** — Uses a minimal `generate_content("Ping")` call to verify the key is live, falling back to `models.list()` if generation is blocked.
