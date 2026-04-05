"""
Seed an admin user and sample transactions (SQLite file from DATABASE_URL).

Run from project root:  python -m app.seed
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserRole
from app.security import hash_password


def seed() -> None:
    from app.database import Base

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = db.scalars(select(User).where(User.username == "admin")).first()
        if admin is None:
            admin = User(
                email="admin@example.com",
                username="admin",
                hashed_password=hash_password("Admin12345!"),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("Created admin user: username=admin password=Admin12345!")
        else:
            print("Admin user already exists (username=admin).")

        exists = db.scalars(select(Transaction).where(Transaction.user_id == admin.id).limit(1)).first()
        if exists is None:
            samples = [
                Transaction(
                    user_id=admin.id,
                    amount=Decimal("3500.00"),
                    type=TransactionType.income,
                    category="salary",
                    occurred_on=date(2026, 3, 1),
                    notes="March salary",
                ),
                Transaction(
                    user_id=admin.id,
                    amount=Decimal("45.99"),
                    type=TransactionType.expense,
                    category="groceries",
                    occurred_on=date(2026, 3, 3),
                    notes="Weekly shop",
                ),
                Transaction(
                    user_id=admin.id,
                    amount=Decimal("120.00"),
                    type=TransactionType.expense,
                    category="utilities",
                    occurred_on=date(2026, 3, 5),
                    notes="Electricity",
                ),
            ]
            for s in samples:
                db.add(s)
            db.commit()
            print(f"Inserted {len(samples)} sample transactions for admin.")
        else:
            print("Sample transactions already present; skipping inserts.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
