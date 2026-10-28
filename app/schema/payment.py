from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
class PaymentInitializationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    authorization_url: str
    access_code: str
    amount: int
    currency: str
    status: str


class PaymentInitializationRequest(BaseModel):
    enrollment_id: UUID


class PaymentVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    amount: int
    currency: str
    status: str
    paid_at: datetime | None
