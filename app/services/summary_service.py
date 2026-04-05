from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.schemas.summary import (
    CategoryBreakdownItem,
    MonthlyTotalItem,
    OverviewSummary,
    RecentActivityItem,
)


def _base_query(db: Session, user_id: int):
    return select(Transaction).where(Transaction.user_id == user_id)


def overview(db: Session, user_id: int) -> OverviewSummary:
    income = (
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id, Transaction.type == TransactionType.income
            )
        ).scalar_one()
    )
    expense = (
        db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id, Transaction.type == TransactionType.expense
            )
        ).scalar_one()
    )
    income_d = Decimal(str(income))
    expense_d = Decimal(str(expense))
    count = db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    ).scalar_one()
    return OverviewSummary(
        total_income=income_d,
        total_expense=expense_d,
        balance=income_d - expense_d,
        transaction_count=int(count or 0),
    )


def category_breakdown(db: Session, user_id: int) -> list[CategoryBreakdownItem]:
    rows = db.execute(
        select(Transaction.category, Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.category, Transaction.type)
    ).all()
    by_cat: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"income": Decimal("0"), "expense": Decimal("0")})
    for category, ttype, total in rows:
        key = "income" if ttype == TransactionType.income else "expense"
        by_cat[category][key] = Decimal(str(total))
    result: list[CategoryBreakdownItem] = []
    for category, vals in sorted(by_cat.items()):
        inc = vals["income"]
        exp = vals["expense"]
        result.append(
            CategoryBreakdownItem(
                category=category,
                total_income=inc,
                total_expense=exp,
                net=inc - exp,
            )
        )
    return result


def monthly_totals(db: Session, user_id: int) -> list[MonthlyTotalItem]:
    rows = db.execute(
        select(
            func.strftime("%Y-%m", Transaction.occurred_on).label("ym"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(Transaction.user_id == user_id)
        .group_by("ym", Transaction.type)
        .order_by("ym")
    ).all()
    by_month: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"income": Decimal("0"), "expense": Decimal("0")})
    for ym, ttype, total in rows:
        key = "income" if ttype == TransactionType.income else "expense"
        by_month[ym][key] = Decimal(str(total))
    return [
        MonthlyTotalItem(
            year_month=ym,
            total_income=vals["income"],
            total_expense=vals["expense"],
            net=vals["income"] - vals["expense"],
        )
        for ym, vals in sorted(by_month.items())
    ]


def recent_activity(db: Session, user_id: int, limit: int = 10) -> list[RecentActivityItem]:
    rows = db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
        .limit(limit)
    ).scalars().all()
    return [
        RecentActivityItem(
            id=r.id,
            amount=r.amount,
            type=r.type.value,
            category=r.category,
            occurred_on=r.occurred_on,
            notes=r.notes,
        )
        for r in rows
    ]


def filtered_transactions_query(
    db: Session,
    user_id: int,
    *,
    type_: TransactionType | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    q = select(Transaction).where(Transaction.user_id == user_id)
    if type_ is not None:
        q = q.where(Transaction.type == type_)
    if category is not None:
        q = q.where(Transaction.category == category)
    if date_from is not None:
        q = q.where(Transaction.occurred_on >= date_from)
    if date_to is not None:
        q = q.where(Transaction.occurred_on <= date_to)
    return q.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
