"""
Filesystem storage for generated documents and images.
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

DEFAULT_GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated_data"


def get_generated_root() -> Path:
    raw = os.getenv("GENERATED_FILES_DIR", "").strip()
    if raw:
        return Path(raw).resolve()
    return DEFAULT_GENERATED_DIR.resolve()


def ensure_storage_dirs() -> tuple[Path, Path]:
    root = get_generated_root()
    docs = root / "documents"
    images = root / "images"
    docs.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)
    return docs, images


def new_storage_id() -> str:
    return uuid.uuid4().hex


def document_storage_path(user_id: int, filename: str) -> Path:
    docs_dir, _ = ensure_storage_dirs()
    user_dir = docs_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return user_dir / f"{new_storage_id()}_{safe_name}"


def image_storage_path(user_id: int, extension: str = "png") -> Path:
    _, images_dir = ensure_storage_dirs()
    user_dir = images_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    ext = extension.lstrip(".") or "png"
    return user_dir / f"{new_storage_id()}.{ext}"


def relative_storage_path(absolute: str | Path) -> str:
    """Store path relative to generated root for portability."""
    path = Path(absolute)
    root = get_generated_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def resolve_storage_path(relative_or_absolute: str) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return get_generated_root() / path


def delete_storage_file(relative_or_absolute: str) -> None:
    path = resolve_storage_path(relative_or_absolute)
    if path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def file_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total
