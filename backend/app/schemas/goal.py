from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GoalStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20_000)
    due_at: datetime | None = None

    @field_validator("due_at")
    @classmethod
    def require_future_due_date(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Due date must include a timezone")
            if value <= datetime.now(timezone.utc):
                raise ValueError("Due date must be in the future")
        return value


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    due_at: datetime | None = None

    @field_validator("due_at")
    @classmethod
    def require_future_due_date(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Due date must include a timezone")
            if value <= datetime.now(timezone.utc):
                raise ValueError("Due date must be in the future")
        return value

    @model_validator(mode="after")
    def require_editable_field(self) -> "GoalUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one goal field must be provided")
        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
            if field in {"title", "description"}
        ):
            raise ValueError("Updated fields cannot be null")
        return self


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str
    status: GoalStatus
    final_report: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    due_at: datetime | None


class GoalList(BaseModel):
    items: list[GoalRead]
    total: int
    limit: int
    offset: int
