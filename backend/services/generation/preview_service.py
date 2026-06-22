"""
Build preview payloads for generated document attachments in chat.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from services.generation.storage import resolve_storage_path

_TEXT_EXTENSIONS = frozenset(
    {
        "txt", "md", "py", "js", "ts", "java", "c", "cpp", "cs", "go", "rs",
        "php", "rb", "swift", "kt", "html", "css", "scss", "jsx", "tsx",
        "vue", "json", "yaml", "yml", "toml", "xml", "env", "sql", "graphql",
        "dockerfile", "tf", "csv", "rtf",
    }
)

_CODE_EXTENSIONS = _TEXT_EXTENSIONS - {"md", "csv", "json", "yaml", "yml", "xml", "txt", "rtf", "env"}


def _read_text(path: Path, limit: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) > limit:
        return text[:limit] + "\n\n… (truncated)"
    return text


def _csv_preview(path: Path, max_rows: int = 8) -> dict:
    text = _read_text(path, limit=8000)
    reader = csv.reader(io.StringIO(text))
    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(row)
    return {"headers": rows[0] if rows else [], "rows": rows[1:] if len(rows) > 1 else rows}


def build_document_preview(storage_path: str, file_type: str, files_json: str | None = None) -> dict:
    """Return preview metadata for chat inline rendering."""
    path = resolve_storage_path(storage_path)
    ext = file_type.lower().lstrip(".")

    if not path.exists():
        return {"preview_type": "unavailable", "message": "File not found."}

    if ext == "zip" or path.suffix.lower() == ".zip":
        files = []
        if files_json:
            try:
                files = json.loads(files_json)
            except json.JSONDecodeError:
                files = []
        if not files and path.is_file():
            try:
                with zipfile.ZipFile(path) as zf:
                    files = [{"name": n, "size": zf.getinfo(n).file_size} for n in zf.namelist()[:30]]
            except zipfile.BadZipFile:
                pass
        return {"preview_type": "archive", "files": files}

    if ext == "pdf":
        return {"preview_type": "pdf", "embed_path": None}

    if ext in ("docx", "xlsx", "pptx"):
        return {
            "preview_type": "office",
            "message": "Preview not available for this format. Download to open.",
        }

    if ext == "csv":
        return {"preview_type": "csv", "table": _csv_preview(path)}

    if ext == "json":
        text = _read_text(path)
        try:
            parsed = json.loads(text)
            formatted = json.dumps(parsed, indent=2)[:12000]
        except json.JSONDecodeError:
            formatted = text
        return {"preview_type": "code", "language": "json", "content": formatted}

    if ext == "md":
        return {"preview_type": "markdown", "content": _read_text(path)}

    if ext in _CODE_EXTENSIONS:
        return {"preview_type": "code", "language": ext, "content": _read_text(path)}

    if ext in _TEXT_EXTENSIONS:
        return {"preview_type": "text", "content": _read_text(path)}

    return {"preview_type": "binary", "message": "Download to view this file."}
