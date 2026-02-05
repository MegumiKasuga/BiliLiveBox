import tkinter as tk

class LoginWindow(tk.Toplevel):

    def __init__(self, qrcode, master=None):
        super().__init__(master)
        self.title("Please scan the qr_code to Login")
        self.geometry("300x200")
