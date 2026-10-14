from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamInvite, TeamJoinRequest, TeamMember
from app.models.user import User
from app.schemas.team import (
    DiscoverableTeamRead,
    JoinRequestStatus,
    TeamCreate,
    TeamDiscoverabilityUpdate,
    TeamInviteCreate,
)
from app.services.errors import ResourceConflict, ResourceNotFound


def _member(db: Session, team_id: int, user_id: int) -> TeamMember:
    member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    if member is None:
        raise ResourceNotFound
    return member


def require_team_membership(
    db: Session, team_id: int, user_id: int
) -> TeamMember:
    return _member(db, team_id, user_id)


def require_team_leader(db: Session, team_id: int, user_id: int) -> Team:
    member = _member(db, team_id, user_id)
    if member.role != "leader":
        raise ResourceConflict("Only this team's leader can perform that action")
    team = db.get(Team, team_id)
    if team is None:
        raise ResourceNotFound
    return team


def require_team_member(db: Session, team_id: int, user_id: int) -> Team:
    require_team_membership(db, team_id, user_id)
    team = db.get(Team, team_id)
    if team is None:
        raise ResourceNotFound
    return team


def create_team(db: Session, leader_id: int, payload: TeamCreate) -> Team:
    name = payload.name.strip()
    if not name:
        raise ValueError("Team name must not be blank")
    team = Team(
        name=name,
        leader_id=leader_id,
        is_discoverable=payload.is_discoverable,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=leader_id, role="leader"))
    db.commit()
    db.refresh(team)
    return team


def list_teams(db: Session, user_id: int) -> list[dict[str, object]]:
    member_count = (
        select(func.count(TeamMember.id))
        .where(TeamMember.team_id == Team.id)
        .correlate(Team)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            Team,
            TeamMember.role,
            member_count.label("member_count"),
        )
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id)
        .order_by(Team.created_at.desc(), Team.id.desc())
    ).all()
    result: list[dict[str, object]] = []
    for team, role, member_count in rows:
        pending = db.scalar(
            select(func.count(TeamInvite.id)).where(
                TeamInvite.team_id == team.id,
                TeamInvite.accepted_at.is_(None),
            )
        ) or 0
        result.append(
            {
                "id": team.id,
                "name": team.name,
                "is_discoverable": team.is_discoverable,
                "leader_id": team.leader_id,
                "created_at": team.created_at,
                "role": role,
                "member_count": member_count,
                "pending_invite_count": pending if role == "leader" else 0,
            }
        )
    return result


