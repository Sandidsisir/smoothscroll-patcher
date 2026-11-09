import os
import sys
from tkinter import messagebox

import customtkinter as ctk

from src.patcher import Patcher
from src.widgets import Controllers, EventViewer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

HEIGHT = 420
WIDTH = 520

INFO_TEXT = (
    "SmoothScroll Patcher 1.2.4.0\n\n"
    "Patches the native SmoothScroll.exe engine and installs the cleaned "
    "settings GUI.\n\n"
    "Supported native builds:\n"
    "  - 2,123,800 bytes\n"
    "  - 2,126,896 bytes\n\n"
    "Backups are stored in:\n"
    "%LOCALAPPDATA%\\SmoothScroll\\patcher-backups\n\n"
    "Use Checkup first, then Patch. Restore reverts the newest backup."
)


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("SmoothScroll Patcher")
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.minsize(480, 380)
        self.is_compiled = getattr(sys, "frozen", False)
        self.assets_path = (
            os.path.join(sys._MEIPASS, "assets")
            if self.is_compiled
            else os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        )
        self.icon_path = os.path.join(self.assets_path, "icon.ico")
        try:
            self.iconbitmap(self.icon_path)
        except Exception:
            pass

        self.setup_widgets()
        self.patcher = Patcher(self.controllers.backup_checkbox_state, self.event_viewer)
        self.after(300, self.checkup_btn_cmd)

    def setup_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="SmoothScroll Patcher",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")

        info_btn = ctk.CTkButton(
            header,
            text="Info",
            width=52,
            height=26,
            font=("Segoe UI", 12),
            command=self.info_btn_cmd,
        )
        info_btn.grid(row=0, column=1, sticky="e")

        self.event_viewer = EventViewer(self)
        self.event_viewer.grid(row=1, column=0, sticky="nsew", padx=10, pady=(8, 0))

        self.controllers = Controllers(
            self,
            select_btn_cmd=self.select_btn_cmd,
            restore_btn_cmd=self.restore_btn_cmd,
            patch_btn_cmd=self.patch_btn_cmd,
            checkup_btn_cmd=self.checkup_btn_cmd,
        )
        self.controllers.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    def info_btn_cmd(self) -> None:
        messagebox.showinfo("SmoothScroll Patcher", INFO_TEXT, parent=self)

    def checkup_btn_cmd(self) -> None:
        self.patcher.checkup()
        self._refresh_patch_btn()

    def select_btn_cmd(self) -> None:
        if self.patcher.select_file():
            self.patcher.checkup()
            self._refresh_patch_btn()

    def patch_btn_cmd(self) -> None:
        self.patcher.patch()
        self._refresh_patch_btn()

    def restore_btn_cmd(self) -> None:
        self.patcher.restore()
        self._refresh_patch_btn()

    def _refresh_patch_btn(self) -> None:
        state = "normal" if self.patcher.checkup_is_valid else "disabled"
        self.controllers.set_patch_btn_state(state)
