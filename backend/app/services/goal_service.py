from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.errors import ResourceConflict, ResourceNotFound

EDITABLE_STATUSES = {"draft"}
DELETABLE_STATUSES = {"draft"}
UNFINISHED_STATUSES = {"draft", "running", "waiting_for_approval"}


def _fail_overdue_goals(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    overdue_goals = db.scalars(
        select(Goal).where(
            Goal.user_id == user_id,
            Goal.status.in_(UNFINISHED_STATUSES),
            Goal.due_at.is_not(None),
        )
    )
    changed = False
    for goal in overdue_goals:
        due_at = goal.due_at
        if due_at is not None:
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            if due_at <= now:
                goal.status = "failed"
                changed = True
    if changed:
        db.commit()


def create_goal(db: Session, user_id: int, payload: GoalCreate) -> Goal:
    goal = Goal(
        user_id=user_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        status="draft",
        due_at=payload.due_at,
    )
    if not goal.title or not goal.description:
        raise ValueError("Title and description must not be blank")
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(
    db: Session, user_id: int, limit: int, offset: int
) -> tuple[list[Goal], int]:
    _fail_overdue_goals(db, user_id)
    base_query = select(Goal).where(Goal.user_id == user_id)
    goals = list(
        db.scalars(
            base_query.order_by(Goal.created_at.desc(), Goal.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    return goals, total


def get_goal(db: Session, user_id: int, goal_id: int) -> Goal:
    _fail_overdue_goals(db, user_id)
    goal = db.scalar(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    )
    if goal is None:
        raise ResourceNotFound
    return goal


def update_goal(
    db: Session, user_id: int, goal_id: int, payload: GoalUpdate
) -> Goal:
    goal = get_goal(db, user_id, goal_id)
    if goal.status not in EDITABLE_STATUSES:
        raise ResourceConflict("Only draft goals can be edited")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field in {"title", "description"}:
            normalized = value.strip()
            if not normalized:
                raise ValueError(f"{field} must not be blank")
            setattr(goal, field, normalized)
        else:
            setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def complete_goal(db: Session, user_id: int, goal_id: int) -> Goal:
    goal = get_goal(db, user_id, goal_id)
    if goal.status != "draft":
        raise ResourceConflict("Only draft goals can be marked as completed")
    goal.status = "completed"
    goal.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, user_id: int, goal_id: int) -> None:
    goal = get_goal(db, user_id, goal_id)
    if goal.status not in DELETABLE_STATUSES:
        raise ResourceConflict("Only draft goals can be deleted")
    db.delete(goal)
    db.commit()
