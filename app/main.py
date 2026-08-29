from fastapi import FastAPI
import pathlib
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.storage import resolve_upload_dir
from app.routers import (
    admin,
    auth,
    categories,
    children,
    content,
    education,
    engagement,
    events,
    feed,
    health,
    hubs,
    leaderboard,
    notifications,
    partnerships,
    role_requests,
    search,
    students,
    users,
    writers,
    read_session
)

settings = get_settings()
upload_path = resolve_upload_dir()

# HARDENING: fail fast at startup rather than silently running with an
# open webhook if someone enables real M-Pesa payments without setting a
# callback secret (see the long comment on mpesa_callback_secret in
# core/config.py for why this secret exists at all).
if settings.payment_mode.lower() == "mpesa" and not settings.mpesa_callback_secret:
    raise RuntimeError(
        "PAYMENT_MODE=mpesa requires MPESA_CALLBACK_SECRET to be set -- "
        "without it, the /partnerships/mpesa/callback endpoint cannot be "
        "safely exposed. Generate one with: "
        "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
    
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    # HARDENING: wildcard methods/headers combined with allow_credentials=True
    # is broader than this API needs. allow_origins is already an explicit
    # list (never "*"), which is the part that actually matters most for
    # credentialed CORS, but tightening these too costs nothing.
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(writers.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(hubs.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(engagement.router, prefix="/api/v1")
app.include_router(education.router, prefix="/api/v1")
app.include_router(children.router, prefix="/api/v1")
app.include_router(partnerships.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(role_requests.router, prefix="/api/v1")
app.include_router(read_session.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(leaderboard.router, prefix="/api/v1")