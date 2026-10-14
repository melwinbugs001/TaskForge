from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.services.errors import AuthenticationFailed, EmailAlreadyRegistered
from app.services.team_service import accept_pending_invites


def register_user(db: Session, email: str, password: str) -> User:
    user = User(email=email.lower(), hashed_password=hash_password(password))
    db.add(user)
    try:
        db.flush()
        accept_pending_invites(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_user = db.scalar(select(User).where(User.email == email.lower()))
        if existing_user is not None:
            raise EmailAlreadyRegistered from exc
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationFailed
    if not user.is_active:
        raise AuthenticationFailed
    return user


def issue_access_token(user: User, settings: Settings) -> tuple[str, int]:
    expires_in = settings.access_token_expire_minutes * 60
    token = create_access_token(
        str(user.id),
        settings.jwt_secret.get_secret_value(),
        timedelta(seconds=expires_in),
    )
    return token, expires_in
