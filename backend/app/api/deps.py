from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid bearer token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(
        credentials.credentials,
        settings.jwt_secret.get_secret_value(),
    )
    if payload is None:
        raise unauthorized
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise unauthorized
    user = db.scalar(select(User).where(User.id == int(subject)))
    if user is None or not user.is_active:
        raise unauthorized
    return user
