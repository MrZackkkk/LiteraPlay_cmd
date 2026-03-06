# LiteraPlay

Talk to characters from Bulgarian literary classics.
Pick a novel, step into a scene, and have a real conversation — powered by the AI provider of your choice.

Built with PySide6 and Qt WebEngine. Works with OpenAI, Google Gemini, and Anthropic Claude.

<br>

## Get started

```bash
git clone https://github.com/MrZackkkk/LiteraPlay_cmd.git
cd LiteraPlay_cmd
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

On first launch, pick your AI provider, paste an API key, and you're in.

<br>

## What's inside

Three works, multiple scenes each:

**Под игото** — Иван Вазов · **Немили-недраги** — Иван Вазов · **Тютюн** — Димитър Димов

Characters stay in-period, in-character, and react to your choices.
Each scene tracks chapter progress, mood, location, and trust.
You can follow the canonical plot or go off-script.

<br>

## Configuration

Everything is optional. The app asks on first run and saves to `.env`:

```env
LITERAPLAY_PROVIDER=gemini
LITERAPLAY_API_KEY=your-key-here
LITERAPLAY_MODEL=gemini-2.5-flash
```

Supported providers: `openai` · `gemini` · `anthropic`

If you have an old `GOOGLE_API_KEY` in `.env`, it still works.

<br>

## Development

```bash
pip install -e ".[dev]"
```

```bash
PYTHONPATH=src pytest tests/ -v        # tests
ruff check src tests                   # lint
ruff format src tests                  # format
```

<br>

## License

Educational use.
