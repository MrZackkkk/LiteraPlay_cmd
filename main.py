import customtkinter as ctk
from google import genai
from google.genai import types
import threading
import queue
from tkinter import messagebox
import os
import time
import traceback
from dotenv import load_dotenv

# ВАЖНО: Тук внасяме данните от другия файл
from data import LIBRARY

# --- 1. НАСТРОЙКИ ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("!!! GRESKA: Ne e nameren GOOGLE_API_KEY v .env faila!")

# --- 2. ПРИЛОЖЕНИЕ ---
class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LiteraPlay - Интерактивна Литература")
        self.geometry("600x800")
        ctk.set_appearance_mode("Dark")
        
        # Настройки на AI
        # Използваме модерен модел по подразбиране
        self.model_name = "gemini-flash-latest" 
        self.client = None
        self.api_configured = False

        if API_KEY:
            try:
                # MODERN CLIENT INITIALIZATION
                self.client = genai.Client(api_key=API_KEY)
                self.api_configured = True
                print("Modern genai.Client configured successfully.")
            except Exception as e:
                print(f"Error init client: {e}")

        if not self.api_configured:
            print("API not configured: missing or invalid GOOGLE_API_KEY")
            try:
                messagebox.showwarning("AI Key", "Няма връзка с AI. Проверете GOOGLE_API_KEY в .env.")
            except Exception:
                pass

        # Основен контейнер за смяна на екрани
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True)

        # Показваме менюто
        self.show_menu()

    # ================== ЕКРАН: МЕНЮ ==================
    def show_menu(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_container, text="Избери произведение", font=("Roboto", 28, "bold"))
        title.pack(pady=(40, 20))

        for key, data in LIBRARY.items():
            card = ctk.CTkFrame(self.main_container, fg_color="transparent", border_width=2, border_color="#444")
            card.pack(pady=10, padx=20, fill="x")

            lbl_title = ctk.CTkLabel(card, text=f"{data['title']}", font=("Arial", 18, "bold"))
            lbl_title.pack(pady=(10, 0))
            
            lbl_char = ctk.CTkLabel(card, text=f"Герой: {data['character']}", text_color="gray")
            lbl_char.pack(pady=(0, 10))

            btn = ctk.CTkButton(card, text="Започни разговор", 
                                fg_color=data['color'], hover_color="#333",
                                command=lambda k=key: self.start_chat(k))
            btn.pack(pady=(0, 15))

    # ================== ЕКРАН: ЧАТ ==================
    def start_chat(self, work_key):
        self.current_work = LIBRARY[work_key]
        
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Инициализация на сесията
        self.chat_history = []
        self.chat = None
        self.request_queue = queue.Queue()

        if self.api_configured:
            try:
                self.init_chat_session()
            except Exception as e:
                print(f"Session error: {e}")
                traceback.print_exc()
                self.update_ui(f"ГРЕШКА: {e}")

        threading.Thread(target=self.request_worker, daemon=True).start()

        # --- UI Компоненти ---
        header_frame = ctk.CTkFrame(self.main_container, height=50, fg_color="#222")
        header_frame.pack(fill="x", side="top")

        btn_back = ctk.CTkButton(header_frame, text="⬅ Меню", width=60, 
                                 fg_color="transparent", border_width=1, 
                                 command=self.show_menu)
        btn_back.pack(side="left", padx=10, pady=10)

        lbl_header = ctk.CTkLabel(header_frame, text=f"{self.current_work['character']}", 
                                  font=("Roboto", 16, "bold"))
        lbl_header.pack(side="left", padx=10)

        lbl_intro = ctk.CTkLabel(self.main_container, text=self.current_work['intro'], text_color="gray", wraplength=500)
        lbl_intro.pack(pady=10)

        self.chat_frame = ctk.CTkScrollableFrame(self.main_container)
        self.chat_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.options_frame = ctk.CTkFrame(self.main_container, height=80, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=10, pady=5)
        
        for text in self.current_work['choices']:
            btn = ctk.CTkButton(self.options_frame, text=text, 
                                fg_color=self.current_work['color'], height=25,
                                command=lambda t=text: self.send_message(t))
            btn.pack(pady=2, fill="x")

        input_frame = ctk.CTkFrame(self.main_container)
        input_frame.pack(pady=10, padx=10, fill="x")

        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Напиши нещо...")
        self.entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        btn_send = ctk.CTkButton(input_frame, text="➤", width=40, command=self.send_message)
        btn_send.pack(side="right", padx=10)

        start_msg = self.current_work.get('first_message', 'Здравей!')
        self.add_message(self.current_work['character'], start_msg, is_user=False)

    def init_chat_session(self):
        """Initializes the chat using the modern Google GenAI Client."""
        try:
            # Create the chat config
            # Note: System instructions in the new SDK are often passed in the config or at create time
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=self.current_work['prompt']
            )
            
            # Create the chat session
            self.chat = self.client.chats.create(
                model=self.model_name,
                config=config,
                history=[]
            )
            print(f"Chat session started with model: {self.model_name}")
            
        except Exception as e:
            print(f"Failed to start chat session: {e}")
            traceback.print_exc()
            self.update_ui("Няма връзка с AI. Грешка при стартиране.")

    def add_message(self, sender, text, is_user=True):
        align = "e" if is_user else "w"
        color = "#1F6AA5" if is_user else "#333333"
        
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5)
        
        name_lbl = ctk.CTkLabel(msg_frame, text=sender, font=("Arial", 10), text_color="silver")
        name_lbl.pack(anchor=align, padx=15)

        bubble = ctk.CTkLabel(msg_frame, text=text, fg_color=color, corner_radius=15, 
                              wraplength=400, padx=15, pady=10, font=("Arial", 14))
        bubble.pack(anchor=align, padx=10)
        
        self.main_container.after(10, lambda: self._scroll_down())

    def _scroll_down(self):
        try: self.chat_frame._parent_canvas.yview_moveto(1.0)
        except: pass

    def send_message(self, text=None):
        if text is None: text = self.entry.get()
        if not text.strip(): return

        self.add_message("Ти", text, is_user=True)
        self.entry.delete(0, 'end')
        self.request_queue.put(text)

    def request_worker(self):
        while True:
            text = self.request_queue.get()
            if text: self.get_ai_response(text)

    def get_ai_response(self, user_text):
        if not self.chat:
            self.update_ui("Няма активна AI сесия.")
            return

        max_retries = 3
        retry_delay = 2 

        for attempt in range(max_retries):
            try:
                # Modern SDK call
                response = self.chat.send_message(user_text)
                self.update_ui(response.text)
                return  # Success

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg and attempt < max_retries - 1:
                    self.update_ui(f"Претоварено. Опит {attempt + 1} след {retry_delay} сек...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.update_ui(f"Грешка: {e}")
                    print(f"API Error: {e}")
                    break

    def update_ui(self, text):
        self.main_container.after(0, lambda: self.add_message(self.current_work['character'], text, is_user=False))

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()