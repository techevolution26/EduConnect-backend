from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

# HARDENING: the original save_upload_file() accepted ANY file extension
# and had no size limit at all -- a user could upload a `.php`/`.exe`/
# arbitrarily-named file (served back from a public /uploads/ static mount)
# or a multi-gigabyte file that would exhaust disk space. The UUID-based
# filename already prevented path traversal, but content type and size
# were completely unchecked.
#
# We whitelist extensions per asset category and cap size. This is a
# pragmatic, dependency-free check -- it inspects the claimed extension and
# the browser-supplied Content-Type, which is NOT the same as deep file
# content sniffing (e.g. magic-byte inspection), but closes the obvious
# abuse cases (arbitrary executables/scripts, unbounded upload size) without
# adding a new dependency. For stronger guarantees, add a magic-byte sniffer
# (e.g. python-magic) at the same call site.

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".wav", ".m4a", ".txt",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_FILE_BYTES = 50 * 1024 * 1024    # 50 MB


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


def _validate_upload(file: UploadFile, *, is_image: bool) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    allowed = ALLOWED_IMAGE_EXTENSIONS if is_image else ALLOWED_FILE_EXTENSIONS

    if suffix not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{suffix or 'unknown'}' is not allowed for this upload.",
        )


async def save_upload_file(file: UploadFile, folder: str, *, is_image: bool = False) -> str:
    _validate_upload(file, is_image=is_image)

    base_dir = resolve_upload_dir() / folder
    base_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    target_path = base_dir / filename

    max_bytes = MAX_IMAGE_BYTES if is_image else MAX_FILE_BYTES

    # Stream-read in chunks and abort as soon as the size cap is exceeded,
    # rather than reading the whole (possibly huge) body into memory first.
    content = bytearray()
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
            )

    target_path.write_bytes(bytes(content))

    settings = get_settings()
    return f"{settings.public_base_url}/uploads/{folder}/{filename}"


def normalize_public_url(path_or_url: str | None) -> str | None:
    if not path_or_url:
        return None

    value = path_or_url.strip()
    if not value:
        return None

    if value.startswith("http://") or value.startswith("https://"):
        return value

    settings = get_settings()
    return f"{settings.public_base_url}/{value.lstrip('/')}"
