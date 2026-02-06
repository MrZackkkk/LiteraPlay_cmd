import threading
import queue
import time
import traceback
import json
import re
from tkinter import messagebox
import customtkinter as ctk

import config
from ai_service import AIService
from data import LIBRARY
from ui_components import AnimationEngine, CharacterCard, ChatBubble, TypingIndicator

# --- APP SETUP ---
config.setup_appearance()

class MenuScreen(ctk.CTkFrame):
    def __init__(self, master, on_start_chat):
        super().__init__(master, fg_color="transparent")
        self.on_start_chat = on_start_chat
        
        # Grid Layout
        self.grid_columnconfigure((0, 1), weight=1) # 2 columns

        title = ctk.CTkLabel(self, text="Избери произведение", font=("Roboto", 28, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(40, 30))

        row = 1
        col = 0
        for key, data in LIBRARY.items():
            card = CharacterCard(self,
                                 title=data['title'],
                                 character=data['character'],
                                 color=data['color'],
                                 command=lambda k=key: self.on_start_chat(k))
            card.grid(row=row, column=col, padx=20, pady=20, sticky="nsew")
            
            col += 1
            if col > 1:
                col = 0
                row += 1

class ChatScreen(ctk.CTkFrame):
    def __init__(self, master, work_key, ai_service, on_back):
        super().__init__(master, fg_color="transparent")
        self.work_data = LIBRARY[work_key]
        self.ai_service = ai_service
        self.on_back = on_back
        
        self.chat = None
        self.request_queue = queue.Queue()
        self.stop_event = threading.Event()

        # Initialize UI
        self.setup_ui_modern()

        # Start Session
        if self.ai_service:
            try:
                self.chat = self.ai_service.create_chat(self.work_data['prompt'])
                print(f"Chat session started for: {self.work_data['character']}")
            except Exception as e:
                print(f"Session error: {e}")
                self.update_ui(f"ГРЕШКА: {e}")

        # Start Worker
        threading.Thread(target=self.request_worker, daemon=True).start()

        # Initial Messages
        self.add_message("System", self.work_data['intro'], is_user=False, msg_type="system")
        start_msg = self.work_data.get('first_message', 'Здравей!')
        self.add_message(self.work_data['character'], start_msg, is_user=False)

    def setup_ui_modern(self):
        # Configure Grid
        self.grid_columnconfigure(0, weight=1) # Sidebar
        self.grid_columnconfigure(1, weight=3) # Chat
        self.grid_columnconfigure(2, weight=1) # Options
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR ---
        self.left_sidebar = ctk.CTkFrame(self, fg_color=config.COLOR_SIDEBAR, corner_radius=0)
        self.left_sidebar.grid(row=0, column=0, sticky="nsew")

        # Character Info
        ctk.CTkLabel(self.left_sidebar, text=self.work_data['character'],
                     font=("Roboto", 20, "bold"), wraplength=180).pack(pady=(40, 10), padx=20)

        ctk.CTkLabel(self.left_sidebar, text=self.work_data['title'],
                     font=("Arial", 14, "italic")).pack(pady=5)

        ctk.CTkLabel(self.left_sidebar, text=f"от {self.work_data['author']}",
                     text_color="gray", font=("Arial", 12)).pack(pady=5)

        # Divider
        ctk.CTkFrame(self.left_sidebar, height=2, fg_color="#444").pack(fill="x", padx=20, pady=20)

        # Back Button
        ctk.CTkButton(self.left_sidebar, text="⬅ Меню",
                      fg_color="transparent", border_width=1, hover_color="#333",
                      command=self.on_back).pack(side="bottom", pady=30, padx=20, fill="x")

        # --- CENTER CHAT ---
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Chat History
        self.chat_frame = ctk.CTkScrollableFrame(self.center_frame, fg_color="transparent")
        self.chat_frame.pack(side="top", expand=True, fill="both", pady=(0, 10))

        # Input Area
        self.input_frame = ctk.CTkFrame(self.center_frame, fg_color="#222", corner_radius=20)
        self.input_frame.pack(side="bottom", fill="x")

        self.btn_send = ctk.CTkButton(self.input_frame, text="➤", width=40, height=35, command=self.send_message)
        self.btn_send.pack(side="right", padx=(5, 10), pady=10)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Напиши нещо...", height=35, border_width=0, fg_color="#333")
        self.entry.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        # --- RIGHT SIDEBAR ---
        self.right_sidebar = ctk.CTkFrame(self, fg_color=config.COLOR_SIDEBAR, corner_radius=0)
        self.right_sidebar.grid(row=0, column=2, sticky="nsew")
        
        ctk.CTkLabel(self.right_sidebar, text="Действия", font=("Arial", 14, "bold")).pack(pady=(40, 20), padx=10)

        self.options_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=10)

    def add_message(self, sender, text, is_user=True, msg_type="normal"):
        if msg_type == "system":
            msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=5)
            bubble = ctk.CTkLabel(msg_frame, text=text, text_color="gray",
                                  wraplength=480, padx=15, pady=5, font=("Arial", 12, "italic"))
            bubble.pack(anchor="center")
        else:
            color = config.COLOR_USER_BUBBLE if is_user else config.COLOR_AI_BUBBLE
            bubble = ChatBubble(self.chat_frame, text=text, sender=sender, is_user=is_user, bubble_color=color)
            bubble.pack(fill="x", pady=5)

        self.after(10, self._scroll_down)

    def set_loading_state(self, is_loading):
        if is_loading:
            self.entry.configure(state="disabled")
            self.btn_send.configure(state="disabled")
            if not self.loading_label:
                self.loading_label = TypingIndicator(self.chat_frame, bubble_color=config.COLOR_AI_BUBBLE)
                self.loading_label.pack(anchor="w", padx=20, pady=5)
                self.after(10, self._scroll_down)
        else:
            self.entry.configure(state="normal")
            self.btn_send.configure(state="normal")
            self.entry.focus()
            if self.loading_label:
                self.loading_label.stop()
                self.loading_label = None

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
        while not self.stop_event.is_set():
            try:
                text = self.request_queue.get(timeout=1)
                if text: self.get_ai_response(text)
            except queue.Empty:
                continue

    def get_ai_response(self, user_text):
        if not self.chat or not self.ai_service:
            self.update_ui("Няма активна AI сесия.")
            return

        self.after(0, lambda: self.set_loading_state(True))

        try:
            response_text = self.ai_service.send_message(
                self.chat,
                user_text,
                status_callback=lambda msg: self.update_ui(msg)
            )
            self.after(0, lambda: self.set_loading_state(False))
            self.process_response(response_text)

        except Exception as e:
            self.after(0, lambda: self.set_loading_state(False))
            self.update_ui(f"Грешка: {e}")
            print(f"API Error: {e}")

    def process_response(self, response_text):
        # Parse JSON Logic
        data = None
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            try:
                data = json.loads(cleaned_text.strip())
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try: data = json.loads(json_match.group(0))
                    except: data = None

        if data and isinstance(data, dict):
            reply = data.get("reply", response_text)
            options = data.get("options", [])
            self.update_ui(reply)
            self.after(0, lambda: self.update_choices(options))
        else:
            self.update_ui(response_text)
            self.after(0, lambda: self.update_choices([]))

    def update_ui(self, text):
        self.after(0, lambda: self.add_message(self.work_data['character'], text, is_user=False))

    def update_choices(self, options_list):
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        if not options_list: return
        for text in options_list:
            btn = ctk.CTkButton(self.options_frame, text=text,
                                fg_color=self.work_data['color'], height=30,
                                command=lambda t=text: self.send_message(t))
            btn.pack(pady=5, fill="x") # Increased pady for better look in sidebar


