import threading
import queue
import traceback
from tkinter import messagebox
from dependency_compat import load_customtkinter

ctk = load_customtkinter()

import config
from ai_service import AIService, validate_api_key_with_available_sdk
from data import LIBRARY
from response_parser import parse_ai_json_response

# --- APP SETUP ---
config.setup_appearance()


def validate_api_key(key: str):
    """Validate key against whichever Gemini SDK is available."""
    return validate_api_key_with_available_sdk(key)


class APIKeyWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.saved = False

        self.title("LiteraPlay Setup")
        self.geometry("520x280")

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        label = ctk.CTkLabel(
            container,
            text="Welcome to LiteraPlay. Please enter your Google Gemini API Key.",
            wraplength=460,
            justify="left",
            font=("Roboto", 16, "bold"),
        )
        label.pack(anchor="w", pady=(10, 18), padx=14)

        self.key_entry = ctk.CTkEntry(
            container,
            placeholder_text="API...",
            show="*",
            width=460,
        )
        self.key_entry.pack(padx=14, fill="x")
        self.key_entry.focus()

        self.verify_btn = ctk.CTkButton(
            container,
            text="Verify & Save",
            command=self.on_verify,
        )
        self.verify_btn.pack(pady=(16, 10), padx=14, anchor="e")

        self.status_label = ctk.CTkLabel(container, text="", text_color="gray")
        self.status_label.pack(anchor="w", padx=14)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.saved = False
        self.destroy()

    def on_verify(self):
        key = self.key_entry.get().strip()
        self.verify_btn.configure(state="disabled", text="Checking...")
        self.status_label.configure(text="Проверка на API ключ...")

        threading.Thread(target=self._verify_worker, args=(key,), daemon=True).start()

    def _verify_worker(self, key: str):
        is_valid, message = validate_api_key(key)
        self.after(0, lambda: self._handle_validation_result(is_valid, message, key))

    def _handle_validation_result(self, is_valid: bool, message: str, key: str):
        if is_valid:
            should_save = messagebox.askyesno(
                "Потвърждение",
                "API ключът е валиден. Искате ли да го запазите в .env файла?",
                parent=self,
            )

            if not should_save:
                self.status_label.configure(text="Ключът е валиден. Записът е отказан.", text_color="orange")
                self.verify_btn.configure(state="normal", text="Verify & Save")
                return

            try:
                config.save_api_key(key)
                self.saved = True
                self.status_label.configure(text="Успешно запазено. Стартиране...", text_color="green")
                self.after(150, self.destroy)
            except Exception as exc:
                self.status_label.configure(text=f"Грешка при запис в .env: {exc}", text_color="red")
                self.verify_btn.configure(state="normal", text="Verify & Save")
        else:
            self.status_label.configure(text=message, text_color="red")
            self.verify_btn.configure(state="normal", text="Verify & Save")


