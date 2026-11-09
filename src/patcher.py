from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from tkinter import filedialog

import psutil

from src.datas import (
    CLEAN_GUI_HASH,
    ORIGINAL_GUI_HASHES,
    PATCHED_NATIVE_HASHES,
    VERSION,
    apply_native_patches,
    native_state,
)
from src.models import FileInfo


class Patcher:
    """Locate, verify, patch, back up and restore a SmoothScroll installation."""

    def __init__(self, do_backup_func, ev, backup_root: str | None = None):
        self.ev = ev
        self._do_backup_func = do_backup_func
        self.checkup_is_valid = False
        self.already_patched = False
        self.check_file_result = FileInfo()

        self._native_path = ""
        self._gui_path = ""
        self._app_dir = ""
        self._backup_root = backup_root or os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "SmoothScroll",
            "patcher-backups",
        )
        self._payload_path = self._resource_path(os.path.join("payload", "SmoothScrollGUI.exe"))

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    @staticmethod
    def _resource_path(relative: str) -> str:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return os.path.join(base, relative)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)

    def _set_paths(self, native_path: str) -> None:
        self._native_path = os.path.abspath(native_path)
        self._app_dir = os.path.dirname(self._native_path)
        self._gui_path = os.path.join(self._app_dir, "SmoothScrollGUI.exe")

    def _find_install(self) -> str:
        local = os.environ.get("LOCALAPPDATA") or ""
        active = []
        backups = []

        if local:
            active += sorted(
                glob.glob(os.path.join(local, "SmoothScroll", "app-*", "SmoothScroll.exe")),
                reverse=True,
            )
            backups += sorted(
                glob.glob(os.path.join(local, "SmoothScroll", "orig_backup-*", "SmoothScroll.exe")),
                reverse=True,
            )

        active += [
            r"C:\Program Files\SmoothScroll\SmoothScroll.exe",
            r"C:\Program Files (x86)\SmoothScroll\SmoothScroll.exe",
            os.path.join(os.getcwd(), "app", "SmoothScroll.exe"),
        ]

        for candidate in active + backups:
            if os.path.isfile(candidate):
                return candidate
        return ""

    def select_file(self) -> bool:
        initial = self._app_dir or os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            "SmoothScroll",
        )
        selected = filedialog.askopenfilename(
            title="Select SmoothScroll.exe",
            initialdir=initial if os.path.isdir(initial) else os.path.expanduser("~"),
            filetypes=[
                ("SmoothScroll engine", "SmoothScroll.exe"),
                ("Executable files", "*.exe"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return False
        self._set_paths(selected)
        return True

    # ------------------------------------------------------------------
    # Checkup
    # ------------------------------------------------------------------
    def checkup(self) -> None:
        self.checkup_is_valid = False
        self.already_patched = False
        self.check_file_result = FileInfo()
        self.ev.add_banner("Checkup")

        if not self._native_path or not os.path.isfile(self._native_path):
            self.ev.event("Searching for SmoothScroll.exe... ")
            found = self._find_install()
            if found:
                self._set_paths(found)
                self.ev.event_done("Found")
            else:
                self.ev.event_error("Not found")
                if not self.select_file():
                    self.ev.event_error("Cancelled")
                    return

        self.ev.event(f"{self._native_path}\n", color="blue")

        data = self._read_file(self._native_path)
        if data is None:
            self.ev.event_error("Unable to read the native engine")
            return

        digest = self._sha256_bytes(data)
        state = native_state(data)
        self.check_file_result = FileInfo(
            path=self._native_path,
            hash=digest,
            size=len(data),
            state=state,
            version=VERSION,
            gui_path=self._gui_path,
        )

        self.ev.event("Checking native engine... ")
        if state == "original":
            self.ev.event_done("Original")
        elif state == "patched":
            self.ev.event_done("Patched")
        elif state == "patched_legacy":
            self.ev.event_warning("Patched (legacy menu)")
        else:
            self.ev.event_error("Unsupported / unknown")

        self.ev.event(f"  size: {len(data):,} bytes\n")
        self.ev.event(f"  sha256: {digest}\n", color="grey")

        gui_state = "missing"
        gui_hash = ""
        gui_size = 0
        if os.path.isfile(self._gui_path):
            gui_data = self._read_file(self._gui_path)
            if gui_data is not None:
                gui_hash = self._sha256_bytes(gui_data)
                gui_size = len(gui_data)
                gui_state = self._gui_state(gui_hash)
            self.ev.event("Checking settings GUI... ")
            if gui_state == "original":
                self.ev.event_done("Original")
            elif gui_state == "patched":
                self.ev.event_done("Patched")
            elif gui_state == "unknown":
                self.ev.event_warning("Unknown (will be backed up and replaced)")
            else:
                self.ev.event_error("Unreadable")
            self.ev.event(f"  sha256: {gui_hash}\n", color="grey")
        else:
            self.ev.event_warning("SmoothScrollGUI.exe not found; native-only patch")

        self.check_file_result.gui_hash = gui_hash
        self.check_file_result.gui_size = gui_size
        self.check_file_result.gui_state = gui_state

        if state == "original":
            self.checkup_is_valid = True
        elif state in ("patched", "patched_legacy"):
            self.checkup_is_valid = gui_state in ("original", "unknown")
            self.already_patched = gui_state == "patched"
        else:
            self.checkup_is_valid = False

        if self.checkup_is_valid:
            self.ev.event_done("Ready to patch")
        elif self.already_patched:
            self.ev.event_warning("Already patched. Use Restore to revert, or Select another file.")
        else:
            self.ev.event_error("Patch not available for this build.")

    @staticmethod
    def _gui_state(gui_hash: str) -> str:
        if gui_hash == CLEAN_GUI_HASH:
            return "patched"
        if gui_hash in ORIGINAL_GUI_HASHES:
            return "original"
        return "unknown"

    # ------------------------------------------------------------------
    # Patch
    # ------------------------------------------------------------------
    def patch(self) -> bool:
        self.ev.add_banner("Patching")
        if not self.checkup_is_valid:
            self.ev.event_error("Checkup is not valid.")
            return False

        backup_dir = None
        if self._do_backup_func():
            try:
                backup_dir = self._create_backup()
            except Exception as exc:
                self.ev.event_error(f"Backup failed: {exc}")
                return False
        else:
            self.ev.event_warning("Backup disabled")

        self._kill_processes("SmoothScroll.exe", "SmoothScrollGUI.exe")

        original_native = None
        original_gui = None
        native_written = False
        gui_written = False

        try:
            native_data = self._read_file(self._native_path)
            if native_data is None:
                raise RuntimeError("cannot read the native engine")

            state = native_state(native_data)
            if state == "original":
                original_native = native_data
                self.ev.event("Applying native patches... ")
                patched, old_menu, new_menu, warnings = apply_native_patches(native_data)
                self.ev.event_done("Done")
                self.ev.event(f"  tray menu: {old_menu} -> {new_menu} bytes\n")
                for warning in warnings:
                    self.ev.event_warning(f"  {warning}\n")

                if not self._write_file(self._native_path, patched):
                    raise RuntimeError("cannot write the native engine")
                native_written = True

                new_hash = self._sha256_bytes(patched)
                if new_hash not in PATCHED_NATIVE_HASHES:
                    raise RuntimeError(f"patched engine hash is unexpected: {new_hash}")
                if native_state(patched) != "patched":
                    raise RuntimeError("patched engine failed verification")
                self.ev.event_done(f"  native sha256: {new_hash}\n")
            elif state in ("patched", "patched_legacy"):
                self.ev.event_warning("Native engine already patched; skipping")
            else:
                raise RuntimeError("native engine is not a supported original")

            if os.path.isfile(self._gui_path):
                original_gui = self._read_file(self._gui_path)
                gui_hash = self._sha256_file(self._gui_path)
                if gui_hash == CLEAN_GUI_HASH:
                    self.ev.event_warning("Settings GUI already patched; skipping")
                else:
                    self.ev.event("Installing cleaned settings GUI... ")
                    if not os.path.isfile(self._payload_path):
                        raise RuntimeError("bundled SmoothScrollGUI.exe payload is missing")
                    payload = self._read_file(self._payload_path)
                    if payload is None:
                        raise RuntimeError("cannot read the bundled GUI payload")
                    if self._sha256_bytes(payload) != CLEAN_GUI_HASH:
                        raise RuntimeError("bundled GUI payload hash is wrong")
                    if not self._write_file(self._gui_path, payload):
                        raise RuntimeError("cannot write SmoothScrollGUI.exe")
                    gui_written = True
                    if self._sha256_file(self._gui_path) != CLEAN_GUI_HASH:
                        raise RuntimeError("installed GUI failed verification")
                    self.ev.event_done("Done")
            else:
                self.ev.event_warning("SmoothScrollGUI.exe not found; native-only patch")

            self._ensure_gui_dependencies()
            self.ev.event_done("Patch complete")
            self.checkup()
            return True
        except Exception as exc:
            self.ev.event_error(f"Patch failed: {exc}")
            if backup_dir:
                self.ev.event_warning("Rolling back from backup...")
                try:
                    self._restore_backup_dir(backup_dir)
                    self.ev.event_done("Rollback complete")
                except Exception as restore_exc:
                    self.ev.event_error(f"Rollback failed: {restore_exc}")
            else:
                if native_written and original_native is not None:
                    self.ev.event_warning("Rolling back the native engine...")
                    self._write_file(self._native_path, original_native)
                if gui_written and original_gui is not None:
                    self.ev.event_warning("Rolling back the settings GUI...")
                    self._write_file(self._gui_path, original_gui)
            self.checkup()
            return False

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------
    def restore(self) -> bool:
        self.ev.add_banner("Restore")
        backup_dir = self._latest_backup()
        if not backup_dir:
            self.ev.event_error("No backup found.")
            return False

        self.ev.event(f"Using backup: {backup_dir}\n", color="blue")
        self._kill_processes("SmoothScroll.exe", "SmoothScrollGUI.exe")
        try:
            self._restore_backup_dir(backup_dir)
            self.ev.event_done("Restore complete")
            manifest_path = os.path.join(backup_dir, "manifest.json")
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            app_dir = manifest.get("app_dir") or self._app_dir
            self._set_paths(os.path.join(app_dir, "SmoothScroll.exe"))
            self.checkup()
            return True
        except Exception as exc:
            self.ev.event_error(f"Restore failed: {exc}")
            return False

    def _latest_backup(self) -> str | None:
        if not os.path.isdir(self._backup_root):
            return None
        candidates = [
            os.path.join(self._backup_root, name)
            for name in os.listdir(self._backup_root)
            if os.path.isdir(os.path.join(self._backup_root, name))
        ]
        candidates.sort(reverse=True)

        current_app = os.path.normcase(os.path.abspath(self._app_dir)) if self._app_dir else ""
        matching = []
        fallback = []
        for candidate in candidates:
            manifest_path = os.path.join(candidate, "manifest.json")
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as fh:
                    manifest = json.load(fh)
            except (OSError, ValueError):
                continue
            fallback.append(candidate)
            app_dir = manifest.get("app_dir", "")
            if current_app and os.path.normcase(os.path.abspath(app_dir)) == current_app:
                matching.append(candidate)

        if matching:
            return matching[0]
        return fallback[0] if fallback else None

    def _create_backup(self) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = os.path.join(self._backup_root, stamp)
        suffix = 1
        while os.path.exists(backup_dir):
            suffix += 1
            backup_dir = os.path.join(self._backup_root, f"{stamp}-{suffix}")
        os.makedirs(backup_dir, exist_ok=False)

        manifest = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "version": VERSION,
            "app_dir": self._app_dir,
            "files": {},
        }

        for path in (self._native_path, self._gui_path):
            if not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            destination = os.path.join(backup_dir, name)
            shutil.copy2(path, destination)
            manifest["files"][name] = {
                "sha256": self._sha256_file(path),
                "size": os.path.getsize(path),
            }

        with open(os.path.join(backup_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        self.ev.event_done(f"Backup: {backup_dir}")
        return backup_dir

    def _restore_backup_dir(self, backup_dir: str) -> None:
        manifest_path = os.path.join(backup_dir, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)

        app_dir = manifest.get("app_dir") or self._app_dir
        if not os.path.isdir(app_dir):
            raise RuntimeError(f"original app folder not found: {app_dir}")

        for name, info in manifest.get("files", {}).items():
            source = os.path.join(backup_dir, name)
            destination = os.path.join(app_dir, name)
            if not os.path.isfile(source):
                raise RuntimeError(f"backup file missing: {source}")
            shutil.copy2(source, destination)
            if self._sha256_file(destination) != info["sha256"]:
                raise RuntimeError(f"restored file hash mismatch: {name}")
            self.ev.event_done(f"  restored {name}")

    # ------------------------------------------------------------------
    # Process / file helpers
    # ------------------------------------------------------------------
    def _kill_processes(self, *names: str) -> None:
        self.ev.event(f"Closing {', '.join(names)}... ")
        for name in names:
            subprocess.run(
                ["taskkill", "/F", "/IM", name, "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        deadline = time.time() + 8
        while time.time() < deadline:
            alive = []
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info.get("name") in names:
                        alive.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if not alive:
                self.ev.event_done("Done")
                return
            for proc in alive:
                try:
                    proc.wait(timeout=0.5)
                except (psutil.TimeoutExpired, psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        self.ev.event_warning("Processes may still be running")

    @staticmethod
    def _read_file(path: str) -> bytes | None:
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError:
            return None

    @staticmethod
    def _write_file(path: str, data: bytes) -> bool:
        tmp = path + ".patcher-tmp"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
            return True
        except OSError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return False

    @staticmethod
    def _sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def _sha256_file(cls, path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _ensure_gui_dependencies(self) -> None:
        required = ["System.Resources.Extensions.dll"]
        payload_dir = os.path.dirname(self._payload_path)
        for name in required:
            destination = os.path.join(self._app_dir, name)
            if os.path.isfile(destination):
                continue
            source = os.path.join(payload_dir, name)
            if not os.path.isfile(source):
                self.ev.event_warning(f"{name} not found; the settings GUI may not start")
                continue
            try:
                shutil.copy2(source, destination)
                self.ev.event_done(f"Installed missing dependency: {name}")
            except OSError as exc:
                self.ev.event_warning(f"Could not install {name}: {exc}")
