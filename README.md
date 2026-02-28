# 📚 LiteraPlay — Interactive Bulgarian Literature

**LiteraPlay** is a desktop application that brings classic Bulgarian literary characters to life through AI-powered, interactive conversations. Select a novel, step into a famous scene, and role-play with iconic characters — all powered by Google's Gemini AI.

Built with **PySide6 / Qt WebEngine** for a modern hybrid UI and backed by the **Google Gemini** generative AI API.

---

## ✨ Features

- **Immersive Role-Play** — Step into pivotal moments from Bulgarian literature and converse with characters who stay faithful to their source material.
- **AI-Powered Dialogue** — Gemini generates context-aware, in-character responses with strict factual accuracy and character consistency.
- **Hybrid Desktop UI** — A native PySide6 window hosts a polished HTML/CSS/JS frontend via Qt WebChannel, combining desktop reliability with web-grade aesthetics.
- **Threaded AI Requests** — Chat and API-key verification run on background `QThread` workers, keeping the UI responsive.
- **Dynamic Choice System** — Pre-defined dialogue options guide the conversation alongside a free-text input field.
- **Text Context Injection** — Full novel text can be loaded (`.txt`) and sent to the AI as factual context for grounded responses.
- **Automatic Rate-Limit Retry** — Handles HTTP 429 errors with exponential back-off (up to 5 retries).

---

## 📖 Supported Literary Works

| # | Work | Author | Character | Scene |
|---|------|--------|-----------|-------|
| 1 | **Под игото** *(Under the Yoke)* | Иван Вазов | **Бай Марко** | A stormy night — an intruder in the barn |
| 2 | **Немили-недраги** | Иван Вазов | **Македонски** | The flag-bearer's tavern in Braila |
| 3 | **Тютюн** *(Tobacco)* | Димитър Димов | **Ирина** | The Nicotiana salon |

> **Note:** *Под игото* includes full novel text loaded from `books/` for enhanced AI grounding. The other scenarios use prompt-only context.

---

## 🛠 Prerequisites

- **Python 3.10+**
- A **Google API Key** with access to the Gemini API

---

## 🚀 Installation

1. **Clone** the repository:
   ```bash
   git clone https://github.com/MrZackkkk/LiteraPlay_cmd.git
   cd LiteraPlay_cmd
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies

| Package | Purpose |
|---------|---------|
| `PySide6 >=6.6.0` | Qt 6 bindings — native window + WebEngine |
| `google-genai >=1.0.0` | Google Gemini AI SDK |
| `python-dotenv` | `.env` file loading (optional — fallback built-in) |

---

## ⚙️ Configuration

LiteraPlay reads its API key from an environment variable. You can configure it in two ways:

### Option A — `.env` file (recommended)
Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_actual_api_key_here
```

### Option B — In-app prompt
If no key is found at startup, the app will display an API-key entry screen where you can paste and verify your key. You'll be asked whether to persist it to `.env`.

---

## ▶️ Running the Application

```bash
# Set the source directory on your Python path
# PowerShell
$env:PYTHONPATH = "src"
# Bash
export PYTHONPATH=src

# Launch LiteraPlay
python -m literaplay.main
```

On launch you will see:

1. **API Key Screen** — if no key is stored (enter and verify your key).
2. **Library Menu** — pick a literary work to begin.
3. **Chat Screen** — role-play with the character using suggested options or free text.


---

## 📁 Project Structure

```
LiteraPlay_cmd/
├── books/                          # Source novel texts (.txt)
├── src/
│   └── literaplay/
│       ├── __init__.py
│       ├── main.py                 # Entry point — QMainWindow, WebChannel bridge, QThread workers
│       ├── ai_service.py           # AIService class — chat creation, message sending + retry
│       ├── config.py               # Environment config — API key, model name
│       ├── data.py                 # LIBRARY dict — scenarios, character prompts, novel text loading
│       ├── response_parser.py      # JSON response parser — handles plain, fenced, and embedded JSON
│       ├── story_state.py          # Story state tracking — chapters, turns, context injection
│       ├── dependency_compat.py    # Fallback implementations for python-dotenv
│       └── ui/
│           ├── index.html          # Frontend markup (API screen, menu, chat)
│           ├── style.css           # Styles — dark theme, glassmorphism, animations
│           └── script.js           # Frontend logic — QWebChannel signals, DOM rendering
├── tests/                          # Pytest test suites
│   ├── test_ai_service.py
│   ├── test_data.py
│   ├── test_dependency_compat.py
│   ├── test_response_parser.py
│   └── test_story_state.py
├── requirements.txt
├── pyrightconfig.json
└── .gitignore
```

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────┐
│               PySide6 MainWindow            │
│  ┌───────────────────────────────────────┐  │
│  │       QWebEngineView (Chromium)       │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   HTML / CSS / JS  (ui/)        │  │  │
│  │  │   Renders screens, chat bubbles │  │  │
│  │  └──────────┬──────────────────────┘  │  │
│  └─────────────┼─────────────────────────┘  │
│       QWebChannel (signals/slots)           │
│  ┌─────────────┴─────────────────────────┐  │
│  │         BackendBridge (QObject)        │  │
│  │  • verify_api_key()                   │  │
│  │  • start_chat_session()               │  │
│  │  • send_user_message()                │  │
│  └─────────────┬─────────────────────────┘  │
│       QThread workers (async AI calls)      │
│  ┌─────────────┴─────────────────────────┐  │
│  │         AIService (google-genai)       │  │
│  │  • create_chat()                      │  │
│  │  • send_message() + retry             │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 🧪 Testing

```bash
# Run the full test suite
$env:PYTHONPATH = "src"        # PowerShell
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src/literaplay --cov-report=term-missing
```

---

## 🔧 Troubleshooting

### `ModuleNotFoundError: No module named 'literaplay'`
The package lives under `src/literaplay`. Always run with `src` on your `PYTHONPATH` and use the `-m` flag:
```bash
$env:PYTHONPATH = "src"
python -m literaplay.main
```

### `ModuleNotFoundError: No module named 'PySide6'`
Install the project dependencies:
```bash
pip install -r requirements.txt
```

### API key errors / `429 Resource Exhausted`
- The app automatically retries on 429 errors with exponential back-off, but sustained overload may require waiting or switching to a different model.
- The default model is configured in `config.py` (`DEFAULT_MODEL`).

---

## 📄 License

This project is provided for educational purposes.
