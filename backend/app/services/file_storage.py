"""Keeping the original uploaded files on disk (in the shared /data folder)."""

from pathlib import Path
from uuid import UUID

from app.config import settings


def save_file(user_id: UUID, document_id: UUID, filename: str, data: bytes) -> str:
    """Store the original file as <upload_dir>/<user>/<document>.<ext> and return that path."""
    folder = Path(settings.upload_dir) / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document_id}{Path(filename).suffix.lower()}"
    path.write_bytes(data)
    return str(path)


def delete_file(path: str) -> None:
    """Remove a stored file if it is still there."""
    if not path:
        return
    file = Path(path)
    if file.exists():
        file.unlink()