from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import AuthToken, UserCreate, UserLogin, UserRead
from app.services import auth_service
from app.services.errors import AuthenticationFailed, EmailAlreadyRegistered

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    try:
        return auth_service.register_user(db, str(payload.email), payload.password)
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc


@router.post("/login", response_model=AuthToken)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthToken:
    try:
        user = auth_service.authenticate_user(db, str(payload.email), payload.password)
    except AuthenticationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    token, expires_in = auth_service.issue_access_token(user, settings)
    return AuthToken(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user
