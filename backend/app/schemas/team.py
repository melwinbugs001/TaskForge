from datetime import datetime, timezone
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class TeamRole(StrEnum):
    LEADER = "leader"
    WORKER = "worker"


class TeamTaskStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    DECLINED = "declined"


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_discoverable: bool = False


class TeamDiscoverabilityUpdate(BaseModel):
    is_discoverable: bool


class TeamJoinRequestReview(BaseModel):
    approve: bool


class JoinRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_discoverable: bool
    leader_id: int
    created_at: datetime
    role: TeamRole
    member_count: int
    pending_invite_count: int


class TeamMemberRead(BaseModel):
    user_id: int
    email: EmailStr
    role: TeamRole
    joined_at: datetime


class TeamInviteCreate(BaseModel):
    email: EmailStr


class TeamInviteRead(BaseModel):
    email: EmailStr
    created_at: datetime
    accepted: bool


class TeamJoinRequestRead(BaseModel):
    id: int
    team_id: int
    user_id: int
    email: EmailStr
    status: JoinRequestStatus
    created_at: datetime


class DiscoverableTeamRead(BaseModel):
    id: int
    name: str
    member_count: int
    request_status: JoinRequestStatus | None


class TeamDetail(TeamRead):
    members: list[TeamMemberRead]
    invites: list[TeamInviteRead]
    join_requests: list[TeamJoinRequestRead]


class TeamTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    assignee_id: int = Field(gt=0)
    start_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def validate_schedule(self) -> "TeamTaskCreate":
        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must include a timezone")
        if self.deadline_at.tzinfo is None or self.deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must include a timezone")
        if self.start_at >= self.deadline_at:
            raise ValueError("deadline_at must be after start_at")
        return self


class TeamTaskBulkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    assignee_ids: list[int] = Field(min_length=1)
    start_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def validate_assignment(self) -> "TeamTaskBulkCreate":
        if any(user_id < 1 for user_id in self.assignee_ids):
            raise ValueError("assignee_ids must contain positive user IDs")
        if len(set(self.assignee_ids)) != len(self.assignee_ids):
            raise ValueError("assignee_ids must not contain duplicates")
        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must include a timezone")
        if self.deadline_at.tzinfo is None or self.deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must include a timezone")
        if self.start_at >= self.deadline_at:
            raise ValueError("deadline_at must be after start_at")
        return self


class TaskRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    start_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def validate_schedule(self) -> "TaskRequestCreate":
        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must include a timezone")
        if self.deadline_at.tzinfo is None or self.deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must include a timezone")
        if self.start_at >= self.deadline_at:
            raise ValueError("deadline_at must be after start_at")
        return self


class TaskScheduleUpdate(BaseModel):
    start_at: datetime
    deadline_at: datetime

    @model_validator(mode="after")
    def validate_schedule(self) -> "TaskScheduleUpdate":
        if self.start_at.tzinfo is None or self.start_at.utcoffset() is None:
            raise ValueError("start_at must include a timezone")
        if self.deadline_at.tzinfo is None or self.deadline_at.utcoffset() is None:
            raise ValueError("deadline_at must include a timezone")
        if self.start_at >= self.deadline_at:
            raise ValueError("deadline_at must be after start_at")
        return self


class TaskReview(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=2000)
    assignee_id: int | None = Field(default=None, gt=0)


class TaskRequestReview(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=2000)


class TeamTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    title: str
    description: str
    assignee_id: int
    assigned_by: int
    requested_by: int | None
    start_at: datetime
    deadline_at: datetime
    status: TeamTaskStatus
    submitted_at: datetime | None
    completed_at: datetime | None
    review_comment: str | None
    assignments: list["TeamTaskAssignmentRead"] = Field(default_factory=list)
    current_assignment: "TeamTaskAssignmentRead | None" = None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "start_at",
        "deadline_at",
        "submitted_at",
        "completed_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def normalize_sqlite_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class TeamTaskDetail(TeamTaskRead):
    assignee_email: EmailStr


class TeamTaskAssignmentRead(BaseModel):
    user_id: int
    email: EmailStr
    status: TeamTaskStatus
    submitted_at: datetime | None
    completed_at: datetime | None
    review_comment: str | None
