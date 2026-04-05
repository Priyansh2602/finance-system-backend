from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionType
from app.models.user import User, UserRole
from app.security import hash_password


def _register(client, suffix="1"):
    r = client.post(
        "/auth/register",
        json={
            "email": f"u{suffix}@test.com",
            "username": f"user{suffix}",
            "password": "password12345",
        },
    )
    assert r.status_code == 201
    return r.json()


def _login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_register_login_me(client):
    _register(client)
    token = _login(client, "user1", "password12345")
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"


def test_viewer_cannot_use_transaction_filters(client, db_session):
    _register(client, "v")
    token = _login(client, "userv", "password12345")
    r = client.get(
        "/transactions?category=food",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_analyst_can_filter_and_insights(client, db_session):
    u = User(
        email="an@test.com",
        username="analyst1",
        hashed_password=hash_password("password12345"),
        role=UserRole.analyst,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    t = Transaction(
        user_id=u.id,
        amount=Decimal("10.00"),
        type=TransactionType.expense,
        category="food",
        occurred_on=date(2026, 1, 15),
        notes="lunch",
    )
    db_session.add(t)
    db_session.commit()

    token = _login(client, "analyst1", "password12345")
    r = client.get(
        "/transactions?category=food",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    r2 = client.get(
        "/summaries/by-category",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()[0]["category"] == "food"


def test_viewer_cannot_access_analyst_insights(client, db_session):
    _register(client, "x")
    token = _login(client, "userx", "password12345")
    r = client.get(
        "/summaries/monthly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_admin_crud_transaction(client, db_session):
    admin = User(
        email="adm@test.com",
        username="admin1",
        hashed_password=hash_password("password12345"),
        role=UserRole.admin,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = _login(client, "admin1", "password12345")
    r = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": "100.50",
            "type": "income",
            "category": "salary",
            "occurred_on": "2026-03-01",
            "notes": "pay",
        },
    )
    assert r.status_code == 201
    tid = r.json()["id"]

    r2 = client.patch(
        f"/transactions/{tid}",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "updated"},
    )
    assert r2.status_code == 200
    assert r2.json()["notes"] == "updated"

    r3 = client.delete(
        f"/transactions/{tid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 204


def test_validation_error_returns_422(client):
    r = client.post(
        "/auth/register",
        json={"email": "not-an-email", "username": "ab", "password": "short"},
    )
    assert r.status_code == 422
