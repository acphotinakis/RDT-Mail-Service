import tkinter as tk
from tkinter import ttk, messagebox
from src.client.frontend.controllers.app_controller_rich import AppController, ViewInterface
from src.client.frontend.gui.message_view_tk import render_html_to_text

class MainWindowTk(ViewInterface):
    def __init__(self, username: str, password: str):
        self.root = tk.Tk()
        self.root.title("Email Client")
        self.controller = AppController(self, username, password)
        self.emails = []
        self.selected_email_index = None

        # Layout: header (buttons), left list, right body, footer (status)
        self._build_layout()
        self.controller.load_user_emails(self.controller.user)

    def _build_layout(self):
        # Header
        header = ttk.Frame(self.root, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="Compose", command=self.open_compose_window).pack(side="left")
        ttk.Button(header, text="Reply", command=self._on_reply).pack(side="left")
        ttk.Button(header, text="Delete", command=self._on_delete).pack(side="left")
        self.refresh_btn = ttk.Button(header, text="Refresh", command=self.controller.refresh_emails)
        self.refresh_btn.pack(side="left")
        ttk.Button(header, text="Logout", command=self.logout).pack(side="right")

        # Main area
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)
        # Email list
        list_frame = ttk.Frame(main)
        list_frame.pack(side="left", fill="y")
        self.listbox = tk.Listbox(list_frame, width=32)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        # Message body
        body_frame = ttk.Frame(main)
        body_frame.pack(side="right", fill="both", expand=True)
        self.body_text = tk.Text(body_frame, wrap="word")
        self.body_text.pack(fill="both", expand=True)

        # Footer
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=4).pack(fill="x")

    # ViewInterface implementations
    def display_emails(self, emails):
        self.emails = emails
        self.listbox.delete(0, tk.END)
        for i, email in enumerate(emails, start=1):
            self.listbox.insert(tk.END, f"{i}. {email.sender} — {email.subject}")
        if self.selected_email_index is None or self.selected_email_index >= len(emails):
            self.clear_email_content()

    def display_email_content(self, html_content: str):
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert(tk.END, render_html_to_text(html_content))

    def show_status_message(self, message: str):
        self.status_var.set(message)

    def open_compose_window(self, initial_data=None):
        from src.client.frontend.gui.compose_view_tk import ComposeDialog
        data = ComposeDialog(self.root, initial_data or {}).show()
        if data:
            self.controller.send_email(data)

    def clear_email_content(self):
        self.body_text.delete("1.0", tk.END)

    def enable_refresh_button(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.refresh_btn.config(state=state)

    def logout(self):
        self.controller.logout()
        self.root.destroy()

    # Internal callbacks
    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.selected_email_index = sel[0]
        self.controller.select_email(self.selected_email_index)

    def _on_reply(self):
        if self.selected_email_index is not None:
            self.controller.reply_to_email(self.selected_email_index)

    def _on_delete(self):
        if self.selected_email_index is not None:
            if messagebox.askyesno("Delete", "Delete this email?"):
                self.controller.delete_email(self.selected_email_index)

    def run(self):
        self.root.mainloop()
