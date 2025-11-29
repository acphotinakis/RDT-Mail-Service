import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from src.client.frontend.controllers.app_controller_rich import AppController, ViewInterface
from src.client.frontend.gui.message_view_tk import render_html_to_text
from src.client.frontend.gui.compose_view_tk import ComposeDialog
from src.client.frontend.models.email_data import EmailData
from src.common.logger import get_class_logger


class MainWindowTk(ViewInterface):
    """Tkinter-based UI for the email client."""

    def __init__(self, username: str, password: str):
        self.root = tk.Tk()
        self.root.title("Email Client")
        self.root.geometry("950x600")
        self.root.minsize(800, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.logout)

        self.log = get_class_logger(self)
        self.emails: List[EmailData] = []
        self.selected_email_index: Optional[int] = None

        self.status_var = tk.StringVar(value="Ready")
        self.refresh_btn: ttk.Button
        self.listbox: tk.Listbox
        self.body_text: tk.Text

        self._build_layout()

        self.controller = AppController(self, username, password)
        self.controller.load_user_emails(self.controller.user)

    # ===== Layout =====
    def _build_layout(self):
        header = ttk.Frame(self.root, padding=8)
        header.pack(fill="x")

        ttk.Button(header, text="Compose", command=self.open_compose_window).pack(side="left", padx=(0, 4))
        ttk.Button(header, text="Reply", command=self._on_reply).pack(side="left", padx=(0, 4))
        ttk.Button(header, text="Delete", command=self._on_delete).pack(side="left", padx=(0, 4))

        self.refresh_btn = ttk.Button(header, text="Refresh", command=self.controller.refresh_emails)
        self.refresh_btn.pack(side="left", padx=(0, 4))

        ttk.Button(header, text="Logout", command=self.logout).pack(side="right")

        # Main split area
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        # Email list panel
        list_frame = ttk.Frame(main)
        list_frame.pack(side="left", fill="y")

        list_label = ttk.Label(list_frame, text="Inbox", font=("TkDefaultFont", 11, "bold"))
        list_label.pack(anchor="w", pady=(0, 4))

        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill="y", expand=True)

        self.listbox = tk.Listbox(listbox_frame, width=40, activestyle="none")
        self.listbox.pack(side="left", fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        list_scroll = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=list_scroll.set)

        # Message body panel
        body_frame = ttk.Frame(main)
        body_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        body_label = ttk.Label(body_frame, text="Message", font=("TkDefaultFont", 11, "bold"))
        body_label.pack(anchor="w", pady=(0, 4))

        text_frame = ttk.Frame(body_frame)
        text_frame.pack(fill="both", expand=True)

        self.body_text = tk.Text(text_frame, wrap="word")
        self.body_text.pack(side="left", fill="both", expand=True)
        self.body_text.config(state="disabled")

        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.body_text.yview)
        text_scroll.pack(side="right", fill="y")
        self.body_text.config(yscrollcommand=text_scroll.set)

        # Footer/status
        status = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=6, relief="sunken")
        status.pack(fill="x", side="bottom")

    # ===== ViewInterface methods =====
    def display_emails(self, emails: List[EmailData]):
        self.emails = emails
        self.listbox.delete(0, tk.END)
        for i, email in enumerate(emails, start=1):
            self.listbox.insert(tk.END, f"{i}. {email.sender} — {email.subject}")

        if self.selected_email_index is None or self.selected_email_index >= len(emails):
            self.selected_email_index = None
            self.clear_email_content()
        else:
            # Reselect to keep highlight on refresh
            self.listbox.selection_set(self.selected_email_index)

    def display_email_content(self, html_content: str):
        self.body_text.config(state="normal")
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert(tk.END, render_html_to_text(html_content))
        self.body_text.config(state="disabled")

    def show_status_message(self, message: str):
        self.status_var.set(message)

    def open_compose_window(self, initial_data: Optional[dict] = None):
        self.log.debug("Opening compose window")
        dialog = ComposeDialog(self.root, initial_data or {})
        data = dialog.show()
        if data:
            self.controller.send_email(data)

    def clear_email_content(self):
        self.body_text.config(state="normal")
        self.body_text.delete("1.0", tk.END)
        self.body_text.config(state="disabled")

    def enable_refresh_button(self, enabled: bool):
        self.refresh_btn.config(state="normal" if enabled else "disabled")

    def logout(self):
        self.controller.logout()
        self.root.destroy()

    def run_on_ui_thread(self, func, *args, **kwargs):
        """Schedule a callback on the Tkinter event loop."""
        self.root.after(0, lambda: func(*args, **kwargs))

    # ===== Internal callbacks =====
    def _on_select(self, _event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected_email_index = selection[0]
        self.controller.select_email(self.selected_email_index)

    def _on_reply(self):
        if self.selected_email_index is None:
            messagebox.showinfo("Reply", "Select an email first.")
            return
        self.controller.reply_to_email(self.selected_email_index)

    def _on_delete(self):
        if self.selected_email_index is None:
            messagebox.showinfo("Delete", "Select an email first.")
            return
        if messagebox.askyesno("Delete", "Delete this email?"):
            self.controller.delete_email(self.selected_email_index)

    def run(self):
        self.root.mainloop()
