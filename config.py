import os
from dotenv import load_dotenv
import customtkinter as ctk

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-2.0-flash"

# UI Configuration
WINDOW_SIZE = "1000x800" # Wider for sidebars
APPEARANCE_MODE = "Dark"
TITLE = "LiteraPlay - Интерактивна Литература"

# Colors
COLOR_BACKGROUND = "#1a1a1a" # Darker background
COLOR_USER_BUBBLE = "#1F6AA5"
COLOR_AI_BUBBLE = "#333333"
COLOR_SIDEBAR = "#222222"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#aaaaaa"

# Animation
ANIMATION_DURATION_MS = 400

def setup_appearance():
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme("blue")
