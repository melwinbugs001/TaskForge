from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember, TeamTask, TeamTaskAssignment
from app.models.user import User
from app.schemas.team import (
    TaskRequestCreate,
    TaskRequestReview,
    TaskReview,
    TaskScheduleUpdate,
    TeamTaskBulkCreate,
    TeamTaskCreate,
)
from app.services.errors import ResourceConflict, ResourceNotFound
from app.services.team_service import (
    require_team_leader,
    require_team_member,
    require_team_membership,
)


def _get_task(db: Session, task_id: int) -> TeamTask:
    task = db.get(TeamTask, task_id)
    if task is None:
        raise ResourceNotFound
    return task


def get_task(db: Session, task_id: int, user_id: int) -> dict[str, object]:
    task = _get_task(db, task_id)
    require_team_member(db, task.team_id, user_id)
    member = require_team_membership(db, task.team_id, user_id)
    assignment = _get_assignment(db, task.id, user_id)
    if member.role != "leader" and assignment is None:
        raise ResourceNotFound
    return task_response(db, task, user_id)


def _get_assignment(
    db: Session, task_id: int, user_id: int
) -> TeamTaskAssignment | None:
    return db.scalar(
        select(TeamTaskAssignment).where(
            TeamTaskAssignment.task_id == task_id,
            TeamTaskAssignment.user_id == user_id,
        )
    )


def task_response(
    db: Session, task: TeamTask, current_user_id: int
) -> dict[str, object]:
    assignment_rows = db.execute(
        select(TeamTaskAssignment, User.email)
        .join(User, User.id == TeamTaskAssignment.user_id)
        .where(TeamTaskAssignment.task_id == task.id)
        .order_by(User.email)
    ).all()
    assignments = [
        {
            "user_id": assignment.user_id,
            "email": email,
            "status": assignment.status,
            "submitted_at": assignment.submitted_at,
            "completed_at": assignment.completed_at,
            "review_comment": assignment.review_comment,
        }
        for assignment, email in assignment_rows
    ]
    assignee = db.get(User, task.assignee_id)
    return {
        **{
            column.name: getattr(task, column.name)
            for column in TeamTask.__table__.columns
        },
        "assignee_email": assignee.email if assignee else "",
        "assignments": assignments,
        "current_assignment": next(
            (item for item in assignments if item["user_id"] == current_user_id),
            None,
        ),
    }


def list_tasks(db: Session, team_id: int, user_id: int) -> list[dict[str, object]]:
    require_team_member(db, team_id, user_id)
    member = require_team_membership(db, team_id, user_id)
    query = select(TeamTask).where(TeamTask.team_id == team_id)
    if member.role != "leader":
        query = query.join(TeamTaskAssignment).where(
            TeamTaskAssignment.user_id == user_id
        )
    tasks = db.scalars(
        query.order_by(TeamTask.start_at, TeamTask.deadline_at, TeamTask.id)
    ).all()
    return [task_response(db, task, user_id) for task in tasks]


def create_task(
    db: Session,
    team_id: int,
    leader_id: int,
    payload: TeamTaskCreate,
) -> TeamTask:
    require_team_leader(db, team_id, leader_id)
    assignee = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == payload.assignee_id,
            TeamMember.role == "worker",
        )
    )
    if assignee is None:
        raise ResourceConflict("Tasks can only be assigned to a worker on this team")
    task = TeamTask(
        team_id=team_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        assignee_id=payload.assignee_id,
        assigned_by=leader_id,
        start_at=payload.start_at.astimezone(timezone.utc),
        deadline_at=payload.deadline_at.astimezone(timezone.utc),
        status="assigned",
    )
    if not task.title or not task.description:
        raise ValueError("Task title and description must not be blank")
    db.add(task)
    db.flush()
    db.add(TeamTaskAssignment(task_id=task.id, user_id=payload.assignee_id))
    db.commit()
    db.refresh(task)
    return task


