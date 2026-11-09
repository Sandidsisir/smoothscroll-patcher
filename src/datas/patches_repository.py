"""Patch data for SmoothScroll 1.2.4.0.

The native engine is patched in place with verified byte/string replacements.
The settings GUI is replaced with the cleaned payload shipped in
``src/payload/SmoothScrollGUI.exe``.
"""

from __future__ import annotations

import hashlib
import struct

import pefile

VERSION = "1.2.4.0"

# ---------------------------------------------------------------------------
# Supported native builds
# ---------------------------------------------------------------------------
# The same offsets and strings are present in both known 1.2.4.0 builds.
SUPPORTED_NATIVE_SIZES = {2123800, 2126896}

ORIGINAL_NATIVE_HASHES = {
    "3383927beb6f704e8405f73e10d2c6d01876e2cee7414bfc0fe52d66b92b1aa2":
        "1.2.4.0 (2,123,800 bytes)",
    "634dace41ea8fb775082ab16e5d0ec77760f7bcdf7e27e70a59140bf2ad31e8a":
        "1.2.4.0 (2,126,896 bytes)",
}

PATCHED_NATIVE_HASHES = {
    "4fcffb546f13c3178e7cdbcb113de756ad29fe04fafd6ec3b2c09c8e0b258b81":
        "1.2.4.0 (2,123,800 bytes, clean menu)",
    "8367136026298dbd325c447d13728c84f905e522b5a7f494aab4adbab634b71f":
        "1.2.4.0 (2,126,896 bytes, clean menu)",
}

LEGACY_PATCHED_NATIVE_HASHES = {
    "1f3f74de80633214588247d8f93fb3b751a127659aa273c771066169ce3cb78f":
        "1.2.4.0 (2,123,800 bytes, legacy menu)",
    "93d7ae4db19ddb8ca8688f8ba5307d4351f73808d142608800f3a020a9326133":
        "1.2.4.0 (2,126,896 bytes, legacy menu)",
}

ORIGINAL_GUI_HASHES = {
    "e1ba57d48ac503b0a4e259ed47a30a317231f97bfa39b18674cdd56445e8e182":
        "1.2.4.0",
}

CLEAN_GUI_HASH = "b616c5a4bc3355fcaadf179c2865e8ee20910f2227a20c38f263fb06dedb9184"
CLEAN_GUI_SIZE = 1900032

# ---------------------------------------------------------------------------
# Native byte patches.  Offsets are PE file offsets, not RVAs.
# ---------------------------------------------------------------------------
BYTE_PATCHES = [
    # FUN_14006ad00: force the loaded "has valid license" flag to 1.
    (0x6A369, bytes.fromhex("0F 95 05 40 FE 0F 00"),
     bytes.fromhex("C6 05 40 FE 0F 00 01"),
     "license load flag -> valid"),

    # FUN_14002b790: remove the trial/credential branches so the state is
    # always 1 (valid) and the license GUI is never told the trial expired.
    (0x2ABCF, bytes.fromhex("74 1B"), bytes.fromhex("90 90"),
     "license state branch 1 -> nop"),
    (0x2ABD8, bytes.fromhex("74 12"), bytes.fromhex("90 90"),
     "license state branch 2 -> nop"),
    (0x2ABDF, bytes.fromhex("B8 03 00 00 00"), bytes.fromhex("B8 01 00 00 00"),
     "license state 3 -> 1"),

    # FUN_1400639f0: Google Analytics /collect sender.
    (0x62DF0, b"\x4C", b"\xC3", "telemetry sender -> ret"),
    # FUN_140063250 / FUN_140063520: analytics event builders.
    (0x62650, b"\x40", b"\xC3", "telemetry event builder 1 -> ret"),
    (0x62920, b"\x40", b"\xC3", "telemetry event builder 2 -> ret"),

    # FUN_14000b840: WinSparkle updater initialization.
    (0xAC40, b"\x48", b"\xC3", "updater init -> ret"),

    # FUN_140028dc0: network connectivity check + license timer arming.
    (0x281C0, b"\x48", b"\xC3", "license timer/connectivity -> ret"),

    # FUN_14005faa0: periodic license gate.  Force the "invalid" flag to 1
    # (1 = valid; FUN_14005d7f0 returns flag == 0) and return.
    #   mov byte ptr [rip + 0xE221D], 1 ; ret
    (0x5EEA0, bytes.fromhex("48 8B C4 55 48 8D 68 A1"),
     bytes.fromhex("C6 05 1D 22 0E 00 01 C3"),
     "license gate -> valid + ret"),

    # DAT_140141cc4: the "license invalid" byte read by FUN_14005d7f0.
    (0x1404C4, b"\x01", b"\x01", "license invalid flag data -> 1"),

    # FUN_14005d7f0: always report "not invalid" (return false).
    (0x5CBF0, bytes.fromhex("0F B6 05 CD 44 0E 00 84 C0 0F 94 C0 C3"),
     bytes.fromhex("31 C0 C3 90 90 90 90 90 90 90 90 90 90"),
     "license getter -> false"),

    # FUN_140065440: ShellExecuteW(store URL) "Buy Now" handler.
    (0x64840, b"\x48", b"\xC3", "store launcher -> ret"),
]

