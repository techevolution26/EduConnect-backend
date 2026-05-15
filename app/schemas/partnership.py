from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.partnership import PartnershipPlan, PartnershipStatus
from app.schemas.common import TimestampedSchema


class PartnershipCreate(BaseModel):
    plan: PartnershipPlan
    referral_creator_id: Optional[str] = None


class PartnershipRead(TimestampedSchema):
    user_id: str
    plan: PartnershipPlan
    status: PartnershipStatus
    referral_creator_id: Optional[str]
    provider: Optional[str]
    provider_reference: Optional[str]
    started_at: Optional[datetime]
    expires_at: Optional[datetime]