class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(config.TITLE)
        self.geometry(config.WINDOW_SIZE)

        # Init AI Service
        self.ai_service = None
        if config.API_KEY:
            try:
                self.ai_service = AIService(config.API_KEY, config.DEFAULT_MODEL)
                print(f"AIService initialized.")
            except Exception as e:
                print(f"Error init AIService: {e}")

        if not self.ai_service:
            try:
                messagebox.showwarning("AI Key", "Няма връзка с AI. Проверете GOOGLE_API_KEY.")
            except: pass

        self.current_screen = None
        self.show_menu()

    def switch_screen(self, new_screen):
        width = self.winfo_width()

        # 1. Place new screen off-screen (right)
        new_screen.place(x=width, y=0, relwidth=1.0, relheight=1.0)

        # 2. If there is a current screen, animate sliding
        if self.current_screen:
            old_screen = self.current_screen

            # Animate Old Screen to Left
            AnimationEngine.animate(
                old_screen,
                lambda v: old_screen.place(x=v),
                0, -width,
                config.ANIMATION_DURATION_MS,
                easing_func=AnimationEngine.ease_out_quad
            )

            # Animate New Screen to Center
            AnimationEngine.animate(
                new_screen,
                lambda v: new_screen.place(x=v),
                width, 0,
                config.ANIMATION_DURATION_MS,
                easing_func=AnimationEngine.ease_out_quad,
                on_complete=lambda: old_screen.destroy()
            )
        else:
            # First load, just place it
            new_screen.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self.current_screen = new_screen

    def show_menu(self):
        screen = MenuScreen(self, on_start_chat=self.start_chat)
        self.switch_screen(screen)

    def start_chat(self, work_key):
        screen = ChatScreen(self, work_key, self.ai_service, on_back=self.show_menu)
        self.switch_screen(screen)

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()
