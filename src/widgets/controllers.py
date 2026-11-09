import customtkinter as ctk


class Controllers(ctk.CTkFrame):

    def __init__(self, master=None, select_btn_cmd=None, restore_btn_cmd=None,
                 patch_btn_cmd=None, checkup_btn_cmd=None, **kwargs):
        super().__init__(master=master, border_width=0, **kwargs)
        self.select_btn_cmd = select_btn_cmd
        self.restore_btn_cmd = restore_btn_cmd
        self.patch_btn_cmd = patch_btn_cmd
        self.checkup_btn_cmd = checkup_btn_cmd
        self.init_widgets()

    def init_widgets(self) -> None:
        self.backup_checkbox = ctk.CTkCheckBox(self, text="Backup")
        self.backup_checkbox.grid(row=0, column=0, sticky="w", padx=(5, 8), pady=5)

        self.select_btn = self._create_btn("Select", self.select_btn_cmd, 0, 1)
        self.restore_btn = self._create_btn("Restore", self.restore_btn_cmd, 0, 2)
        self.checkup_btn = self._create_btn("Checkup", self.checkup_btn_cmd, 0, 3)
        self.patch_btn = self._create_btn("Patch", self.patch_btn_cmd, 0, 4, state="disabled")

        self.backup_checkbox.select()
        self.columnconfigure(0, weight=1)

    def _create_btn(self, text, command, row, column, state="normal", width=82) -> ctk.CTkButton:
        btn = ctk.CTkButton(self, text=text, command=command, state=state, width=width,
                            font=("Segoe UI", 12))
        btn.grid(row=row, column=column, sticky="e", padx=4, pady=5)
        return btn

    def backup_checkbox_state(self) -> bool:
        """Return True if the user wants a backup before patching."""
        return bool(self.backup_checkbox.get())

    def set_patch_btn_state(self, state: str) -> None:
        self.patch_btn.configure(state=state)
