import tkinter as tk
from tkinter import ttk
from typing import Optional


class WelcomeDialog:
    """Welcome screen to choose login or signup."""

    def __init__(self, error_message: Optional[str] = None):
        self.error_message = error_message
        self.result: Optional[str] = None

    def run(self) -> Optional[str]:
        root = tk.Tk()
        root.title("Welcome")
        root.geometry("360x200")

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Welcome to the Email Client", font=("TkDefaultFont", 12, "bold")).pack()

        if self.error_message:
            ttk.Label(frame, text=self.error_message, foreground="red").pack(pady=(4, 0))

        ttk.Label(frame, text="Choose an option:").pack(pady=(12, 6))

        buttons = ttk.Frame(frame)
        buttons.pack()
        ttk.Button(buttons, text="Login", command=lambda: self._choose(root, "login")).pack(side="left", padx=6)
        ttk.Button(buttons, text="Sign Up", command=lambda: self._choose(root, "signup")).pack(side="left", padx=6)

        root.mainloop()
        return self.result

    def _choose(self, root, choice: str):
        self.result = choice
        root.destroy()
