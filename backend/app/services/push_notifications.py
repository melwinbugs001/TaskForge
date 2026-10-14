import json
import logging
from pathlib import Path
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.push_subscription import WebPushSubscription
from app.models.team import Team, TeamTask
from app.models.user import User

logger = logging.getLogger(__name__)


def is_configured(settings: Settings) -> bool:
    private_key = (
        settings.vapid_private_key.get_secret_value()
        if settings.vapid_private_key is not None
        else ""
    )
    return bool(settings.vapid_public_key and private_key.strip() and settings.vapid_subject)


def _private_key_value(settings: Settings) -> str:
    value = settings.vapid_private_key.get_secret_value()  # checked by is_configured
    if "-----BEGIN" in value:
        return value
    try:
        key_path = Path(value)
        if key_path.is_file():
            return str(key_path)
    except OSError:
        pass
    return value


def send_to_user(
    db: Session,
    user_id: int,
    notification: dict[str, Any],
    settings: Settings,
) -> None:
    if not is_configured(settings):
        logger.warning("Web Push is not configured; notification was not sent")
        return

    subscriptions = db.scalars(
        select(WebPushSubscription).where(WebPushSubscription.user_id == user_id)
    ).all()
    removed_subscription = False
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(notification),
                vapid_private_key=_private_key_value(settings),
                vapid_claims={"sub": settings.vapid_subject},
                ttl=60,
                timeout=5,
            )
        except WebPushException as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(exc, "status_code", None) or getattr(
                response, "status_code", None
            )
            if status_code in (404, 410):
                db.delete(subscription)
                removed_subscription = True
                logger.info(
                    "Removed expired Web Push subscription %s", subscription.id
                )
            else:
                logger.warning(
                    "Web Push delivery failed for subscription %s (status %s)",
                    subscription.id,
                    status_code,
                )
        except Exception:
            logger.exception(
                "Web Push delivery failed for subscription %s", subscription.id
            )

    if removed_subscription:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not remove expired Web Push subscriptions")


def notify_team_leader(
    db: Session,
    task: TeamTask,
    settings: Settings,
) -> None:
    try:
        team = db.get(Team, task.team_id)
        if team is None:
            return
        send_to_user(
            db,
            team.leader_id,
            {
                "title": "Task submitted for review",
                "body": f"{task.title} is ready for your review.",
                "url": f"/teams/{task.team_id}",
                "tag": f"task-{task.id}-submitted",
            },
            settings,
        )
    except Exception:
        logger.exception("Could not dispatch submission notification for task %s", task.id)


def notify_worker_of_assignment(
    db: Session,
    task: TeamTask,
    worker_id: int,
    settings: Settings,
) -> None:
    try:
        send_to_user(
            db,
            worker_id,
            {
                "title": "New task assigned",
                "body": f"Your team leader assigned: {task.title}.",
                "url": f"/teams/{task.team_id}",
                "tag": f"task-{task.id}-assigned-{worker_id}",
            },
            settings,
        )
    except Exception:
        logger.exception("Could not dispatch assignment notification for task %s", task.id)


def notify_team_leader_of_task_proposal(
    db: Session,
    task: TeamTask,
    worker_id: int,
    settings: Settings,
) -> None:
    try:
        team = db.get(Team, task.team_id)
        worker = db.get(User, worker_id)
        if team is None:
            return
        worker_email = worker.email if worker is not None else "A worker"
        send_to_user(
            db,
            team.leader_id,
            {
                "title": "Task proposal needs review",
                "body": f"{worker_email} proposed: {task.title}.",
                "url": f"/teams/{task.team_id}",
                "tag": f"task-{task.id}-proposal",
            },
            settings,
        )
    except Exception:
        logger.exception("Could not dispatch task proposal notification for task %s", task.id)


def notify_worker_of_task_proposal_review(
    db: Session,
    task: TeamTask,
    approved: bool,
    reason: str | None,
    settings: Settings,
) -> None:
    worker_id = task.requested_by or task.assignee_id
    clean_reason = reason.strip() if reason and reason.strip() else None
    if approved:
        title = "Task proposal approved"
        body = f"Your proposed task, {task.title}, was approved."
    else:
        title = "Task proposal declined"
        body = f"Your proposed task, {task.title}, was declined."
        if clean_reason:
            body = f"{body} Reason: {clean_reason}"
    try:
        send_to_user(
            db,
            worker_id,
            {
                "title": title,
                "body": body,
                "url": f"/teams/{task.team_id}",
                "tag": f"task-{task.id}-proposal-review-{worker_id}",
            },
            settings,
        )
    except Exception:
        logger.exception("Could not dispatch proposal review notification for task %s", task.id)


def notify_worker_of_review(
    db: Session,
    task: TeamTask,
    worker_id: int,
    approved: bool,
    reason: str | None,
    settings: Settings,
) -> None:
    clean_reason = reason.strip() if reason and reason.strip() else None
    title = "Task approved" if approved else "Changes requested"
    body = f"{task.title} was approved."
    if not approved:
        body = f"Changes were requested for {task.title}."
        if clean_reason:
            body = f"{body} Reason: {clean_reason}"
    try:
        send_to_user(
            db,
            worker_id,
            {
                "title": title,
                "body": body,
                "url": f"/teams/{task.team_id}",
                "tag": f"task-{task.id}-review-{worker_id}",
            },
            settings,
        )
    except Exception:
        logger.exception("Could not dispatch review notification for task %s", task.id)