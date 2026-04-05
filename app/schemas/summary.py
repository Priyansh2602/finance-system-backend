from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class OverviewSummary(BaseModel):
    total_income: Decimal = Field(..., decimal_places=2)
    total_expense: Decimal = Field(..., decimal_places=2)
    balance: Decimal = Field(..., decimal_places=2)
    transaction_count: int


class CategoryBreakdownItem(BaseModel):
    category: str
    total_income: Decimal
    total_expense: Decimal
    net: Decimal


class MonthlyTotalItem(BaseModel):
    year_month: str = Field(..., description="YYYY-MM")
    total_income: Decimal
    total_expense: Decimal
    net: Decimal


class RecentActivityItem(BaseModel):
    id: int
    amount: Decimal
    type: str
    category: str
    occurred_on: date
    notes: str | None
