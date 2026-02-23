# LiteraPlay - Interactive Literature

LiteraPlay is a Python-based desktop application that brings classic characters from Bulgarian literature to life through interactive AI-powered conversations. Built with CustomTkinter and Google's Gemini AI, the application allows users to immerse themselves in famous literary scenes and role-play with iconic characters.

## Features

* **Interactive Chat Interface:** A modern, dark-themed GUI built with CustomTkinter.
* **AI-Powered Characters:** Integrates with Google's Gemini API to generate context-aware, in-character responses.
* **Literary Scenarios:** Pre-configured scenarios with specific roles, settings, and opening lines for characters like Makedonski, Boycho Ognyanov, and Irina.
* **Dynamic Role-Playing:** The AI is instructed to strictly adhere to character constraints, maintain internal logic, and treat the user as a new participant in the scene.
* **Conversation Tools:** Includes pre-defined dialogue options to help users start the conversation, alongside a free-text input field.

## Supported Works

The current version supports the following literary works and characters:

1. **Nemili-nedragi (Ivan Vazov):** Chat with **Makedonski** in the flag-bearer's tavern in Braila.
2. **Pod Igoto (Ivan Vazov):** Encounter **Boycho Ognyanov** hiding in the old mill near Byala Cherkva.
3. **Tyutyun (Dimitar Dimov):** Conversate with **Irina** in the "Nicotiana" salon.

## Prerequisites

* Python 3.8 or higher
* A Google Cloud Project with the Gemini API enabled
* A valid Google API Key

## Installation

1. Clone the repository to your local machine.
2. Install the required dependencies using pip:
```bash
pip install -r requirements.txt
```

*Note: Key dependencies include `customtkinter`, `google-genai`, `pytest`, and `python-dotenv`.*

## Configuration

1. Create a `.env` file in the root directory of the project, or let the graphical UI prompt you on first launch.
2. If manually configuring, add your Google API key to the `.env` file using the following format:
```env
GOOGLE_API_KEY=your_actual_api_key_here
```

## Running the Application

To start the main application dashboard from the module:

```bash
# Before running you must include the source directory in the Python Path or be running from an IDE
$env:PYTHONPATH="src"
python -m literaplay.main
```

Upon launching, select a literary work from the main menu to begin a session. You can choose from suggested responses or type your own messages.

### Checking Available Models

A utility script is provided to verify your API connection and list available Gemini models:

```bash
$env:PYTHONPATH="src"
python -m literaplay.check_models
```

## Project Structure (src layout)

LiteraPlay follows a standard Python package structure using the `/src` and `/tests` abstraction:

* `src/literaplay/main.py`: The entry point of the application. Handles the GUI setup, application loop, threading for AI requests, and API communication.
* `src/literaplay/data.py`: Contains the literary database, including character prompts, introductory texts, and scenario-specific rules.
* `src/literaplay/config.py`: Environment configuration and Theme styling parameters.
* `src/literaplay/ai_service.py`: API abstractions interacting with Gemini.
* `tests/`: Contains module and integration level Pytest suites.

## Testing & Quality Assurance

To execute the unit testing suites manually to ensure core service stability:

```bash
$env:PYTHONPATH="src"

# Run tests
pytest tests/ -v

# Run tests with coverage diagnostics
pytest tests/ --cov=src/literaplay --cov-report=term-missing
```

## Troubleshooting

### ModuleNotFoundError: No module named 'customtkinter'
If you encounter this error, it means the required dependencies are not installed. Please run:
```bash
pip install -r requirements.txt
```

### ModuleNotFoundError: No module named 'literaplay'
Because the app is nested under `src/literaplay`, running scripts directly by filepath (e.g. `python src/literaplay/main.py`) will fail to find absolute package references. Always execute using the python module operator `-m`, e.g. `python -m literaplay.main`, while having `src/` in your `PYTHONPATH`.
