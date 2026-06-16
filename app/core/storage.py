from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


def resolve_upload_dir() -> Path:
    settings = get_settings()

    preferred = Path(settings.upload_dir)
    fallback = Path("uploads")

    for candidate in (preferred, fallback):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue

    raise RuntimeError("No writable upload directory is available.")


async def save_upload_file(file: UploadFile, folder: str) -> str:
    base_dir = resolve_upload_dir() / folder
    base_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix
    filename = f"{uuid4().hex}{suffix}"
    target_path = base_dir / filename

    content = await file.read()
    target_path.write_bytes(content)

    settings = get_settings()
    return f"{settings.public_base_url}/uploads/{folder}/{filename}"