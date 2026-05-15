from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.partnership import PartnershipPlan, PartnershipStatus


class PartnershipPlanRead(BaseModel):
    plan: PartnershipPlan
    label: str
    description: str
    recommended_for: str


class PartnershipCreate(BaseModel):
    plan: PartnershipPlan
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


class PartnershipAccessRead(BaseModel):
    has_active_partnership: bool
    active_plan: Optional[PartnershipPlan] = None
    expires_at: Optional[datetime] = None


class AdminActivatePartnershipRequest(BaseModel):
    months: int = 1