# ---------------------------------------------------------------------------
# Native string patches.  (offset, encoding, original, replacement, label)
# Replacement is padded/truncated to the original length so no length field
# or terminator is disturbed.
#
# The three tray-menu labels are handled by patch_menu_resource() instead.
# ---------------------------------------------------------------------------
STRING_PATCHES = [
    # URLs / network endpoints
    (0x107E20, "utf-16le", "https://sites.fastspring.com/smoothscroll/product/smoothscroll-windows?app",
     "", "store URL"),
    (0x10AAA0, "utf-16le", "https://www.smoothscroll.net/win/getting-started/pdf/",
     "", "getting-started PDF URL"),
    (0x10ABC0, "utf-16le", "https://www.smoothscroll.net/win/getting-started/sublime/",
     "", "getting-started Sublime URL"),
    (0x10D1D8, "utf-16le", "www.google-analytics.com", "", "analytics host"),
    (0x10D210, "utf-16le", "/collect", "", "analytics path"),
    (0x107EB8, "ascii", "https://updater.smoothscroll.net/win/updater.xml",
     "", "updater URL"),
    (0x107EF0, "ascii", "https://client.smoothscroll.net/license/validate.php",
     "", "license validation URL"),
    (0x2003B0, "ascii", "https://winsparkle.org/example/appcast.xml",
     "", "WinSparkle example URL"),

    # Support messages
    (0x10BD58, "ascii", " Please contact support@smoothscroll.net",
     " See the local error log", "support message 1"),
    (0x10BD90, "ascii", "Cannot write Options file, Please contact support@smoothscroll.net",
     "Cannot write the Options file.", "support message 2"),
    (0x10BDE0, "ascii", "Options FAILED parsing, Please contact support@smoothscroll.net",
     "Options FAILED parsing.", "support message 3"),

    # Trial / license UI labels
    (0x10D148, "utf-16le", "Trial: %d days left", "SmoothScroll", "trial tooltip"),
    (0x10D170, "utf-16le", "Enter License", "Settings", "enter-license label"),
    (0x10D468, "utf-16le", "SmoothScroll Registered", "SmoothScroll", "registered label"),
    (0x108E90, "utf-16le", "licenseWindow", "settings", "license window arg"),
    (0x108F00, "utf-16le", "trialExpired", "", "trial expired arg"),
    (0x108F20, "utf-16le", "invalidLicense", "", "invalid license arg"),

    # Developer name in the version resource
    (0x200168, "utf-16le", "Bal\u00e1zs Galambosi", "", "version CompanyName"),
    (0x20028E, "utf-16le", "Bal\u00e1zs Galambosi", "", "version LegalCopyright name"),

    # Developer name / address / e-mail in embedded certificate blobs
    (0x204421, "utf-8", "Bal\u00e1zs Galambosi", "", "cert subject name 1"),
    (0x20443D, "utf-8", "Bal\u00e1zs Galambosi", "", "cert subject name 2"),
    (0x205458, "utf-8", "Bal\u00e1zs Galambosi", "", "cert subject name 3"),
    (0x205474, "utf-8", "Bal\u00e1zs Galambosi", "", "cert subject name 4"),
    (0x20440D, "ascii", "Szolo u 4", "", "cert address 1"),
    (0x205444, "ascii", "Szolo u 4", "", "cert address 2"),
    (0x20470B, "ascii", "support@smoothscroll.net", "", "cert e-mail 1"),
    (0x205742, "ascii", "support@smoothscroll.net", "", "cert e-mail 2"),

    # Local build path in the debug directory
    (0x11EDBC, "ascii",
     r"G:\Shared\Dropbox\Projects\WIN\SmoothScroll\x64\Release\SmoothScroll.pdb",
     "SmoothScroll.pdb", "PDB path"),
]

