import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, Dict


class LoginDialog:
    """Simple login dialog using Tkinter."""

    def __init__(self, error_message: Optional[str] = None):
        self.error_message = error_message
        self.result: Optional[Tuple[str, str]] = None

    def run(self) -> Optional[Tuple[str, str]]:
        root = tk.Tk()
        root.title("Login")
        root.geometry("360x220")

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Login", font=("TkDefaultFont", 12, "bold")).pack()
        self.error_var = tk.StringVar(value=self.error_message or "")
        ttk.Label(frame, textvariable=self.error_var, foreground="red").pack()

        ttk.Label(frame, text="Username").pack(anchor="w", pady=(8, 0))
        username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=username_var).pack(fill="x")

        ttk.Label(frame, text="Password").pack(anchor="w", pady=(8, 0))
        password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=password_var, show="*").pack(fill="x")

        button_row = ttk.Frame(frame)
        button_row.pack(pady=12)
        ttk.Button(
            button_row, text="Login", command=lambda: self._submit(root, username_var, password_var)
        ).pack()

        root.mainloop()
        return self.result

    def _submit(self, root, username_var, password_var):
        username = username_var.get().strip()
        password = password_var.get().strip()

        if not username or not password:
            self.error_var.set("Both fields are required.")
            return

        self.result = (username, password)
        root.destroy()


class SignupDialog:
    """Signup dialog with password confirmation."""

    def __init__(self, error_message: Optional[str] = None):
        self.error_message = error_message
        self.result: Optional[Dict[str, str]] = None

    def run(self) -> Optional[Dict[str, str]]:
        root = tk.Tk()
        root.title("Sign Up")
        root.geometry("360x260")

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Create Account", font=("TkDefaultFont", 12, "bold")).pack()
        self.error_var = tk.StringVar(value=self.error_message or "")
        ttk.Label(frame, textvariable=self.error_var, foreground="red").pack()

        ttk.Label(frame, text="Username").pack(anchor="w", pady=(8, 0))
        username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=username_var).pack(fill="x")

        ttk.Label(frame, text="Password").pack(anchor="w", pady=(8, 0))
        password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=password_var, show="*").pack(fill="x")

        ttk.Label(frame, text="Confirm Password").pack(anchor="w", pady=(8, 0))
        confirm_var = tk.StringVar()
        ttk.Entry(frame, textvariable=confirm_var, show="*").pack(fill="x")

        button_row = ttk.Frame(frame)
        button_row.pack(pady=12)
        ttk.Button(
            button_row,
            text="Sign Up",
            command=lambda: self._submit(root, username_var, password_var, confirm_var),
        ).pack()

        root.mainloop()
        return self.result

    def _submit(self, root, username_var, password_var, confirm_var):
        username = username_var.get().strip()
        password = password_var.get().strip()
        confirm = confirm_var.get().strip()

        if not username or not password or not confirm:
            self.error_var.set("All fields are required.")
            return

        if password != confirm:
            self.error_var.set("Passwords do not match.")
            return

        self.result = {"user": username, "password": password}
        root.destroy()
