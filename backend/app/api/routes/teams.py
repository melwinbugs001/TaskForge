from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.team import Team, TeamInvite, TeamTask
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamDetail,
    TeamDiscoverabilityUpdate,
    TeamJoinRequestRead,
    TeamJoinRequestReview,
    DiscoverableTeamRead,
    TeamInviteCreate,
    TeamInviteRead,
    TeamRead,
    TeamTaskBulkCreate,
    TeamTaskCreate,
    TeamTaskRead,
    TaskRequestCreate,
)
from app.services import push_notifications, team_service, team_task_service
from app.services.errors import ResourceConflict, ResourceNotFound

router = APIRouter(prefix="/teams", tags=["teams"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ResourceNotFound):
        return HTTPException(status_code=404, detail="Team or task not found")
    if isinstance(exc, ResourceConflict):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        team = team_service.create_team(db, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": team.id,
        "name": team.name,
        "is_discoverable": team.is_discoverable,
        "leader_id": team.leader_id,
        "created_at": team.created_at,
        "role": "leader",
        "member_count": 1,
        "pending_invite_count": 0,
    }


@router.get("", response_model=list[TeamRead])
def list_teams(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    return team_service.list_teams(db, user.id)


@router.get("/discover", response_model=list[DiscoverableTeamRead])
def discover_teams(
    q: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if len(q) > 120:
        raise HTTPException(status_code=422, detail="Search text is too long")
    return team_service.search_discoverable_teams(db, user.id, q, limit)


@router.post("/{team_id}/join-requests", response_model=TeamJoinRequestRead, status_code=201)
def request_to_join(
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        request = team_service.request_to_join(db, team_id, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    return {
        "id": request.id,
        "team_id": request.team_id,
        "user_id": request.user_id,
        "email": user.email,
        "status": request.status,
        "created_at": request.created_at,
    }


@router.patch(
    "/{team_id}/join-requests/{request_id}",
    response_model=TeamJoinRequestRead,
)
def review_join_request(
    team_id: int,
    request_id: int,
    payload: TeamJoinRequestReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    approve = payload.approve
    try:
        request = team_service.review_join_request(
            db, team_id, request_id, user.id, approve
        )
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    requester = db.get(User, request.user_id)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requester not found")
    return {
        "id": request.id,
        "team_id": request.team_id,
        "user_id": request.user_id,
        "email": requester.email,
        "status": request.status,
        "created_at": request.created_at,
    }


@router.patch("/{team_id}/discoverability", response_model=TeamRead)
def update_discoverability(
    team_id: int,
    payload: TeamDiscoverabilityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        team = team_service.set_team_discoverability(
            db, team_id, user.id, payload
        )
        info = team_service.get_team(db, team_id, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    return {**info, "is_discoverable": team.is_discoverable}


@router.get("/{team_id}", response_model=TeamDetail)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        return team_service.get_team(db, team_id, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{team_id}/invites",
    response_model=TeamInviteRead,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    team_id: int,
    payload: TeamInviteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        invite: TeamInvite = team_service.invite_member(
            db, team_id, user.id, payload
        )
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    return {
        "email": invite.email,
        "created_at": invite.created_at,
        "accepted": invite.accepted_at is not None,
    }


@router.get("/{team_id}/tasks", response_model=list[TeamTaskRead])
def list_tasks(
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    try:
        return team_task_service.list_tasks(db, team_id, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{team_id}/tasks",
    response_model=TeamTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    team_id: int,
    payload: TeamTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.create_task(db, team_id, user.id, payload)
        push_notifications.notify_worker_of_assignment(
            db, task, payload.assignee_id, settings
        )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{team_id}/tasks/bulk",
    response_model=TeamTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tasks_for_workers(
    team_id: int,
    payload: TeamTaskBulkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.create_tasks_for_workers(
            db, team_id, user.id, payload
        )
        for worker_id in payload.assignee_ids:
            push_notifications.notify_worker_of_assignment(
                db, task, worker_id, settings
            )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/{team_id}/task-requests",
    response_model=TeamTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def request_task(
    team_id: int,
    payload: TaskRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        task = team_task_service.request_task(db, team_id, user.id, payload)
        push_notifications.notify_team_leader_of_task_proposal(
            db, task, user.id, settings
        )
        return team_task_service.task_response(db, task, user.id)
    except (ResourceNotFound, ResourceConflict) as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
