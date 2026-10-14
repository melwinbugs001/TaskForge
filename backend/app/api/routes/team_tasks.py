from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.team import TeamTask
from app.models.user import User
from app.schemas.team import (
    TaskRequestCreate,
    TaskRequestReview,
    TaskReview,
    TaskScheduleUpdate,
    TeamTaskDetail,
    TeamTaskRead,
)
from app.services import push_notifications, team_task_service
from app.services.errors import ResourceConflict, ResourceNotFound

router = APIRouter(prefix="/tasks", tags=["team tasks"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ResourceNotFound):
        return HTTPException(status_code=404, detail="Task not found")
    if isinstance(exc, ResourceConflict):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.get("/{task_id}", response_model=TeamTaskDetail)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        return team_task_service.get_task(db, task_id, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.patch("/{task_id}/schedule", response_model=TeamTaskRead)
def update_schedule(
    task_id: int,
    payload: TaskScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        task = team_task_service.update_schedule(db, task_id, user.id, payload)
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.post("/{task_id}/submit", response_model=TeamTaskRead)
def submit_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.submit_task(db, task_id, user.id)
        push_notifications.notify_team_leader(db, task, settings)
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.post("/{task_id}/review", response_model=TeamTaskRead)
def review_task(
    task_id: int,
    payload: TaskReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.review_task(db, task_id, user.id, payload)
        assignment_user_id = payload.assignee_id or task.assignee_id
        push_notifications.notify_worker_of_review(
            db,
            task,
            assignment_user_id,
            payload.approved,
            payload.comment,
            settings,
        )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.post("/{task_id}/approval", response_model=TeamTaskRead)
def review_task_request(
    task_id: int,
    payload: TaskRequestReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.review_task_request(
            db, task_id, user.id, payload
        )
        push_notifications.notify_worker_of_task_proposal_review(
            db, task, payload.approved, payload.comment, settings
        )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.patch("/{task_id}/request", response_model=TeamTaskRead)
def update_declined_task_request(
    task_id: int,
    payload: TaskRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.update_declined_task_request(
            db, task_id, user.id, payload
        )
        push_notifications.notify_team_leader_of_task_proposal(
            db, task, user.id, settings
        )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
