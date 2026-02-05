import customtkinter as ctk
import google.generativeai as genai
import threading
import os
import warnings
from dotenv import load_dotenv

# --- 0. ПОЧИСТВАНЕ НА ТЕРМИНАЛА ---
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. НАСТРОЙКИ И СИГУРНОСТ ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("!!! ГРЕШКА: Не е намерен GOOGLE_API_KEY в .env файла!")
else:
    genai.configure(api_key=API_KEY)

# --- 2. СЦЕНАРИЙ ---
SCENARIO = {
    "work": "Немили-недраги",
    "character_name": "Македонски",
    "player_role": "Бръчков",
    "intro_text": "Кръчмата на Знаменосеца в Браила. Мирише на евтино вино и патриотизъм.",
    "system_instruction": """
    Ти си Македонски от повестта 'Немили-недраги' на Иван Вазов.
    Ти си хъш - смел, гръмогласен, патриот, но и комарджия. 
    Говори на старовремски български диалект.
    Твоята цел е да надъхаш младия Бръчков (играча).
    Отговаряй стегнато, не пиши дълги фермани.
    """,
    "predefined_choices": [
        "Добър вечер, братя хъшове!",
        "Какво ново отсам Дунава?",
        "(Сядам мълчаливо и поръчвам вино)"
    ]
}

# --- 3. ГРАФИЧЕН ИНТЕРФЕЙС ---
class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Литературен Чат: {SCENARIO['character_name']}")
        self.geometry("600x750")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.chat_history = []
        
        # --- ВАЖНАТА ПРОМЯНА ТУК ---
        # Сменихме модела на 'lite', който има по-добри квоти
        if API_KEY:
            try:
                self.model = genai.GenerativeModel(
                    model_name='gemini-2.0-flash-lite-preview-09-2025', 
                    system_instruction=SCENARIO['system_instruction']
                )
                self.chat_session = self.model.start_chat(history=[])
            except Exception as err:
                print(f"Грешка при зареждане на модела: {err}")
                self.model = None

        # --- ЕЛЕМЕНТИ ---
        self.header = ctk.CTkLabel(self, text=f"{SCENARIO['character_name']}", font=("Roboto", 24, "bold"))
        self.header.pack(pady=(15, 5))

        self.sub_header = ctk.CTkLabel(self, text=SCENARIO['intro_text'], text_color="gray")
        self.sub_header.pack(pady=(0, 10))

        # Чат зона
        self.chat_frame = ctk.CTkScrollableFrame(self, width=550, height=450)
        self.chat_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # Бутони с подсказки
        self.options_frame = ctk.CTkFrame(self, height=100, fg_color="transparent")
        self.options_frame.pack(pady=5, padx=10, fill="x")
        self.load_options()

        # Поле за писане
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=10, fill="x")

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Напиши нещо на героя...")
        self.entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.send_btn = ctk.CTkButton(self.input_frame, text="Изпрати", width=100, command=self.send_message)
        self.send_btn.pack(side="right", padx=10)

        # Първа реплика
        self.add_message(SCENARIO['character_name'], "Ехее, кой влиза! Ела при нас, момче! Гладни ли сте?", is_user=False)

    def load_options(self):
        for text in SCENARIO['predefined_choices']:
            btn = ctk.CTkButton(self.options_frame, text=text, 
                                command=lambda t=text: self.send_message(t),
                                fg_color="#2E8B57", hover_color="#20603D")
            btn.pack(pady=3, padx=5, fill="x")

    def add_message(self, sender, text, is_user=True):
        align = "e" if is_user else "w"
        color = "#1F6AA5" if is_user else "#333333"
        
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5)
        
        label_name = ctk.CTkLabel(msg_frame, text=sender, font=("Arial", 10), text_color="silver")
        label_name.pack(anchor=align, padx=15)

        bubble = ctk.CTkLabel(msg_frame, text=text, fg_color=color, corner_radius=15, 
                              wraplength=400, padx=15, pady=10, font=("Arial", 14))
        bubble.pack(anchor=align, padx=10)
        
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def send_message(self, text=None):
        if text is None:
            text = self.entry.get()
        if not text.strip(): return

        self.add_message("Ти", text, is_user=True)
        self.entry.delete(0, 'end')
        self.send_btn.configure(state="disabled")

        threading.Thread(target=self.get_ai_response, args=(text,)).start()

    def get_ai_response(self, user_text):
        if not self.model:
            self.after(0, lambda: self.update_ui("Грешка: Моделът не е зареден."))
            return

        try:
            response = self.chat_session.send_message(user_text)
            ai_reply = response.text
            self.after(0, lambda: self.update_ui(ai_reply))
        except Exception as e:
            error_msg = f"Грешка връзка: {e}"
            self.after(0, lambda: self.update_ui(error_msg))

    def update_ui(self, text):
        self.add_message(SCENARIO['character_name'], text, is_user=False)
        self.send_btn.configure(state="normal")

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()