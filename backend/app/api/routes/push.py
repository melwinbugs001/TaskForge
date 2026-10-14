from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.push_subscription import WebPushSubscription
from app.models.user import User
from app.schemas.push import (
    PushSubscriptionDelete,
    PushSubscriptionInput,
    PushSubscriptionStatus,
    VapidPublicKeyRead,
)
from app.services import push_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyRead)
def get_vapid_public_key(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    del user
    if not push_notifications.is_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Browser push notifications are not configured on the server",
        )
    return {"public_key": settings.vapid_public_key or ""}


@router.get("/subscriptions", response_model=PushSubscriptionStatus)
def get_subscription_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool | int]:
    count = db.scalar(
        select(func.count(WebPushSubscription.id)).where(
            WebPushSubscription.user_id == user.id
        )
    ) or 0
    return {"enabled": push_notifications.is_configured(settings), "subscription_count": count}


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
def save_subscription(
    payload: PushSubscriptionInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    existing = db.scalar(
        select(WebPushSubscription).where(
            WebPushSubscription.endpoint == payload.endpoint
        )
    )
    if existing is not None:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This browser subscription is already linked to another account",
            )
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        db.commit()
        return {"saved": True}

    db.add(
        WebPushSubscription(
            user_id=user.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(WebPushSubscription).where(
                WebPushSubscription.endpoint == payload.endpoint
            )
        )
        if existing is None or existing.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This browser subscription is already linked to another account",
            )
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        db.commit()
    return {"saved": True}


@router.delete("/subscriptions")
def delete_subscription(
    payload: PushSubscriptionDelete,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    subscription = db.scalar(
        select(WebPushSubscription).where(
            WebPushSubscription.endpoint == payload.endpoint,
            WebPushSubscription.user_id == user.id,
        )
    )
    if subscription is not None:
        db.delete(subscription)
        db.commit()
    return {"removed": subscription is not None}