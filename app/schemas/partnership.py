from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.partnership import PartnershipPlan, PartnershipStatus
from app.models.partnership_payment import PaymentStatus, PaymentProvider


class PartnershipPlanRead(BaseModel):
    plan: PartnershipPlan
    label: str
    description: str
    recommended_for: str
    price_kes: int
    duration_days: int
    allows_premium_content: bool = True


class PartnershipCreate(BaseModel):
    plan: PartnershipPlan
    phone_number: str = Field(min_length=9, max_length=20)
    referral_creator_id: Optional[str] = None


class PartnershipRead(BaseModel):
    id: str
    user_id: str
    plan: PartnershipPlan
    status: PartnershipStatus
    referral_creator_id: Optional[str]
    provider: Optional[str]
    provider_reference: Optional[str]
    started_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartnershipPaymentRead(BaseModel):
    id: str
    partnership_id: str
    user_id: str
    provider: PaymentProvider
    status: PaymentStatus
    plan: str
    amount: int
    currency: str
    phone_number: str
    merchant_request_id: Optional[str]
    checkout_request_id: Optional[str]
    mpesa_receipt_number: Optional[str]
    result_code: Optional[str]
    result_desc: Optional[str]
    requested_at: Optional[datetime]
    paid_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartnershipCheckoutResponse(BaseModel):
    partnership: PartnershipRead
    payment: Optional[PartnershipPaymentRead] = None
    message: str


class PartnershipAccessRead(BaseModel):
    has_active_partnership: bool
    active_plan: Optional[PartnershipPlan] = None
    expires_at: Optional[datetime] = None


class AdminActivatePartnershipRequest(BaseModel):
    months: int = 1


class PartnershipPaymentStatusRead(BaseModel):
    payment: Optional[PartnershipPaymentRead] = None
    partnership: Optional[PartnershipRead] = None
    message: str