class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(config.TITLE)
        self.geometry("980x820")
        self.minsize(860, 700)

        self.palette = {
            "bg": "#0B1020",
            "surface": "#11182C",
            "surface_soft": "#161F36",
            "surface_chat": "#0D1325",
            "border": "#2A3554",
            "border_active": "#4E6BFF",
            "text_primary": "#F5F7FF",
            "text_secondary": "#9BA6C4",
            "accent": "#4E6BFF",
            "accent_hover": "#6F86FF",
            "success": "#2CC7A0",
            "user_bubble": "#385CFF",
            "ai_bubble": "#1A233A",
            "chip": "#253251",
        }

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

        # Main Container
        self.main_container = ctk.CTkFrame(self, fg_color=self.palette["bg"])
        self.main_container.pack(fill="both", expand=True)

        self.show_menu()

    # ================== SCREEN: MENU ==================
    def show_menu(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        hero = ctk.CTkFrame(self.main_container, fg_color="transparent")
        hero.pack(fill="x", padx=30, pady=(36, 20))

        badge = ctk.CTkLabel(
            hero,
            text="✦ LITERAPLAY SELECT",
            fg_color=self.palette["surface"],
            text_color=self.palette["accent_hover"],
            corner_radius=20,
            padx=16,
            pady=8,
            font=("Roboto", 12, "bold"),
        )
        badge.pack(anchor="w")

        title = ctk.CTkLabel(
            hero,
            text="Избери произведение",
            text_color=self.palette["text_primary"],
            font=("Roboto", 42, "bold"),
        )
        title.pack(anchor="w", pady=(18, 4))

        subtitle = ctk.CTkLabel(
            hero,
            text="Потопи се в диалог с легендарни герои – динамично, стилно и живо.",
            text_color=self.palette["text_secondary"],
            font=("Roboto", 16),
        )
        subtitle.pack(anchor="w")

        cards_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        cards_container.pack(fill="both", expand=True, padx=24, pady=8)

        for key, data in LIBRARY.items():
            card = ctk.CTkFrame(
                cards_container,
                fg_color=self.palette["surface"],
                border_width=1,
                border_color=self.palette["border"],
                corner_radius=18,
            )
            card.pack(pady=12, padx=8, fill="x")

            lbl_title = ctk.CTkLabel(
                card,
                text=f"{data['title']}",
                text_color=self.palette["text_primary"],
                font=("Roboto", 30, "bold"),
            )
            lbl_title.pack(pady=(16, 2))

            lbl_char = ctk.CTkLabel(
                card,
                text=f"Герой: {data['character']}",
                text_color=self.palette["text_secondary"],
                font=("Roboto", 18),
            )
            lbl_char.pack(pady=(0, 14))

            btn = ctk.CTkButton(
                card,
                text="Започни разговор",
                fg_color=data['color'],
                hover_color=self.palette["accent_hover"],
                font=("Roboto", 16, "bold"),
                corner_radius=14,
                height=44,
                width=220,
                command=lambda k=key: self.start_chat(k),
            )
            btn.pack(pady=(0, 20))

            self._bind_card_hover(card, btn)

    def _is_descendant(self, widget, ancestor):
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            current = current.master
        return False

    def _bind_card_hover(self, card, btn):
        def activate(_event=None):
            card.configure(border_color=self.palette["border_active"])
            btn.configure(width=235)

        def deactivate_if_outside(_event=None):
            hovered = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
            if hovered is not None and self._is_descendant(hovered, card):
                return
            card.configure(border_color=self.palette["border"])
            btn.configure(width=220)

        hover_widgets = [card] + list(card.winfo_children())
        for widget in hover_widgets:
            widget.bind("<Enter>", activate, add="+")
            widget.bind("<Leave>", deactivate_if_outside, add="+")

    # ================== SCREEN: CHAT ==================
    def start_chat(self, work_key):
        self.current_work = LIBRARY[work_key]

        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Session Init
        self.chat = None
        self.request_queue = queue.Queue()

        if self.api_configured and self.ai_service is not None:
            try:
                self.chat = self.ai_service.create_chat(self.current_work['prompt'])
                print(f"Chat session started for: {self.current_work['character']}")
            except Exception as e:
                print(f"Session error: {e}")
                traceback.print_exc()
                self.update_ui(f"ГРЕШКА: {e}")

        threading.Thread(target=self.request_worker, daemon=True).start()

        # --- UI Components ---
        header_frame = ctk.CTkFrame(
            self.main_container,
            height=64,
            fg_color=self.palette["surface"],
            border_width=1,
            border_color=self.palette["border"],
            corner_radius=0,
        )
        header_frame.pack(fill="x", side="top", padx=18, pady=(16, 6))

        btn_back = ctk.CTkButton(header_frame, text="⬅ Меню", width=60,
                                 fg_color="transparent", border_width=1,
                                 border_color=self.palette["border_active"],
                                 hover_color=self.palette["surface_soft"],
                                 command=self.show_menu)
        btn_back.pack(side="left", padx=10, pady=10)

        lbl_header = ctk.CTkLabel(header_frame, text=f"{self.current_work['character']}",
                                  text_color=self.palette["text_primary"],
                                  font=("Roboto", 24, "bold"))
        lbl_header.pack(side="left", padx=10)

        status_chip = ctk.CTkLabel(
            header_frame,
            text="● На линия",
            fg_color=self.palette["chip"],
            text_color=self.palette["success"],
            corner_radius=16,
            padx=10,
            pady=4,
            font=("Roboto", 12, "bold"),
        )
        status_chip.pack(side="right", padx=12)

        # Input Area (Bottom)
        input_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=self.palette["surface"],
            corner_radius=20,
            border_width=1,
            border_color=self.palette["border"],
        )
        input_frame.pack(side="bottom", fill="x", padx=15, pady=(5, 15))

        self.btn_send = ctk.CTkButton(
            input_frame,
            text="➤",
            width=42,
            height=38,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"],
            font=("Roboto", 16, "bold"),
            corner_radius=10,
            command=self.send_message,
        )
        self.btn_send.pack(side="right", padx=(5, 10), pady=10)

        self.entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Напиши нещо...",
            height=40,
            border_width=0,
            fg_color=self.palette["surface_soft"],
            text_color=self.palette["text_primary"],
            placeholder_text_color=self.palette["text_secondary"],
            font=("Roboto", 16),
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(15, 5), pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        # Options Area (Bottom, above Input)
        self.options_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.options_frame.pack(side="bottom", fill="x", padx=15, pady=5)

        for text in self.current_work['choices']:
            btn = ctk.CTkButton(
                self.options_frame,
                text=text,
                fg_color=self.current_work['color'],
                hover_color=self.palette["accent_hover"],
                height=36,
                font=("Roboto", 15, "bold"),
                corner_radius=12,
                command=lambda t=text: self.send_message(t),
            )
            btn.pack(pady=2, fill="x")

        # Chat Frame (Remaining space)
        self.chat_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=self.palette["surface_chat"],
            corner_radius=18,
            border_width=1,
            border_color=self.palette["border"],
        )
        self.chat_frame.pack(side="top", pady=5, padx=10, fill="both", expand=True)

        self.loading_label = None

        self.add_message("System", self.current_work['intro'], is_user=False, msg_type="system")

        start_msg = self.current_work.get('first_message', 'Здравей!')
        self.add_message(self.current_work['character'], start_msg, is_user=False)

    def add_message(self, sender, text, is_user=True, msg_type="normal"):
        if msg_type == "system":
            msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=5)

            bubble = ctk.CTkLabel(msg_frame, text=text, text_color=self.palette["text_secondary"],
                                  wraplength=720, padx=15, pady=5, font=("Roboto", 17, "italic"))
            bubble.pack(anchor="center")

        else:
            align = "e" if is_user else "w"
            color = self.palette["user_bubble"] if is_user else self.palette["ai_bubble"]

            msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=5)

            name_lbl = ctk.CTkLabel(msg_frame, text=sender, font=("Roboto", 12, "bold"), text_color=self.palette["text_secondary"])
            name_lbl.pack(anchor=align, padx=15)

            bubble = ctk.CTkLabel(msg_frame, text=text, fg_color=color, corner_radius=20,
                                  text_color=self.palette["text_primary"],
                                  wraplength=690, padx=20, pady=12, font=("Roboto", 16))
            bubble.pack(anchor=align, padx=10)

        self.main_container.after(10, lambda: self._scroll_down())

    def set_loading_state(self, is_loading):
        option_state = "disabled" if is_loading else "normal"
        for widget in self.options_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(state=option_state)

        if is_loading:
            self.entry.configure(state="disabled")
            self.btn_send.configure(state="disabled")

            if not self.loading_label:
                msg = f"{self.current_work['character']} пише..."
                self.loading_label = ctk.CTkLabel(self.chat_frame, text=msg,
                                                  font=("Roboto", 13, "italic"), text_color=self.palette["text_secondary"])
                self.loading_label.pack(anchor="w", padx=20, pady=5)
                self.main_container.after(10, lambda: self._scroll_down())
        else:
            self.entry.configure(state="normal")
            self.btn_send.configure(state="normal")
            self.entry.focus()

            if self.loading_label:
                self.loading_label.destroy()
                self.loading_label = None

    def _scroll_down(self):
        try:
            self.chat_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def send_message(self, text=None):
        if text is None:
            text = self.entry.get()
        if not text.strip():
            return

        self.add_message("Ти", text, is_user=True)
        self.entry.delete(0, 'end')
        self.request_queue.put(text)

    def request_worker(self):
        while True:
            text = self.request_queue.get()
            if text:
                self.get_ai_response(text)

    def get_ai_response(self, user_text):
        if not self.chat or not self.ai_service:
            self.update_ui("Няма активна AI сесия.")
            return

        self.main_container.after(0, lambda: self.set_loading_state(True))

        try:
            # Using AIService to send message
            response_text = self.ai_service.send_message(
                self.chat,
                user_text,
                status_callback=lambda msg: self.update_ui(msg)
            )
            self.main_container.after(0, lambda: self.set_loading_state(False))

            # Parse JSON
            data = parse_ai_json_response(response_text)

            if data and isinstance(data, dict):
                reply = data.get("reply", response_text)
                options = data.get("options", [])

                self.update_ui(reply)
                self.main_container.after(0, lambda: self.update_choices(options))
            else:
                # Fallback if no valid JSON structure found
                self.update_ui(response_text)
                self.main_container.after(0, lambda: self.update_choices([]))

        except Exception as e:
            self.main_container.after(0, lambda: self.set_loading_state(False))
            self.update_ui(f"Грешка: {e}")
            print(f"API Error: {e}")

    def update_ui(self, text):
        self.main_container.after(0, lambda: self.add_message(self.current_work['character'], text, is_user=False))

    def update_choices(self, options_list):
        # Clear existing buttons
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        if not options_list:
            return

        # Create new buttons
        for text in options_list:
            btn = ctk.CTkButton(
                self.options_frame,
                text=text,
                fg_color=self.current_work['color'],
                hover_color=self.palette["accent_hover"],
                height=36,
                font=("Roboto", 15, "bold"),
                corner_radius=12,
                command=lambda t=text: self.send_message(t),
            )
            btn.pack(pady=2, fill="x")


if __name__ == "__main__":
    if not (config.API_KEY or "").strip():
        setup_window = APIKeyWindow()
        setup_window.mainloop()
        if not setup_window.saved:
            raise SystemExit(0)

    app = ChatApp()
    app.mainloop()
