from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EduConnect API"
    app_env: str = "development"
    debug: bool = True

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # 7 days
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    backend_cors_origins: str = Field(
        default="http://localhost:3000",
        alias="BACKEND_CORS_ORIGINS",
    )

    upload_dir: str = Field(default="/data/uploads", alias="UPLOAD_DIR")
    public_base_url: str = Field(
        default="http://localhost:8000",
        alias="PUBLIC_BASE_URL",
    )


    payment_mode: str = Field(default="stub", alias="PAYMENT_MODE")
    mpesa_environment: str = Field(default="sandbox", alias="MPESA_ENVIRONMENT")
    mpesa_consumer_key: str = Field(default="", alias="MPESA_CONSUMER_KEY")
    mpesa_consumer_secret: str = Field(default="", alias="MPESA_CONSUMER_SECRET")
    mpesa_shortcode: str = Field(default="", alias="MPESA_SHORTCODE")
    mpesa_passkey: str = Field(default="", alias="MPESA_PASSKEY")
    mpesa_callback_url: str = Field(default="", alias="MPESA_CALLBACK_URL")
    # HARDENING: Safaricom's Daraja API does not sign STK push callbacks in
    # any way -- there is no header or body signature to verify. Without
    # this secret, the callback endpoint was a fully open, unauthenticated
    # POST route that ONLY trusted a `CheckoutRequestID` value which is
    # returned directly to the paying client in the /partnerships/start
    # response. Any user could start checkout, never pay, then POST a
    # forged "success" callback straight to the endpoint using their own
    # leaked CheckoutRequestID and get a paid partnership for free.
    #
    # This secret is embedded as a path segment in the callback URL i
    # register with Safaricom (see routers/partnerships.py) and is never
    # returned to any client. Generate a long random value in production,
    # e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
    mpesa_callback_secret: str = Field(default="", alias="MPESA_CALLBACK_SECRET")
    mpesa_account_reference: str = Field(
        default="EduConnect",
        alias="MPESA_ACCOUNT_REFERENCE",
    )
    mpesa_transaction_desc: str = Field(
        default="EduConnect Partnership",
        alias="MPESA_TRANSACTION_DESC",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @field_validator("public_base_url")
    @classmethod
    def normalize_public_base_url(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()