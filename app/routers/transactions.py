from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserRole
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from app.services.summary_service import filtered_transactions_query

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _resolve_target_user_id(
    current: User,
    user_id: int | None,
) -> int:
    if user_id is None or user_id == current.id:
        return current.id
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins may access another user's transactions",
        )
    return user_id


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    current: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=100),
    user_id: int | None = Query(None, description="Admin only: list transactions for this user"),
    type: TransactionType | None = Query(None),
    category: str | None = Query(None, max_length=100),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    """
    **Viewer:** paginated list of own transactions (filter query params are not allowed).

    **Analyst / Admin:** may filter by type, category, and date range.

    **Admin:** may set `user_id` to list another user's transactions.
    """
    from datetime import date as date_cls

    target = _resolve_target_user_id(current, user_id)

    has_filters = any(x is not None for x in (type, category, date_from, date_to))
    if has_filters and current.role == UserRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot apply filters; analyst or admin role required",
        )

    if current.role == UserRole.viewer:
        q = filtered_transactions_query(db, target)
    else:
        df = dt = None
        if date_from:
            try:
                df = date_cls.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="date_from must be ISO format YYYY-MM-DD",
                ) from None
        if date_to:
            try:
                dt = date_cls.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="date_to must be ISO format YYYY-MM-DD",
                ) from None
        if df and dt and df > dt:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from must be on or before date_to",
            )
        q = filtered_transactions_query(
            db, target, type_=type, category=category, date_from=df, date_to=dt
        )

    rows = db.execute(q.offset(skip).limit(limit)).scalars().all()
    return list(rows)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    current: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.user_id != current.id and current.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this record")
    return tx


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    owner_id = body.user_id if body.user_id is not None else admin.id
    if body.user_id is not None:
        target = db.get(User, body.user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
    tx = Transaction(
        user_id=owner_id,
        amount=body.amount,
        type=body.type,
        category=body.category,
        occurred_on=body.occurred_on,
        notes=body.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return None