SENSITIVE_TERMS = (
    "google-analytics",
    "fastspring",
    "updater.smoothscroll.net",
    "client.smoothscroll.net",
    "support@smoothscroll.net",
    "Bal\u00e1zs Galambosi",
)

# ---------------------------------------------------------------------------
# Tray menu.  RT_MENU resource id 4.
# ---------------------------------------------------------------------------
MENU_ORIG_ITEMS = [
    (0x0090, None, "POPUP", True),
    (0x0000, 0x0068, "About SmoothScroll", False),
    (0x0000, 0x0000, "", False),
    (0x0000, 0x8019, "Settings...", False),
    (0x0000, 0x0000, "", False),
    (0x0008, 0x801A, "Disable for All Apps", False),
    (0x0000, 0x801D, "Disable for Active App", False),
    (0x0000, 0x0000, "", False),
    (0x0000, 0x8023, "Trial days left", False),
    (0x0000, 0x8022, "Buy Now", False),
    (0x0000, 0x801C, "License", False),
    (0x0000, 0x0000, "", False),
    (0x0080, 0x0069, "Exit SmoothScroll", False),
]

# Drop the Trial days left / Buy Now / License block and its trailing separator.
MENU_KEEP_ITEMS = MENU_ORIG_ITEMS[:8] + MENU_ORIG_ITEMS[12:]


def _enc(text: str, encoding: str) -> bytes:
    return text.encode(encoding)


