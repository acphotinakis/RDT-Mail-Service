import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict


class ComposeDialog:
    """Modal compose dialog for creating or replying to emails."""

    def __init__(self, parent, initial_data: Optional[Dict[str, str]] = None):
        self.initial = initial_data or {}
        self.result: Optional[Dict[str, str]] = None

        self.top = tk.Toplevel(parent)
        self.top.title("Compose Email")
        self.top.geometry("600x450")
        self.top.transient(parent)
        self.top.grab_set()

        self._build_form()

    def _build_form(self):
        frame = ttk.Frame(self.top, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="To").pack(anchor="w")
        self.to_var = tk.StringVar(value=self.initial.get("recipient", ""))
        ttk.Entry(frame, textvariable=self.to_var).pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="Subject").pack(anchor="w")
        self.subject_var = tk.StringVar(value=self.initial.get("subject", ""))
        ttk.Entry(frame, textvariable=self.subject_var).pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="Body").pack(anchor="w")
        self.body_text = tk.Text(frame, height=15, wrap="word")
        self.body_text.pack(fill="both", expand=True)
        if "body" in self.initial:
            self.body_text.insert("1.0", self.initial["body"])

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))

        ttk.Button(buttons, text="Send", command=self._on_send).pack(side="right", padx=(4, 0))
        ttk.Button(buttons, text="Cancel", command=self.top.destroy).pack(side="right")

    def _on_send(self):
        recipient = self.to_var.get().strip()
        subject = self.subject_var.get().strip()
        body = self.body_text.get("1.0", "end-1c")

        if not recipient or not subject:
            return  # Keep dialog open; could add warning label if desired

        self.result = {"recipient": recipient, "subject": subject, "body": body}
        self.top.destroy()

    def show(self) -> Optional[Dict[str, str]]:
        self.top.wait_window()
        return self.result
