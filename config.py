import os
from dotenv import load_dotenv
import customtkinter as ctk

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-2.0-flash"  # Updated to a stable model name, or keep what was there

# UI Configuration
WINDOW_SIZE = "600x800"
APPEARANCE_MODE = "Dark"
TITLE = "LiteraPlay - Интерактивна Литература"

# Colors
COLOR_USER_BUBBLE = "#1F6AA5"
COLOR_AI_BUBBLE = "#333333"

def setup_appearance():
    ctk.set_appearance_mode(APPEARANCE_MODE)
