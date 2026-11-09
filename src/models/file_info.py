from src.models.base_model import BaseModel


class FileInfo(BaseModel):
    path: str = ""
    hash: str = ""
    size: int = 0
    state: str = "unknown"
    version: str = ""
    gui_path: str = ""
    gui_hash: str = ""
    gui_size: int = 0
    gui_state: str = "missing"

    def native_is_original(self) -> bool:
        return self.state == "original"

    def native_is_patched(self) -> bool:
        return self.state in ("patched", "patched_legacy")

    def gui_is_original(self) -> bool:
        return self.gui_state == "original"

    def gui_is_patched(self) -> bool:
        return self.gui_state == "patched"
