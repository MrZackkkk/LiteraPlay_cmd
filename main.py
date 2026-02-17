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


class UITheme:
    BG = "#070B16"
    BG_SOFT = "#0D1426"
    BG_ELEVATED = "#111A33"
    PANEL = "#0F1931"
    PANEL_BORDER = "#2A3B66"
    TEXT_PRIMARY = "#E7ECFF"
    TEXT_MUTED = "#9CAACB"
    ACCENT = "#6E8BFF"
    ACCENT_HOVER = "#7B96FF"
    SUCCESS = "#22C55E"


WORK_ACCENTS = {
    "nemili": {"accent": "#00B77B", "hover": "#00D892", "soft": "#083B31", "icon": "⚔"},
    "pod_igoto": {"accent": "#FF5D73", "hover": "#FF7386", "soft": "#3A1821", "icon": "✦"},
    "tyutyun": {"accent": "#7A6CFF", "hover": "#8D83FF", "soft": "#231D4B", "icon": "◆"},
}


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
        self.geometry(config.WINDOW_SIZE)
        self.configure(fg_color=UITheme.BG)

        # AI Service Init
        self.ai_service = None
        self.api_configured = False
        self.loading_label = None
        self.loading_step = 0

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
        self.main_container = ctk.CTkFrame(self, fg_color=UITheme.BG)
        self.main_container.pack(fill="both", expand=True, padx=12, pady=12)

        self.show_menu()

    # ================== SCREEN: MENU ==================
    def show_menu(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(
            self.main_container,
            text="Избери произведение",
            font=("Roboto", 36, "bold"),
            text_color=UITheme.TEXT_PRIMARY,
        )
        title.pack(pady=(24, 4))

        subtitle = ctk.CTkLabel(
            self.main_container,
            text="Потопи се в жива литературна сцена.",
            font=("Roboto", 14),
            text_color=UITheme.TEXT_MUTED,
        )
        subtitle.pack(pady=(0, 16))

        for key, data in LIBRARY.items():
            accent_data = WORK_ACCENTS.get(key, {})
            accent = accent_data.get("accent", data.get("color", UITheme.ACCENT))
            hover = accent_data.get("hover", UITheme.ACCENT_HOVER)
            soft = accent_data.get("soft", UITheme.BG_SOFT)
            icon = accent_data.get("icon", "✦")

            card = ctk.CTkFrame(
                self.main_container,
                fg_color=UITheme.BG_ELEVATED,
                border_width=1,
                border_color=UITheme.PANEL_BORDER,
                corner_radius=18,
            )
            card.pack(pady=10, padx=10, fill="x")

            card_top = ctk.CTkFrame(card, fg_color="transparent")
            card_top.pack(fill="x", padx=18, pady=(14, 4))

            badge = ctk.CTkLabel(
                card_top,
                text=f" {icon}  {data.get('author', 'Класика')} ",
                fg_color=soft,
                corner_radius=14,
                text_color=accent,
                font=("Roboto", 12, "bold"),
            )
            badge.pack(side="left")

            lbl_title = ctk.CTkLabel(card, text=f"{data['title']}", font=("Roboto", 30, "bold"), text_color=UITheme.TEXT_PRIMARY)
            lbl_title.pack(anchor="w", padx=18, pady=(4, 0))

            lbl_char = ctk.CTkLabel(card, text=f"Герой: {data['character']}", text_color=UITheme.TEXT_MUTED, font=("Roboto", 16))
            lbl_char.pack(anchor="w", padx=18, pady=(0, 12))

            btn = ctk.CTkButton(
                card,
                text="Започни разговор",
                fg_color=accent,
                hover_color=hover,
                corner_radius=12,
                font=("Roboto", 15, "bold"),
                height=40,
                command=lambda k=key: self.start_chat(k),
            )
            btn.pack(padx=18, pady=(0, 16), anchor="w")

    # ================== SCREEN: CHAT ==================
    def start_chat(self, work_key):
        self.current_work = LIBRARY[work_key]
        accent_data = WORK_ACCENTS.get(work_key, {})
        self.work_accent = accent_data.get("accent", self.current_work.get("color", UITheme.ACCENT))
        self.work_accent_hover = accent_data.get("hover", UITheme.ACCENT_HOVER)
        self.work_soft = accent_data.get("soft", UITheme.BG_SOFT)

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
        header_frame = ctk.CTkFrame(self.main_container, fg_color=UITheme.PANEL, corner_radius=16, border_width=1, border_color=UITheme.PANEL_BORDER)
        header_frame.pack(fill="x", side="top", padx=4, pady=(2, 10))

        btn_back = ctk.CTkButton(
            header_frame,
            text="← Меню",
            width=90,
            height=34,
            fg_color="transparent",
            hover_color=UITheme.BG_SOFT,
            border_width=1,
            border_color=UITheme.PANEL_BORDER,
            corner_radius=10,
            text_color=UITheme.TEXT_PRIMARY,
            command=self.show_menu,
        )
        btn_back.pack(side="left", padx=12, pady=10)

        title_group = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_group.pack(side="left", padx=8)

        lbl_header = ctk.CTkLabel(
            title_group,
            text=f"{self.current_work['character']}",
            font=("Roboto", 21, "bold"),
            text_color=UITheme.TEXT_PRIMARY,
        )
        lbl_header.pack(anchor="w")

        status_pill = ctk.CTkLabel(
            title_group,
            text="В роля",
            fg_color=self.work_soft,
            text_color=self.work_accent,
            corner_radius=12,
            font=("Roboto", 11, "bold"),
            padx=10,
            pady=2,
        )
        status_pill.pack(anchor="w", pady=(2, 0))

        # Input Area (Bottom)
        input_frame = ctk.CTkFrame(self.main_container, fg_color=UITheme.PANEL, corner_radius=18, border_width=1, border_color=UITheme.PANEL_BORDER)
        input_frame.pack(side="bottom", fill="x", padx=4, pady=(6, 4))

        self.btn_send = ctk.CTkButton(
            input_frame,
            text="➤",
            width=46,
            height=38,
            corner_radius=11,
            fg_color=self.work_accent,
            hover_color=self.work_accent_hover,
            font=("Roboto", 16, "bold"),
            command=self.send_message,
        )
        self.btn_send.pack(side="right", padx=(4, 10), pady=10)

        self.entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Напиши следващия си ход...",
            height=38,
            corner_radius=12,
            border_width=0,
            fg_color=UITheme.BG_SOFT,
            text_color=UITheme.TEXT_PRIMARY,
            placeholder_text_color=UITheme.TEXT_MUTED,
            font=("Roboto", 14),
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=10)
        self.entry.bind("<Return>", lambda event: self.send_message())

        # Options Area (Bottom, above Input)
        self.options_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.options_frame.pack(side="bottom", fill="x", padx=4, pady=(2, 6))

        for text in self.current_work['choices']:
            btn = ctk.CTkButton(
                self.options_frame,
                text=text,
                fg_color=self.work_soft,
                hover_color=self.work_accent,
                text_color=UITheme.TEXT_PRIMARY,
                corner_radius=12,
                height=36,
                anchor="w",
                font=("Roboto", 13, "bold"),
                command=lambda t=text: self.send_message(t),
            )
            btn.pack(pady=4, fill="x")

        # Chat Frame (Remaining space)
        self.chat_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=UITheme.BG_ELEVATED,
            corner_radius=20,
            border_width=1,
            border_color=UITheme.PANEL_BORDER,
            scrollbar_button_color=UITheme.PANEL_BORDER,
            scrollbar_button_hover_color=self.work_accent,
        )
        self.chat_frame.pack(side="top", pady=4, padx=4, fill="both", expand=True)

        self.loading_label = None

        self.add_message("System", self.current_work['intro'], is_user=False, msg_type="system")

        start_msg = self.current_work.get('first_message', 'Здравей!')
        self.add_message(self.current_work['character'], start_msg, is_user=False)

    def add_message(self, sender, text, is_user=True, msg_type="normal"):
        if msg_type == "system":
            msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=7)

            bubble = ctk.CTkLabel(
                msg_frame,
                text=text,
                text_color=UITheme.TEXT_MUTED,
                fg_color=UITheme.BG_SOFT,
                wraplength=540,
                padx=15,
                pady=8,
                corner_radius=12,
                font=("Roboto", 13, "italic"),
            )
            bubble.pack(anchor="center")

        else:
            align = "e" if is_user else "w"
            color = self.work_accent if is_user else UITheme.PANEL

            msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=7)

            name_lbl = ctk.CTkLabel(msg_frame, text=sender, font=("Roboto", 11), text_color=UITheme.TEXT_MUTED)
            name_lbl.pack(anchor=align, padx=14)

            bubble = ctk.CTkLabel(
                msg_frame,
                text=text,
                fg_color=color,
                text_color=UITheme.TEXT_PRIMARY,
                corner_radius=16,
                wraplength=520,
                padx=18,
                pady=12,
                font=("Roboto", 14),
                justify="left",
            )
            bubble.pack(anchor=align, padx=8)

        self.main_container.after(10, lambda: self._scroll_down())

    def set_loading_state(self, is_loading):
        if is_loading:
            self.entry.configure(state="disabled")
            self.btn_send.configure(state="disabled")

            if not self.loading_label:
                self.loading_step = 0
                msg = f"{self.current_work['character']} пише"
                self.loading_label = ctk.CTkLabel(
                    self.chat_frame,
                    text=msg,
                    font=("Roboto", 12, "italic"),
                    text_color=UITheme.TEXT_MUTED,
                )
                self.loading_label.pack(anchor="w", padx=20, pady=5)
                self._animate_loading_text()
                self.main_container.after(10, lambda: self._scroll_down())
        else:
            self.entry.configure(state="normal")
            self.btn_send.configure(state="normal")
            self.entry.focus()

            if self.loading_label:
                self.loading_label.destroy()
                self.loading_label = None

    def _animate_loading_text(self):
        if not self.loading_label:
            return

        dots = "." * (self.loading_step % 4)
        self.loading_label.configure(text=f"{self.current_work['character']} пише{dots}")
        self.loading_step += 1
        self.main_container.after(350, self._animate_loading_text)

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
                fg_color=self.work_soft,
                hover_color=self.work_accent,
                text_color=UITheme.TEXT_PRIMARY,
                corner_radius=12,
                height=36,
                anchor="w",
                font=("Roboto", 13, "bold"),
                command=lambda t=text: self.send_message(t),
            )
            btn.pack(pady=4, fill="x")


if __name__ == "__main__":
    if not (config.API_KEY or "").strip():
        setup_window = APIKeyWindow()
        setup_window.mainloop()
        if not setup_window.saved:
            raise SystemExit(0)

    app = ChatApp()
    app.mainloop()