def create_tasks_for_workers(
    db: Session,
    team_id: int,
    leader_id: int,
    payload: TeamTaskBulkCreate,
) -> TeamTask:
    require_team_leader(db, team_id, leader_id)
    assignees = db.scalars(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id.in_(payload.assignee_ids),
            TeamMember.role == "worker",
        )
    ).all()
    if len(assignees) != len(payload.assignee_ids):
        raise ResourceConflict("Tasks can only be assigned to workers on this team")

    title = payload.title.strip()
    description = payload.description.strip()
    if not title or not description:
        raise ValueError("Task title and description must not be blank")
    task = TeamTask(
        team_id=team_id,
        title=title,
        description=description,
        assignee_id=payload.assignee_ids[0],
        assigned_by=leader_id,
        start_at=payload.start_at.astimezone(timezone.utc),
        deadline_at=payload.deadline_at.astimezone(timezone.utc),
        status="assigned",
    )
    db.add(task)
    db.flush()
    db.add_all(
        TeamTaskAssignment(task_id=task.id, user_id=assignee.user_id)
        for assignee in assignees
    )
    db.commit()
    db.refresh(task)
    return task


def request_task(
    db: Session,
    team_id: int,
    worker_id: int,
    payload: TaskRequestCreate,
) -> TeamTask:
    require_team_member(db, team_id, worker_id)
    member = require_team_membership(db, team_id, worker_id)
    if member.role != "worker":
        raise ResourceConflict("Only workers can request a task")
    team = db.get(Team, team_id)
    if team is None:
        raise ResourceNotFound
    task = TeamTask(
        team_id=team_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        assignee_id=worker_id,
        assigned_by=team.leader_id,
        requested_by=worker_id,
        start_at=payload.start_at.astimezone(timezone.utc),
        deadline_at=payload.deadline_at.astimezone(timezone.utc),
        status="pending_approval",
    )
    if not task.title or not task.description:
        raise ValueError("Task title and description must not be blank")
    db.add(task)
    db.flush()
    db.add(
        TeamTaskAssignment(
            task_id=task.id,
            user_id=worker_id,
            status="pending_approval",
        )
    )
    db.commit()
    db.refresh(task)
    return task


def review_task_request(
    db: Session,
    task_id: int,
    leader_id: int,
    payload: TaskRequestReview,
) -> TeamTask:
    task = _get_task(db, task_id)
    require_team_leader(db, task.team_id, leader_id)
    if task.status != "pending_approval":
        raise ResourceConflict("Only task requests awaiting approval can be resolved")
    if payload.approved:
        assignment = _get_assignment(db, task.id, task.assignee_id)
        if assignment is None:
            raise ResourceNotFound
        assignment.status = "assigned"
        assignment.review_comment = payload.comment.strip() if payload.comment else None
        task.status = "assigned"
        task.assigned_by = leader_id
        task.review_comment = payload.comment.strip() if payload.comment else None
    else:
        assignment = _get_assignment(db, task.id, task.assignee_id)
        if assignment is None:
            raise ResourceNotFound
        assignment.status = "declined"
        assignment.review_comment = (
            payload.comment.strip() if payload.comment else "Task request declined"
        )
        task.status = "declined"
        task.review_comment = (
            payload.comment.strip() if payload.comment else "Task request declined"
        )
    db.commit()
    db.refresh(task)
    return task


def update_declined_task_request(
    db: Session,
    task_id: int,
    worker_id: int,
    payload: TaskRequestCreate,
) -> TeamTask:
    task = _get_task(db, task_id)
    require_team_member(db, task.team_id, worker_id)
    member = require_team_membership(db, task.team_id, worker_id)
    if member.role != "worker" or task.requested_by != worker_id:
        raise ResourceNotFound
    if task.status != "declined":
        raise ResourceConflict("Only declined task requests can be edited")
    title = payload.title.strip()
    description = payload.description.strip()
    if not title or not description:
        raise ValueError("Task title and description must not be blank")
    task.title = title
    task.description = description
    task.start_at = payload.start_at.astimezone(timezone.utc)
    task.deadline_at = payload.deadline_at.astimezone(timezone.utc)
    assignment = _get_assignment(db, task.id, worker_id)
    if assignment is None:
        raise ResourceNotFound
    assignment.status = "pending_approval"
    assignment.review_comment = None
    task.status = "pending_approval"
    task.review_comment = None
    db.commit()
    db.refresh(task)
    return task


