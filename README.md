# SmoothScroll Patcher

[![Build](https://github.com/Sandidsisir/smoothscroll-patcher/actions/workflows/build.yml/badge.svg)](https://github.com/Sandidsisir/smoothscroll-patcher/actions/workflows/build.yml)

A standalone Windows patcher for **SmoothScroll 1.2.4.0**, modeled on the
PyPass-SAB patcher flow:

- **Checkup** - locate and verify the installed app.
- **Backup** - timestamped copy of the native engine and settings GUI.
- **Patch** - remove the license/trial logic, telemetry, updater, store links,
  vendor URLs/e-mails/developer strings, and trial/license tray-menu rows.
- **Restore** - put the newest backup back.

The native engine is patched in place. The settings GUI is replaced with the
cleaned `SmoothScrollGUI.exe` payload bundled in this patcher; the original GUI
is backed up first.

## Supported builds

The patcher accepts either known pristine 1.2.4.0 native engine:

| Native size | Original SHA-256 |
|---|---|
| 2,123,800 bytes | `3383927beb6f704e8405f73e10d2c6d01876e2cee7414bfc0fe52d66b92b1aa2` |
| 2,126,896 bytes | `634dace41ea8fb775082ab16e5d0ec77760f7bcdf7e27e70a59140bf2ad31e8a` |

Every byte and string is verified before anything is written. A different
version or an unknown build is refused. If the native engine is already
patched, the native patch is skipped; the patcher can still replace the
settings GUI if it is original. Use Restore or a pristine copy to get the
clean tray menu.

Patched output hashes:

| Native size | Patched SHA-256 |
|---|---|
| 2,123,800 bytes | `4fcffb546f13c3178e7cdbcb113de756ad29fe04fafd6ec3b2c09c8e0b258b81` |
| 2,126,896 bytes | `8367136026298dbd325c447d13728c84f905e522b5a7f494aab4adbab634b71f` |

## What is removed

Native engine (`SmoothScroll.exe`):

- license/trial validation and the periodic license gate;
- Google Analytics telemetry entry points;
- WinSparkle updater initialization and updater URL;
- store/"Buy Now" launcher and store URL;
- license server URL, getting-started URLs, support e-mail addresses;
- trial/license UI strings;
- developer name, address, and e-mail from the version resource and embedded
  certificate blobs;
- local build path in the debug directory;
- the **Trial days left**, **Buy Now**, and **License** tray-menu rows (the
  menu template is rebuilt and shrunk from 324 to 242 bytes).

Settings GUI (`SmoothScrollGUI.exe`):

- license/trial forms and panels;
- license window entry point and links;
- vendor links, About placeholder, and related UI entries.

The app logo/icons are not changed.

## Usage

1. Close SmoothScroll if it is running.
2. Run `SmoothScroll-Patcher.exe` (or `python main.py`).
3. Click **Checkup**. The patcher auto-detects the installed app in
   `%LOCALAPPDATA%\SmoothScroll\app-*\SmoothScroll.exe` or under
   `C:\Program Files\SmoothScroll`.
4. If the auto-detected file is not the one you want, click **Select** and
   choose the pristine `SmoothScroll.exe`.
5. Leave **Backup** checked and click **Patch**.
6. To revert, click **Restore**. It uses the newest backup for the selected
   app in `%LOCALAPPDATA%\SmoothScroll\patcher-backups`.

If Checkup reports **Patched (legacy menu)**, the native engine has an older
patch and cannot be re-patched in place. Select a pristine 1.2.4.0
`SmoothScroll.exe` (or restore/reinstall first) to apply the clean tray menu.
The settings GUI can still be replaced independently when it is original.

The patcher normally runs without elevation because the app is per-user. If
SmoothScroll is installed under `Program Files`, run the patcher as
administrator (or start it with `--elevate`).

## Build locally

```powershell
python -m pip install -r requirements.txt
python build.py
```

The executable is written to `dist\SmoothScroll-Patcher.exe`, with a matching
`dist\SmoothScroll-Patcher.exe.sha256`.

## Build on GitHub

The repository includes a **Build** workflow in
`.github/workflows/build.yml`.

1. Open the **Actions** tab.
2. Select **Build**.
3. Click **Run workflow**.
4. Download the `SmoothScroll-Patcher` artifact from the run.

Pushing a tag such as `v1.0.0` also builds the executable and publishes it as a
GitHub Release together with the SHA-256 file.

## Layout

```
main.py                         entry point
build.py                        PyInstaller build + checksum
.github/workflows/build.yml     GitHub Actions Build workflow
src/app.py                      customtkinter UI
src/patcher.py                  locate / checkup / backup / patch / restore
src/datas/patches_repository.py verified native patches + tray-menu rewrite
src/widgets/                    event log and controls
src/assets/icon.ico             app icon
src/payload/SmoothScrollGUI.exe cleaned settings GUI payload
```
