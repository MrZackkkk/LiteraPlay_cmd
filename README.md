# LiteraPlay - Interactive Literature

LiteraPlay is a Python-based desktop application that brings classic characters from Bulgarian literature to life through interactive AI-powered conversations. Built with CustomTkinter and Google's Gemini AI, the application allows users to immerse themselves in famous literary scenes and role-play with iconic characters.

## Features

* **Interactive Chat Interface:** A modern, dark-themed GUI built with CustomTkinter.
* **AI-Powered Characters:** Integrates with Google's Gemini API (`gemini-flash-latest`) to generate context-aware, in-character responses.
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


*Note: Key dependencies include `customtkinter`, `google-genai`, and `python-dotenv`.*

## Configuration

1. Create a `.env` file in the root directory of the project.
2. Add your Google API key to the file using the following format:
```env
GOOGLE_API_KEY=your_actual_api_key_here

```


The application will automatically load this key at runtime.

## Usage

### Running the Application

To start the main application:

```bash
python main.py

```

Upon launching, select a literary work from the main menu to begin a session. You can choose from suggested responses or type your own messages.

### Checking Available Models

A utility script is provided to verify your API connection and list available Gemini models:

```bash
python check_models.py

```

## Project Structure

* `main.py`: The entry point of the application. Handles the GUI setup, application loop, threading for AI requests, and API communication.
* `data.py`: Contains the literary database, including character prompts, introductory texts, and scenario-specific rules.
* `check_models.py`: A diagnostic script to authenticate with the API and list accessible models.
* `.env`: (User created) Stores sensitive configuration like the API key.

## Technical Details

The application uses `threading` to ensure the GUI remains responsive while waiting for API responses. It implements a retry mechanism for handling API rate limits (error 429) and isolates the character logic using strict system instructions to prevent the AI from breaking character or assuming the user's role.