def update_schedule(
    db: Session,
    task_id: int,
    leader_id: int,
    payload: TaskScheduleUpdate,
) -> TeamTask:
    task = _get_task(db, task_id)
    require_team_leader(db, task.team_id, leader_id)
    if task.status == "completed":
        raise ResourceConflict("Completed task schedules cannot be changed")
    task.start_at = payload.start_at.astimezone(timezone.utc)
    task.deadline_at = payload.deadline_at.astimezone(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def submit_task(db: Session, task_id: int, worker_id: int) -> TeamTask:
    task = _get_task(db, task_id)
    require_team_member(db, task.team_id, worker_id)
    assignment = _get_assignment(db, task.id, worker_id)
    if assignment is None:
        raise ResourceNotFound
    if assignment.status != "assigned":
        raise ResourceConflict("Only assigned tasks can be submitted for review")
    assignment.status = "submitted"
    assignment.submitted_at = datetime.now(timezone.utc)
    assignment.completed_at = None
    assignment.review_comment = None
    _refresh_task_status(db, task)
    db.commit()
    db.refresh(task)
    return task


def review_task(
    db: Session,
    task_id: int,
    leader_id: int,
    payload: TaskReview,
) -> TeamTask:
    task = _get_task(db, task_id)
    require_team_leader(db, task.team_id, leader_id)
    assignment_query = select(TeamTaskAssignment).where(
        TeamTaskAssignment.task_id == task.id
    )
    if payload.assignee_id is not None:
        assignment_query = assignment_query.where(
            TeamTaskAssignment.user_id == payload.assignee_id
        )
    else:
        assignments = db.scalars(assignment_query).all()
        if len(assignments) != 1:
            raise ResourceConflict("Select a worker to review")
        assignment = assignments[0]
    if payload.assignee_id is not None:
        assignment = db.scalar(assignment_query)
    if assignment is None:
        raise ResourceNotFound
    if assignment.status != "submitted":
        raise ResourceConflict("Only tasks awaiting review can be resolved")
    if payload.approved:
        assignment.status = "completed"
        assignment.completed_at = datetime.now(timezone.utc)
        assignment.review_comment = payload.comment.strip() if payload.comment else None
    else:
        assignment.status = "assigned"
        assignment.submitted_at = None
        assignment.completed_at = None
        assignment.review_comment = (
            payload.comment.strip() if payload.comment else "Changes requested"
        )
    task.review_comment = assignment.review_comment
    _refresh_task_status(db, task)
    db.commit()
    db.refresh(task)
    return task


def _refresh_task_status(db: Session, task: TeamTask) -> None:
    assignments = db.scalars(
        select(TeamTaskAssignment).where(TeamTaskAssignment.task_id == task.id)
    ).all()
    statuses = [assignment.status for assignment in assignments]
    if statuses and all(status == "completed" for status in statuses):
        task.status = "completed"
        completed_times = [
            assignment.completed_at
            for assignment in assignments
            if assignment.completed_at is not None
        ]
        task.completed_at = max(
            completed_times,
            key=lambda value: _timestamp_order(value),
        )
        task.submitted_at = None
    elif "submitted" in statuses:
        task.status = "submitted"
        submitted_times = [
            assignment.submitted_at
            for assignment in assignments
            if assignment.submitted_at is not None
        ]
        task.submitted_at = max(
            submitted_times,
            key=lambda value: _timestamp_order(value),
        )
        task.completed_at = None
    elif statuses and all(status == "declined" for status in statuses):
        task.status = "declined"
        task.submitted_at = None
        task.completed_at = None
    elif "pending_approval" in statuses:
        task.status = "pending_approval"
        task.submitted_at = None
        task.completed_at = None
    else:
        task.status = "assigned"
        task.submitted_at = None
        task.completed_at = None


def _timestamp_order(value: datetime) -> float:
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return normalized.timestamp()
