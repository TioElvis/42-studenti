"""Defensive checks for files students upload to Materiale / Archivio.

Layers, cheapest first: filename rules, an extension allow-list and a content
check (magic bytes / text decoding / ZIP and PDF inspection). Anything suspicious
raises :class:`UploadRejected` carrying an HTTP status and an Italian message.

This is defence in depth, not a guarantee: a well-formed PDF or Office file can
still carry malware (no antivirus scan is performed).
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
import zipfile

logger = logging.getLogger("app.upload_guard")

# Final extensions we accept (all of them the app can show or hand out safely).
# SVG is left out on purpose: it can embed scripts.
ALLOWED_EXT = {
    ".md", ".markdown", ".txt", ".log", ".csv", ".json", ".yml", ".yaml",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".pdf",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".zip",
}  # fmt: skip

_TEXT_EXT = {".md", ".markdown", ".txt", ".log", ".csv", ".json", ".yml", ".yaml"}
_OOXML_EXT = {".docx", ".pptx", ".xlsx"}
_OLE_EXT = {".doc", ".ppt", ".xls"}

# Extensions that must not hide inside a name (``report.exe.pdf``).
_DANGEROUS_INNER = {
    "exe", "dll", "bat", "cmd", "com", "scr", "msi", "msp", "sh", "bash", "zsh",
    "ps1", "vbs", "vbe", "js", "jse", "mjs", "jar", "apk", "app", "bin", "run",
    "php", "phtml", "html", "htm", "svg", "hta", "lnk", "reg", "elf", "so",
    "dylib", "pif", "cpl", "wsf",
}  # fmt: skip

_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}  # fmt: skip

_MAX_NAME_LEN = 120
_BAD_NAME_CHARS = set('<>:"|?*')

_ZIP_MAX_ENTRIES = 2000
_ZIP_MAX_UNCOMPRESSED = 100 * 1024 * 1024  # 100 MiB
_ZIP_MAX_RATIO = 100  # uncompressed / compressed, a decompression-bomb guard

_PDF_ACTIVE = re.compile(rb"/(JavaScript|JS|Launch)(?![A-Za-z])")

_OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


class UploadRejected(Exception):
    """The upload failed a safety check (``status`` is the HTTP code to return)."""

    def __init__(self, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status


def _suffix(name: str) -> str:
    return f".{name.rsplit('.', 1)[-1].lower()}" if "." in name else ""


def check_filename(name: str) -> None:
    """Reject names that are risky on any OS or in a file manager."""
    if not name or name != name.strip() or name.endswith("."):
        raise UploadRejected("Nome del file non valido.")
    if len(name) > _MAX_NAME_LEN:
        raise UploadRejected(f"Nome del file troppo lungo (max {_MAX_NAME_LEN}).")
    for ch in name:
        # Control chars and invisible formatting (e.g. the right-to-left override
        # used to disguise extensions).
        if ord(ch) < 32 or ord(ch) == 127 or unicodedata.category(ch) in {"Cc", "Cf"}:
            raise UploadRejected("Il nome del file contiene caratteri non ammessi.")
        if ch in _BAD_NAME_CHARS:
            raise UploadRejected("Il nome del file contiene caratteri non ammessi.")
    stem, _, _ = name.partition(".")
    if stem.lower() in _WINDOWS_RESERVED:
        raise UploadRejected("Nome del file riservato, scegline un altro.")
    parts = name.lower().split(".")[1:-1]  # extensions other than the last
    if any(p in _DANGEROUS_INNER for p in parts):
        raise UploadRejected("Il nome del file nasconde un'estensione pericolosa.")


def check_extension(name: str) -> str:
    ext = _suffix(name)
    if ext not in ALLOWED_EXT:
        shown = ext or "senza estensione"
        raise UploadRejected(f"Tipo di file non consentito ({shown}).", 415)
    return ext


def _check_zip(data: bytes, *, ooxml: bool) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = zf.infolist()
    except (zipfile.BadZipFile, ValueError, OSError) as exc:
        raise UploadRejected("Archivio ZIP/Office non valido o corrotto.", 422) from exc
    if len(infos) > _ZIP_MAX_ENTRIES:
        raise UploadRejected("Archivio con troppi file.", 422)
    total = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise UploadRejected("Gli archivi protetti da password non sono ammessi.", 422)
        n = info.filename
        if n.startswith("/") or "\\" in n or any(seg == ".." for seg in n.split("/")):
            raise UploadRejected("Archivio con percorsi non sicuri.", 422)
        total += info.file_size
        if total > _ZIP_MAX_UNCOMPRESSED:
            raise UploadRejected("Archivio troppo grande una volta estratto.", 422)
        if info.compress_size and info.file_size / info.compress_size > _ZIP_MAX_RATIO:
            raise UploadRejected("Archivio sospetto (rapporto di compressione anomalo).", 422)
        if ooxml and n.lower().endswith("vbaproject.bin"):
            raise UploadRejected("I documenti con macro non sono ammessi.", 422)


def check_content(ext: str, data: bytes) -> None:
    """The bytes must really be what the extension claims."""
    if not data:
        raise UploadRejected("File vuoto.", 422)
    bad = UploadRejected("Il contenuto non corrisponde al tipo di file.", 422)
    if ext in _TEXT_EXT:
        if b"\x00" in data:
            raise bad
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise bad from exc
    elif ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise bad
    elif ext in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"):
            raise bad
    elif ext == ".gif":
        if not data.startswith((b"GIF87a", b"GIF89a")):
            raise bad
    elif ext == ".webp":
        if not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise bad
    elif ext == ".pdf":
        if not data.lstrip(b"\x00\t\n\r\x0c ").startswith(b"%PDF-"):
            raise bad
        if _PDF_ACTIVE.search(data):
            raise UploadRejected("I PDF con script o azioni automatiche non sono ammessi.", 422)
    elif ext in _OLE_EXT:
        if not data.startswith(_OLE_MAGIC):
            raise bad
    elif ext in _OOXML_EXT or ext == ".zip":
        if not data.startswith(b"PK\x03\x04"):
            raise bad
        _check_zip(data, ooxml=ext in _OOXML_EXT)


def validate_upload(rel_path: str, data: bytes) -> None:
    """Run every offline check on ``assets/<section>/<rel_path>``'s bytes."""
    name = rel_path.rsplit("/", 1)[-1]
    check_filename(name)
    ext = check_extension(name)
    check_content(ext, data)
