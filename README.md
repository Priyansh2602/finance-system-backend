# Finance System Backend

A small **FastAPI** backend for personal finance tracking: transactions, summaries, and **role-based access** (viewer / analyst / admin). Persistence uses **SQLAlchemy 2** with **SQLite** by default (easy to swap for PostgreSQL via `DATABASE_URL`).

## Features

- **Financial records**: amount, type (income / expense), category, date, optional notes; full CRUD with filtering.
- **Summaries**: totals, balance, category breakdown, monthly aggregates, recent activity.
- **Users & roles** (JWT bearer auth):
  - **viewer**: read own transactions (paginated, **no query filters**); read high-level **overview** summary.
  - **analyst**: viewer capabilities **plus** filters on transactions and **detailed** summary endpoints (category, monthly, recent).
  - **admin**: create/update/delete transactions; create/list/update users; optional `user_id` on list/summary routes to act on another user’s data.
- **Validation**: Pydantic models for request bodies; `422` with structured errors on invalid input.
- **API docs**: OpenAPI at `/docs` and `/redoc` when the server is running.

## Assumptions

- Each **transaction belongs to one user** (multi-tenant by `user_id`).
- **Public registration** creates accounts with role **viewer**; admins are created via the admin API or the seed script.
- **Only admins** may create, update, or delete transactions (analysts read and analyze; viewers read a simplified list).
- **Monthly summaries** use SQLite’s `strftime` (documented here; for PostgreSQL you would switch to a portable expression such as `date_trunc` / `to_char`).
- **JWT** secret defaults are for development only—set `SECRET_KEY` in production.

## Quick start

Python 3.11+ recommended.

```bash
cd "Python Based Finance System Backend"
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` and set `SECRET_KEY` and `DATABASE_URL`.

**Run the API:**

```bash
uvicorn app.main:app --reload
```

- Health: `GET http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

**Seed demo data** (admin + sample rows in the configured SQLite file):

```bash
python -m app.seed
```

Default admin (after seed): username `admin`, password `Admin12345!`.

## Configuration

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (default `sqlite:///./finance.db`) |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default 1440) |

## How to authenticate

1. `POST /auth/register` with JSON `{ "email", "username", "password" }` (new users are **viewers**).
2. `POST /auth/login` with JSON `{ "username", "password" }` → `access_token`.
3. Send `Authorization: Bearer <access_token>` on protected routes.

## Main endpoints (summary)

| Area | Method | Path | Roles |
|------|--------|------|--------|
| Auth | POST | `/auth/register`, `/auth/login` | Public |
| User | GET | `/users/me` | Authenticated |
| Users | POST, GET, PATCH | `/users`, `/users/{id}` | Admin |
| Transactions | GET | `/transactions` | Viewer+ (filters: analyst+; `user_id`: admin) |
| Transactions | POST, PATCH, DELETE | `/transactions`, `/transactions/{id}` | Admin |
| Summaries | GET | `/summaries/overview` | Viewer+ |
| Summaries | GET | `/summaries/by-category`, `/summaries/monthly`, `/summaries/recent` | Analyst+ |

## Tests

```bash
python -m pytest tests -v
```

Tests use an isolated temporary SQLite file (set in `tests/conftest.py` before imports).

## Project layout

```
app/
  main.py           # FastAPI app, routers, validation error handler
  config.py         # Settings from environment
  database.py       # Engine and session
  models/           # SQLAlchemy models
  schemas/          # Pydantic request/response models
  routers/          # auth, users, transactions, summaries
  services/         # Summary/analytics logic
  security.py       # Password hashing and JWT
  deps.py           # Auth and role dependencies
  seed.py           # Optional demo data
tests/
  conftest.py
  test_api.py
```

