from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, summaries, transactions, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description=(
        "Finance tracking API: transactions, summaries, and role-based access "
        "(viewer / analyst / admin). See README for assumptions and how to test."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": "Validation failed"},
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(summaries.router)


@app.get("/health")
def health():
    return {"status": "ok"}
