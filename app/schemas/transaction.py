from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    type: TransactionType
    category: str = Field(..., min_length=1, max_length=100)
    occurred_on: date
    notes: str | None = Field(None, max_length=5000)


class TransactionCreate(TransactionBase):
    user_id: int | None = Field(
        None,
        description="Admin only: create record for another user. Defaults to the authenticated user.",
    )


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(None, gt=0, max_digits=14, decimal_places=2)
    type: TransactionType | None = None
    category: str | None = Field(None, min_length=1, max_length=100)
    occurred_on: date | None = None
    notes: str | None = Field(None, max_length=5000)


class TransactionOut(TransactionBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionFilterParams(BaseModel):
    """Query params for analyst+ filtered listing."""

    type: TransactionType | None = None
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def check_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self
