import threading
import queue
import time
import traceback
from tkinter import messagebox
import customtkinter as ctk

import config
from ai_service import AIService
from data import LIBRARY

# --- APP SETUP ---
config.setup_appearance()

class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(config.TITLE)
        self.geometry(config.WINDOW_SIZE)
        
        # AI Service Init
        self.ai_service = None
        self.api_configured = False

        if config.API_KEY:
            try:
                self.ai_service = AIService(config.API_KEY, config.DEFAULT_MODEL)
                self.api_configured = True
                print(f"AIService initialized with model: {config.DEFAULT_MODEL}")
            except Exception as e:
                print(f"Error init AIService: {e}")

        if not self.api_configured:
            print("API not configured: missing or invalid GOOGLE_API_KEY")
            try:
                messagebox.showwarning("AI Key", "Няма връзка с AI. Проверете GOOGLE_API_KEY в .env.")
            except Exception:
                pass

        # Main Container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True)

        self.show_menu()

    # ================== SCREEN: MENU ==================
    def show_menu(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.main_container, text="Избери произведение", font=config.FONT_TITLE)
        title.pack(pady=(40, 20))

        for key, data in LIBRARY.items():
            card = ctk.CTkFrame(self.main_container, fg_color=config.COLOR_BG_CARD,
                                border_width=2, border_color=config.COLOR_BORDER_CARD)
            card.pack(pady=10, padx=20, fill="x")

            # Title
            lbl_title = ctk.CTkLabel(card, text=data['title'], font=config.FONT_HEADER)
            lbl_title.pack(pady=(15, 0))

            # Author
            lbl_author = ctk.CTkLabel(card, text=data.get('author', 'Неизвестен'),
                                      font=config.FONT_SMALL, text_color="gray")
            lbl_author.pack(pady=(0, 5))
            
            # Character
            lbl_char = ctk.CTkLabel(card, text=f"Герой: {data['character']}",
                                    font=config.FONT_BODY, text_color="silver")
            lbl_char.pack(pady=(0, 15))

            # Button
            btn = ctk.CTkButton(card, text="Започни разговор", 
                                fg_color=data['color'], hover_color="#333",
                                font=config.FONT_BODY,
                                command=lambda k=key: self.start_chat(k))
            btn.pack(pady=(0, 20))

    # ================== SCREEN: CHAT ==================
    def start_chat(self, work_key):
        self.current_work = LIBRARY[work_key]
        
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Session Init
        self.chat = None
        self.request_queue = queue.Queue()

        if self.api_configured:
            try:
                self.chat = self.ai_service.create_chat(self.current_work['prompt'])
                print(f"Chat session started for: {self.current_work['character']}")
            except Exception as e:
                print(f"Session error: {e}")
                traceback.print_exc()
                self.update_ui(f"ГРЕШКА: {e}")

        threading.Thread(target=self.request_worker, daemon=True).start()

        # --- UI Components ---
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

        self.entry = ctk.CTkEntry(input_frame, placeholder_text="Напиши нещо...", font=config.FONT_BODY)
        self.entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        self.btn_send = ctk.CTkButton(input_frame, text="➤", width=40, command=self.send_message, font=config.FONT_BODY)
        self.btn_send.pack(side="right", padx=10)

        # Status Label (Typing indicator)
        self.status_label = ctk.CTkLabel(self.main_container, text="", font=config.FONT_TINY, text_color="gray")
        self.status_label.place(relx=0.05, rely=0.84, anchor="w") # Position above input

        start_msg = self.current_work.get('first_message', 'Здравей!')
        self.add_message(self.current_work['character'], start_msg, is_user=False)

    def add_message(self, sender, text, is_user=True):
        align = "e" if is_user else "w"
        bubble_color = config.COLOR_USER_BUBBLE if is_user else config.COLOR_AI_BUBBLE
        avatar_color = config.COLOR_AVATAR_USER if is_user else config.COLOR_AVATAR_AI
        
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5)
        
        # Inner frame to hold avatar + bubble
        content_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        content_frame.pack(anchor=align, padx=10)

        # Avatar circle (using a rounded frame)
        initial = sender[0].upper() if sender else "?"
        avatar = ctk.CTkFrame(content_frame, width=35, height=35, corner_radius=17, fg_color=avatar_color)

        # We need to turn off propagation to force size
        avatar.pack_propagate(False)

        lbl_initial = ctk.CTkLabel(avatar, text=initial, font=("Arial", 14, "bold"), text_color="white")
        lbl_initial.place(relx=0.5, rely=0.5, anchor="center")

        # Bubble
        bubble = ctk.CTkLabel(content_frame, text=text, fg_color=bubble_color, corner_radius=15,
                              wraplength=380, padx=15, pady=10, font=config.FONT_BODY)

        # Layout based on user or AI
        if is_user:
            # User: Bubble Left, Avatar Right
            bubble.pack(side="left", padx=(0, 10))
            avatar.pack(side="right")
        else:
            # AI: Avatar Left, Bubble Right
            avatar.pack(side="left", padx=(0, 10))
            bubble.pack(side="right")
        
        self.main_container.after(10, lambda: self._scroll_down())

    def _scroll_down(self):
        try: self.chat_frame._parent_canvas.yview_moveto(1.0)
        except: pass

    def send_message(self, text=None):
        if text is None: text = self.entry.get()
        if not text.strip(): return

        self.add_message("Ти", text, is_user=True)
        self.entry.delete(0, 'end')

        # Disable input
        self.entry.configure(state="disabled")
        self.btn_send.configure(state="disabled")
        self.status_label.configure(text=f"{self.current_work['character']} пише...")

        self.request_queue.put(text)

    def request_worker(self):
        while True:
            text = self.request_queue.get()
            if text: self.get_ai_response(text)

    def get_ai_response(self, user_text):
        if not self.chat or not self.ai_service:
            self.update_ui("Няма активна AI сесия.")
            return

        try:
            # Using AIService to send message
            response_text = self.ai_service.send_message(
                self.chat,
                user_text,
                status_callback=lambda msg: self.update_ui(msg)
            )
            self.update_ui(response_text)

        except Exception as e:
            self.update_ui(f"Грешка: {e}")
            print(f"API Error: {e}")

    def update_ui(self, text):
        def _update():
            self.add_message(self.current_work['character'], text, is_user=False)
            # Re-enable input
            self.status_label.configure(text="")
            self.entry.configure(state="normal")
            self.btn_send.configure(state="normal")
            self.entry.focus()

        self.main_container.after(0, _update)

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()