def get_team(db: Session, team_id: int, user_id: int) -> dict[str, object]:
    team = require_team_member(db, team_id, user_id)
    current_member = _member(db, team_id, user_id)
    member_rows = db.execute(
        select(TeamMember, User.email)
        .join(User, User.id == TeamMember.user_id)
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at, TeamMember.id)
    ).all()
    invites = list(
        db.scalars(
            select(TeamInvite)
            .where(TeamInvite.team_id == team_id)
            .order_by(TeamInvite.created_at.desc())
        )
    )
    join_requests = list(
        db.execute(
            select(TeamJoinRequest, User.email)
            .join(User, User.id == TeamJoinRequest.user_id)
            .where(
                TeamJoinRequest.team_id == team_id,
                TeamJoinRequest.status == "pending",
            )
            .order_by(TeamJoinRequest.created_at, TeamJoinRequest.id)
        )
    ) if current_member.role == "leader" else []
    return {
        "id": team.id,
        "name": team.name,
        "is_discoverable": team.is_discoverable,
        "leader_id": team.leader_id,
        "created_at": team.created_at,
        "role": current_member.role,
        "member_count": len(member_rows),
        "pending_invite_count": (
            sum(invite.accepted_at is None for invite in invites)
            if current_member.role == "leader"
            else 0
        ),
        "members": [
            {
                "user_id": member.user_id,
                "email": email,
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member, email in member_rows
        ],
        "invites": [
            {
                "email": invite.email,
                "created_at": invite.created_at,
                "accepted": invite.accepted_at is not None,
            }
            for invite in invites
        ] if current_member.role == "leader" else [],
        "join_requests": [
            {
                "id": request.id,
                "team_id": request.team_id,
                "user_id": request.user_id,
                "email": email,
                "status": request.status,
                "created_at": request.created_at,
            }
            for request, email in join_requests
        ],
    }


def search_discoverable_teams(
    db: Session,
    user_id: int,
    query_text: str,
    limit: int = 50,
) -> list[dict[str, object]]:
    member_count = (
        select(func.count(TeamMember.id))
        .where(TeamMember.team_id == Team.id)
        .correlate(Team)
        .scalar_subquery()
    )
    request_status = (
        select(TeamJoinRequest.status)
        .where(
            TeamJoinRequest.team_id == Team.id,
            TeamJoinRequest.user_id == user_id,
        )
        .correlate(Team)
        .scalar_subquery()
    )
    statement = (
        select(Team.id, Team.name, member_count.label("member_count"), request_status)
        .where(Team.is_discoverable.is_(True))
        .order_by(Team.name, Team.id)
        .limit(limit)
    )
    normalized_query = query_text.strip()
    if normalized_query:
        statement = statement.where(Team.name.ilike(f"%{normalized_query}%"))
    rows = db.execute(statement).all()
    return [
        {
            "id": team_id,
            "name": name,
            "member_count": member_count,
            "request_status": request_status,
        }
        for team_id, name, member_count, request_status in rows
        if db.scalar(
            select(TeamMember.id).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        is None
    ]


def set_team_discoverability(
    db: Session,
    team_id: int,
    leader_id: int,
    payload: TeamDiscoverabilityUpdate,
) -> Team:
    team = require_team_leader(db, team_id, leader_id)
    team.is_discoverable = payload.is_discoverable
    db.commit()
    db.refresh(team)
    return team


def request_to_join(db: Session, team_id: int, user_id: int) -> TeamJoinRequest:
    team = db.get(Team, team_id)
    if team is None or not team.is_discoverable:
        raise ResourceNotFound
    if db.scalar(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    ):
        raise ResourceConflict("You are already a member of this team")
    request = db.scalar(
        select(TeamJoinRequest).where(
            TeamJoinRequest.team_id == team_id,
            TeamJoinRequest.user_id == user_id,
        )
    )
    if request is not None:
        if request.status == "pending":
            raise ResourceConflict("Your join request is already pending")
        if request.status == "approved":
            raise ResourceConflict("Your join request has already been approved")
        request.status = "pending"
        request.created_at = datetime.now(timezone.utc)
        request.resolved_at = None
        request.resolved_by = None
    else:
        request = TeamJoinRequest(
            team_id=team_id,
            user_id=user_id,
            status="pending",
        )
        db.add(request)
    db.commit()
    db.refresh(request)
    return request


def review_join_request(
    db: Session,
    team_id: int,
    request_id: int,
    leader_id: int,
    approve: bool,
) -> TeamJoinRequest:
    require_team_leader(db, team_id, leader_id)
    request = db.scalar(
        select(TeamJoinRequest).where(
            TeamJoinRequest.id == request_id,
            TeamJoinRequest.team_id == team_id,
        )
    )
    if request is None:
        raise ResourceNotFound
    if request.status != "pending":
        raise ResourceConflict("This join request has already been resolved")
    request.status = "approved" if approve else "rejected"
    request.resolved_at = datetime.now(timezone.utc)
    request.resolved_by = leader_id
    if approve:
        membership = db.scalar(
            select(TeamMember.id).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == request.user_id,
            )
        )
        if membership is None:
            db.add(
                TeamMember(
                    team_id=team_id,
                    user_id=request.user_id,
                    role="worker",
                )
            )
    db.commit()
    db.refresh(request)
    return request


def invite_member(
    db: Session, team_id: int, leader_id: int, payload: TeamInviteCreate
) -> TeamInvite:
    require_team_leader(db, team_id, leader_id)
    email = str(payload.email).lower()
    existing_invite = db.scalar(
        select(TeamInvite).where(
            TeamInvite.team_id == team_id,
            TeamInvite.email == email,
        )
    )
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_invite is not None:
        if existing_invite.accepted_at is not None:
            raise ResourceConflict("This person is already a team member")
        raise ResourceConflict("This email already has a pending invitation")
    if existing_user is not None and db.scalar(
        select(TeamMember.id).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == existing_user.id,
        )
    ):
        raise ResourceConflict("This person is already a team member")

    invite = TeamInvite(team_id=team_id, email=email, invited_by=leader_id)
    db.add(invite)
    if existing_user is not None:
        db.add(
            TeamMember(team_id=team_id, user_id=existing_user.id, role="worker")
        )
        invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invite)
    return invite


def accept_pending_invites(db: Session, user: User) -> None:
    pending = list(
        db.scalars(
            select(TeamInvite).where(
                TeamInvite.email == user.email.lower(),
                TeamInvite.accepted_at.is_(None),
            )
        )
    )
    if not pending:
        return
    now = datetime.now(timezone.utc)
    for invite in pending:
        membership = db.scalar(
            select(TeamMember.id).where(
                TeamMember.team_id == invite.team_id,
                TeamMember.user_id == user.id,
            )
        )
        if membership is None:
            db.add(
                TeamMember(team_id=invite.team_id, user_id=user.id, role="worker")
            )
        invite.accepted_at = now
