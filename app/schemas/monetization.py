from datetime import datetime

from pydantic import BaseModel

from app.models.monetization import ReferralEarningStatus


class ReferralSummaryRead(BaseModel):
    pending_kes: int
    paid_kes: int
    total_referrals: int


class ReferralEarningRead(BaseModel):
    id: str
    partnership_id: str
    source_amount_kes: int
    commission_rate_bps: int
    commission_amount_kes: int
    status: ReferralEarningStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferralEarningListResponse(BaseModel):
    items: list[ReferralEarningRead]
    total: int
    skip: int
    limit: int
