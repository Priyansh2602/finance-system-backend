from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(current: Annotated[User, Depends(get_current_user)]):
    return current


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    """Admin: create a user with an optional role (defaults to viewer)."""
    if db.scalars(select(User).where(User.email == body.email)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if db.scalars(select(User).where(User.username == body.username)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    from app.models.user import UserRole
    from app.security import hash_password

    role = body.role if body.role is not None else UserRole.viewer
    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    from app.security import hash_password

    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        data["hashed_password"] = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