def _pad_bytes(text: str, encoding: str, length: int) -> bytes:
    raw = _enc(text, encoding)
    if len(raw) > length:
        raise ValueError(f"replacement {text!r} is longer than {length} bytes")
    pad_unit = _enc(" ", encoding)
    pad = pad_unit * ((length - len(raw)) // len(pad_unit))
    return raw + pad


def build_menu(items) -> bytes:
    out = struct.pack("<HH", 0, 0)
    for option, ident, text, popup in items:
        out += struct.pack("<H", option)
        if not popup:
            out += struct.pack("<H", ident)
        out += text.encode("utf-16le") + b"\x00\x00"
    return out


def get_menu_resource(data: bytes):
    """Return (data_entry_offset, data_offset, size, template)."""
    pe = pefile.PE(data=bytes(data))
    entry = None
    for type_entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if type_entry.id != 4:  # RT_MENU
            continue
        if not type_entry.directory:
            continue
        for name_entry in type_entry.directory.entries:
            if name_entry.id != 4:
                continue
            if not name_entry.directory:
                continue
            for lang_entry in name_entry.directory.entries:
                entry = lang_entry
                break
            break
        break

    if entry is None:
        raise RuntimeError("RT_MENU resource 4 not found")

    data_entry_off = entry.data.struct.get_file_offset()
    data_off = pe.get_offset_from_rva(entry.data.struct.OffsetToData)
    size = entry.data.struct.Size
    size_field = struct.unpack_from("<I", data, data_entry_off + 4)[0]
    if size_field != size:
        raise RuntimeError(f"resource size field mismatch: {size_field} != {size}")
    return data_entry_off, data_off, size, bytes(data[data_off:data_off + size])


def menu_is_original(data: bytes) -> bool:
    try:
        _, _, size, template = get_menu_resource(data)
        expected = build_menu(MENU_ORIG_ITEMS)
        return size == len(expected) and template == expected
    except Exception:
        return False


def menu_is_clean(data: bytes) -> bool:
    try:
        _, _, size, template = get_menu_resource(data)
        expected = build_menu(MENU_KEEP_ITEMS)
        return size == len(expected) and template == expected
    except Exception:
        return False


def patch_menu_resource(data: bytearray) -> tuple[int, int]:
    """Remove the trial/buy/license rows from the tray menu template.

    Returns (old_size, new_size).  The file size does not change; the old tail
    of the resource is zero-filled and the resource data-entry size is updated.
    """
    data_entry_off, data_off, old_size, template = get_menu_resource(data)
    old_menu = build_menu(MENU_ORIG_ITEMS)
    if template != old_menu:
        raise RuntimeError("tray menu template does not match supported original")

    new_menu = build_menu(MENU_KEEP_ITEMS)
    if len(new_menu) >= old_size:
        raise RuntimeError("tray menu template did not shrink")

    data[data_off:data_off + len(new_menu)] = new_menu
    data[data_off + len(new_menu):data_off + old_size] = b"\x00" * (old_size - len(new_menu))
    struct.pack_into("<I", data, data_entry_off + 4, len(new_menu))

    # Verify both the template and the resource size field.
    check_entry_off, check_data_off, check_size, check_template = get_menu_resource(data)
    if check_entry_off != data_entry_off or check_data_off != data_off:
        raise RuntimeError("tray menu resource moved unexpectedly")
    if check_size != len(new_menu) or check_template != new_menu:
        raise RuntimeError("tray menu write verification failed")

    return old_size, len(new_menu)


def native_state(data: bytes) -> str:
    """Return original / patched / patched_legacy / unknown."""
    digest = hashlib.sha256(data).hexdigest()
    if digest in ORIGINAL_NATIVE_HASHES:
        return "original"
    if digest in PATCHED_NATIVE_HASHES:
        return "patched"
    if digest in LEGACY_PATCHED_NATIVE_HASHES:
        return "patched_legacy"

    if len(data) not in SUPPORTED_NATIVE_SIZES:
        return "unknown"

    # Structural fallback: verify every original byte/string and the menu.
    original_ok = True
    for off, expected, _, _ in BYTE_PATCHES:
        if data[off:off + len(expected)] != expected:
            original_ok = False
            break
    if original_ok:
        for off, encoding, old, _, _ in STRING_PATCHES:
            expected = _enc(old, encoding)
            if data[off:off + len(expected)] != expected:
                original_ok = False
                break
    if original_ok and menu_is_original(data):
        return "original"

    patched_ok = True
    for off, _, replacement, _ in BYTE_PATCHES:
        if data[off:off + len(replacement)] != replacement:
            patched_ok = False
            break
    if patched_ok:
        for off, encoding, old, _, _ in STRING_PATCHES:
            expected = _enc(old, encoding)
            if data[off:off + len(expected)] == expected:
                patched_ok = False
                break
    if patched_ok and menu_is_clean(data):
        return "patched"

    return "unknown"


def apply_native_patches(data: bytes) -> tuple[bytes, int, int, list[str]]:
    """Apply the native patches and return (patched, old_menu_size, new_menu_size, warnings)."""
    original_size = len(data)
    patched = bytearray(data)

    old_menu_size, new_menu_size = patch_menu_resource(patched)

    for off, expected, replacement, label in BYTE_PATCHES:
        actual = bytes(patched[off:off + len(expected)])
        if actual != expected:
            raise RuntimeError(
                f"{label}: expected {expected.hex(' ')} at {off:#x}, found {actual.hex(' ')}"
            )
        patched[off:off + len(replacement)] = replacement

    for off, encoding, old, new, label in STRING_PATCHES:
        expected = _enc(old, encoding)
        actual = bytes(patched[off:off + len(expected)])
        if actual != expected:
            raise RuntimeError(
                f"{label}: expected {old!r} at {off:#x}, found {actual!r}"
            )
        patched[off:off + len(expected)] = _pad_bytes(new, encoding, len(expected))

    if len(patched) != original_size:
        raise RuntimeError("native patch changed the file size")

    pe = pefile.PE(data=bytes(patched), fast_load=True)
    if pe.FILE_HEADER.Machine != 0x8664:
        raise RuntimeError("patched file is not an x86-64 PE")

    warnings = []
    for term in SENSITIVE_TERMS:
        for encoding in ("ascii", "utf-16le", "utf-8"):
            try:
                needle = term.encode(encoding)
            except UnicodeEncodeError:
                continue
            if needle in patched:
                warnings.append(f"{term!r} still present as {encoding}")

    return bytes(patched), old_menu_size, new_menu_size, warnings
