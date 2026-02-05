Project: LiteraPlay_cmd — AI assistant guidance

Overview
- This is a small desktop interactive-fiction GUI built with `customtkinter` that drives AI-powered character dialogues.
- UI (`main.py`) reads static content from `data.py` (the `LIBRARY` dict) and uses the Google GenAI client to run a chat-style session.

Key components
- `main.py`: Application entrypoint and UI. Responsible for app/window lifecycle, menus, chat UI, threading, and interaction with the GenAI client.
- `data.py`: Contains the `LIBRARY` dictionary with each work entry. Each entry uses keys: `title`, `author`, `character`, `color`, `intro`, `prompt`, `choices`.
- `check_models.py`: Lightweight helper to list available models (uses an alternate import of the GenAI package). Use it to discover model names.
- `.env` (not tracked): stores `GOOGLE_API_KEY`. The app reads `GOOGLE_API_KEY` with `python-dotenv`.

Why this structure
- Separation of UI (`main.py`) and content (`data.py`) makes it trivial to add works or tweak prompts without touching UI logic.
- The app uses an async-ish design: UI pushes user text into a `queue.Queue`, and a background `request_worker` thread consumes it and calls the AI. Keep heavy work off the UI thread.

Developer workflows
- Install deps and run the app (Windows example):
  - `python -m pip install -r requirements.txt`
  - create a `.env` file containing `GOOGLE_API_KEY=your_key_here`
  - `python main.py`
- List models: `python check_models.py` (check that your environment variable is set). Note: `check_models.py` imports `google.generativeai` while `main.py` uses `google.genai` — both packages are listed in `requirements.txt`.

Patterns & conventions (codebase-specific)
- Data shape: New works must follow the `LIBRARY` entry shape. Example minimal entry to add to `data.py`:

```python
"new_work": {
  "title": "Title",
  "author": "Author",
  "character": "HeroName",
  "color": "#RRGGBB",
  "intro": "Short intro shown in chat header",
  "prompt": """System instruction given to the model (character persona)""",
  "choices": ["Choice 1", "Choice 2"]
}
```

- UI -> AI flow: clicking a choice or pressing Enter calls `send_message()` which enqueues the text. The `request_worker` thread calls `get_ai_response()` which uses `self.chat_session.send_message()` and then `update_ui()` to add the AI reply into the chat area.
- Retry strategy: `get_ai_response()` performs up to 3 retries on errors, doing exponential backoff for rate-limit-like failures (detects '429' in exception text).

Integration notes & pitfalls
- API client setup: `main.py` expects `genai.configure(api_key=API_KEY)` and then builds a `genai.GenerativeModel(...).start_chat(history=[])`. If the API key is missing the UI will still start but will show "Няма връзка с AI." when trying to chat.
- Mixed GenAI imports: `requirements.txt` lists `google-generativeai` and `google-genai`. Be aware: code uses slightly different clients in different files. If you change client imports, run `check_models.py` to verify behavior.
- Threading & UI: all UI updates are scheduled onto the main thread using `self.main_container.after(...)`. Avoid calling Tk methods directly from worker threads.

Quick examples for contributors
- Add a new choice button: append to the `choices` list in the `LIBRARY` entry and the UI will create a button automatically when `start_chat()` runs.
- Change default model: update `self.model_name` in `ChatApp.__init__()` in `main.py` (currently `gemini-1.5-flash`). Use `check_models.py` to list valid alternatives.

Files to inspect for behavior
- [main.py](main.py)
- [data.py](data.py)
- [check_models.py](check_models.py)
- [requirements.txt](requirements.txt)

If something is unclear
- Tell me which part you want expanded (e.g., detailed example of adding a new work, or migration to a single GenAI client). I'll iterate this file.

— End
