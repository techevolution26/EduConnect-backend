from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone_number(phone_number: str) -> str:
    digits = "".join(ch for ch in phone_number if ch.isdigit())

    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]

    if digits.startswith("254") and len(digits) == 12:
        return digits

    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits

    return digits


def mpesa_base_url() -> str:
    settings = get_settings()
    environment = settings.mpesa_environment.lower()

    if environment == "production":
        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


async def get_access_token() -> str:
    settings = get_settings()

    if not settings.mpesa_consumer_key or not settings.mpesa_consumer_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="M-Pesa consumer credentials are missing.",
        )

    auth = (settings.mpesa_consumer_key, settings.mpesa_consumer_secret)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials",
            auth=auth,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Daraja token error: {response.text}",
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Daraja token response did not include access_token.",
            )

        return token


async def stk_push(
    *,
    phone_number: str,
    amount: int,
    account_reference: str,
    transaction_desc: str,
) -> dict:
    settings = get_settings()

    access_token = await get_access_token()
    timestamp = _now().strftime("%Y%m%d%H%M%S")
    password = b64encode(
        f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode("utf-8")
    ).decode("utf-8")

    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.mpesa_shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{mpesa_base_url()}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Daraja STK error: {response.text}",
            )

        return response.json()