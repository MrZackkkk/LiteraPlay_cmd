import os
from dotenv import load_dotenv
import customtkinter as ctk

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-2.0-flash"

# UI Configuration
WINDOW_SIZE = "600x800"
APPEARANCE_MODE = "Dark"
TITLE = "LiteraPlay - Интерактивна Литература"

# Fonts
FONT_TITLE = ("Roboto", 24, "bold")
FONT_HEADER = ("Roboto", 16, "bold")
FONT_BODY = ("Arial", 14)
FONT_SMALL = ("Arial", 12)
FONT_TINY = ("Arial", 10)

# Colors
COLOR_USER_BUBBLE = "#1F6AA5"
COLOR_AI_BUBBLE = "#333333"
COLOR_AVATAR_USER = "#1F6AA5"
COLOR_AVATAR_AI = "#444444"
COLOR_BG_CARD = "transparent"
COLOR_BORDER_CARD = "#444444"

def setup_appearance():
    ctk.set_appearance_mode(APPEARANCE_MODE)
