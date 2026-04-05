from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_analyst_or_admin
from app.models.user import User, UserRole
from app.schemas.summary import (
    CategoryBreakdownItem,
    MonthlyTotalItem,
    OverviewSummary,
    RecentActivityItem,
)
from app.services import summary_service

router = APIRouter(prefix="/summaries", tags=["summaries"])


def _target_user_id(current: User, user_id: int | None) -> int:
    if user_id is None or user_id == current.id:
        return current.id
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins may access another user's summaries",
        )
    return user_id


@router.get("/overview", response_model=OverviewSummary)
def overview(
    current: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    user_id: int | None = Query(None, description="Admin only: scope summary to this user"),
):
    """Total income, total expenses, balance, and transaction count (viewer+)."""
    tid = _target_user_id(current, user_id)
    return summary_service.overview(db, tid)


@router.get("/by-category", response_model=list[CategoryBreakdownItem])
def by_category(
    current: Annotated[User, Depends(require_analyst_or_admin)],
    db: Session = Depends(get_db),
    user_id: int | None = Query(None, description="Admin only"),
):
    """Category-wise income, expense, and net (analyst+)."""
    tid = _target_user_id(current, user_id)
    return summary_service.category_breakdown(db, tid)


@router.get("/monthly", response_model=list[MonthlyTotalItem])
def monthly(
    current: Annotated[User, Depends(require_analyst_or_admin)],
    db: Session = Depends(get_db),
    user_id: int | None = Query(None, description="Admin only"),
):
    """Monthly totals aggregated as YYYY-MM (analyst+). Uses SQLite date functions."""
    tid = _target_user_id(current, user_id)
    return summary_service.monthly_totals(db, tid)


@router.get("/recent", response_model=list[RecentActivityItem])
def recent(
    current: Annotated[User, Depends(require_analyst_or_admin)],
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    user_id: int | None = Query(None, description="Admin only"),
):
    """Most recent transactions by date (analyst+)."""
    tid = _target_user_id(current, user_id)
    return summary_service.recent_activity(db, tid, limit=limit)
