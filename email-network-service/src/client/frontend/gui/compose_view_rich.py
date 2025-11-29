import tkinter as tk
from tkinter import ttk

class ComposeDialog:
    def __init__(self, parent, initial):
        self.top = tk.Toplevel(parent)
        self.top.title("Compose")
        self.result = None
        # fields
        self.to_var = tk.StringVar(value=initial.get("recipient", ""))
        self.subj_var = tk.StringVar(value=initial.get("subject", ""))
        ttk.Label(self.top, text="To").pack(anchor="w")
        ttk.Entry(self.top, textvariable=self.to_var, width=50).pack(fill="x")
        ttk.Label(self.top, text="Subject").pack(anchor="w")
        ttk.Entry(self.top, textvariable=self.subj_var, width=50).pack(fill="x")
        ttk.Label(self.top, text="Body").pack(anchor="w")
        self.body = tk.Text(self.top, width=60, height=15)
        self.body.pack(fill="both", expand=True)
        if "body" in initial:
            self.body.insert("1.0", initial["body"])
        ttk.Button(self.top, text="Send", command=self._on_send).pack(pady=4)
        ttk.Button(self.top, text="Cancel", command=self.top.destroy).pack()
        self.top.grab_set()  # modal

    def _on_send(self):
        to = self.to_var.get().strip()
        subj = self.subj_var.get().strip()
        body = self.body.get("1.0", "end-1c")
        if to and subj:
            self.result = {"recipient": to, "subject": subj, "body": body}
            self.top.destroy()

    def show(self):
        self.top.wait_window()
        return self.result
