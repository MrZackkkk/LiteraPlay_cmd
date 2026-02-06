import customtkinter as ctk
import time
import math

class AnimationEngine:
    @staticmethod
    def interpolate_color(start_hex, end_hex, t):
        """Interpolate between two hex colors. t is between 0.0 and 1.0"""
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(*rgb)

        s_rgb = hex_to_rgb(start_hex)
        e_rgb = hex_to_rgb(end_hex)

        new_rgb = tuple(int(s + (e - s) * t) for s, e in zip(s_rgb, e_rgb))
        return rgb_to_hex(new_rgb)

    @staticmethod
    def ease_out_quad(t):
        return t * (2 - t)

    @staticmethod
    def animate(widget, callback, start_val, end_val, duration_ms, easing_func=None, on_complete=None):
        """
        Generic animation function.
        callback: function(value) -> void
        """
        start_time = time.time()

        def step():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)

            if easing_func:
                t = easing_func(progress)
            else:
                t = progress # linear

            current_val = start_val + (end_val - start_val) * t

            callback(current_val)

            if progress < 1.0:
                widget.after(16, step) # ~60fps
            else:
                if on_complete:
                    on_complete()

        step()

    @staticmethod
    def animate_color(widget, callback, start_hex, end_hex, duration_ms):
        start_time = time.time()

        def step():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)

            # Simple linear for color
            current_hex = AnimationEngine.interpolate_color(start_hex, end_hex, progress)
            callback(current_hex)

            if progress < 1.0:
                widget.after(16, step)

        step()

class CharacterCard(ctk.CTkFrame):
    def __init__(self, master, title, character, color, command, **kwargs):
        super().__init__(master, fg_color="transparent", border_width=2, border_color="#444", **kwargs)
        self.command = command
        self.default_border = "#444"
        self.hover_border = color # Use the character's theme color for hover

        self.grid_columnconfigure(0, weight=1)

        # Title
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Arial", 18, "bold"))
        self.lbl_title.grid(row=0, column=0, pady=(15, 5), padx=10)

        # Character Name
        self.lbl_char = ctk.CTkLabel(self, text=f"Герой: {character}", text_color="gray")
        self.lbl_char.grid(row=1, column=0, pady=(0, 10))

        # Start Button
        self.btn = ctk.CTkButton(self, text="Започни разговор",
                                fg_color=color, hover_color="#333",
                                command=self.on_click)
        self.btn.grid(row=2, column=0, pady=(0, 20), padx=20)

        # Bind hover events
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        # Bind children too so the effect doesn't flicker
        self.lbl_title.bind("<Enter>", self.on_enter)
        self.lbl_char.bind("<Enter>", self.on_enter)

    def on_click(self):
        if self.command:
            self.command()

    def on_enter(self, event):
        self.configure(border_color=self.hover_border)

    def on_leave(self, event):
        self.configure(border_color=self.default_border)

class ChatBubble(ctk.CTkFrame):
    def __init__(self, master, text, sender, is_user, bubble_color, text_color="white", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        align = "e" if is_user else "w"

        # Name Label
        self.name_lbl = ctk.CTkLabel(self, text=sender, font=("Arial", 10), text_color="silver")
        self.name_lbl.pack(anchor=align, padx=15)

        # The Bubble
        # We start with text color matching the bubble color (invisible) if we want to fade in
        # But CTkLabel doesn't let us easily change text color independently of fg_color in a way that implies transparency.
        # Actually, let's just animate the text color from the bg color (bubble_color) to the target text_color.

        self.bubble_color = bubble_color
        self.target_text_color = text_color

        self.bubble = ctk.CTkLabel(self, text=text, fg_color=bubble_color, corner_radius=20,
                                  wraplength=400, padx=20, pady=12, font=("Arial", 14),
                                  text_color=bubble_color) # Start invisible (same as bg)
        self.bubble.pack(anchor=align, padx=10)

        self.animate_in()

    def animate_in(self):
        # Animate text color from bubble_color to target_text_color
        # Note: If bubble_color is transparent, this might be tricky. But usually it's a solid color.
        # Assuming bubble_color is a hex string.

        AnimationEngine.animate_color(
            self,
            lambda c: self.bubble.configure(text_color=c),
            self.bubble_color,
            self.target_text_color,
            500 # 500ms fade in
        )

class TypingIndicator(ctk.CTkFrame):
    def __init__(self, master, bubble_color, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.bubble = ctk.CTkFrame(self, fg_color=bubble_color, corner_radius=20, width=60, height=30)
        self.bubble.pack(padx=10, anchor="w")

        self.dots = []
        for i in range(3):
            dot = ctk.CTkLabel(self.bubble, text="•", font=("Arial", 24), text_color="white")
            dot.place(relx=0.2 + (i*0.3), rely=0.5, anchor="center")
            self.dots.append(dot)

        self.animating = True
        self.animate(0)

    def animate(self, step):
        if not self.animating:
            return

        # Bounce effect: move dots up and down
        for i, dot in enumerate(self.dots):
            offset = math.sin((step + i * 2) * 0.5) * 0.1 # Small vertical movement
            dot.place_configure(rely=0.5 + offset)

        self.after(50, lambda: self.animate(step + 1))

    def stop(self):
        self.animating = False
        self.destroy()
