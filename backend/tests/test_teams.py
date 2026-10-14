from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.team import TeamTask


def register_and_login(client: TestClient, email: str) -> dict[str, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-pass-123"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secure-pass-123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_team_with_worker(client: TestClient, owner_email: str):
    leader_headers = register_and_login(client, owner_email)
    created_team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Product crew"},
    )
    assert created_team.status_code == 201
    team_id = created_team.json()["id"]

    invitation = client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "worker@example.com"},
    )
    assert invitation.status_code == 201
    assert invitation.json()["accepted"] is False

    worker_headers = register_and_login(client, "worker@example.com")
    return team_id, leader_headers, worker_headers


def task_payload(assignee_id: int, start: datetime, deadline: datetime) -> dict:
    return {
        "title": "Prepare weekly report",
        "description": "Collect team progress and write a concise summary.",
        "assignee_id": assignee_id,
        "start_at": start.isoformat(),
        "deadline_at": deadline.isoformat(),
    }


def test_team_invite_auto_joins_after_registration(client: TestClient) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )

    details = client.get(f"/api/v1/teams/{team_id}", headers=leader_headers)
    assert details.status_code == 200
    assert details.json()["role"] == "leader"
    assert {member["email"] for member in details.json()["members"]} == {
        "leader@example.com",
        "worker@example.com",
    }
    assert details.json()["invites"][0]["accepted"] is True

    worker_teams = client.get("/api/v1/teams", headers=worker_headers)
    assert worker_teams.status_code == 200
    assert worker_teams.json()[0]["role"] == "worker"
    assert worker_teams.json()[0]["member_count"] == 2
    worker_details = client.get(f"/api/v1/teams/{team_id}", headers=worker_headers)
    assert worker_details.status_code == 200
    assert worker_details.json()["invites"] == []


def test_team_and_task_endpoints_require_login(client: TestClient) -> None:
    assert client.get("/api/v1/teams").status_code == 401
    assert client.post("/api/v1/teams", json={"name": "No access"}).status_code == 401
    assert client.get("/api/v1/tasks/1").status_code == 401


def test_worker_searches_discoverable_team_and_requests_leader_approval(
    client: TestClient,
) -> None:
    leader_headers = register_and_login(client, "discovery-leader@example.com")
    private_team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Private room"},
    )
    public_team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Research crew"},
    )
    assert private_team.status_code == 201
    assert private_team.json()["is_discoverable"] is False
    public_team_id = public_team.json()["id"]
    enabled = client.patch(
        f"/api/v1/teams/{public_team_id}/discoverability",
        headers=leader_headers,
        json={"is_discoverable": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["is_discoverable"] is True

    worker_headers = register_and_login(client, "searching-worker@example.com")
    discovery = client.get(
        "/api/v1/teams/discover?q=research",
        headers=worker_headers,
    )
    assert discovery.status_code == 200
    assert [team["id"] for team in discovery.json()] == [public_team_id]
    assert "leader_id" not in discovery.json()[0]

    request = client.post(
        f"/api/v1/teams/{public_team_id}/join-requests",
        headers=worker_headers,
    )
    assert request.status_code == 201
    assert request.json()["status"] == "pending"

    worker_teams = client.get("/api/v1/teams", headers=worker_headers)
    assert all(team["id"] != public_team_id for team in worker_teams.json())
    worker_details = client.get(
        f"/api/v1/teams/{public_team_id}",
        headers=worker_headers,
    )
    assert worker_details.status_code == 404

    leader_details = client.get(
        f"/api/v1/teams/{public_team_id}",
        headers=leader_headers,
    )
    assert leader_details.json()["join_requests"][0]["email"] == "searching-worker@example.com"

    approved = client.patch(
        f"/api/v1/teams/{public_team_id}/join-requests/{request.json()['id']}",
        headers=leader_headers,
        json={"approve": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    memberships = client.get("/api/v1/teams", headers=worker_headers)
    assert any(team["id"] == public_team_id for team in memberships.json())


def test_worker_can_resubmit_after_leader_rejects_join_request(
    client: TestClient,
) -> None:
    leader_headers = register_and_login(client, "reject-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Open to join", "is_discoverable": True},
    ).json()
    worker_headers = register_and_login(client, "requester@example.com")
    request = client.post(
        f"/api/v1/teams/{team['id']}/join-requests",
        headers=worker_headers,
    ).json()

    rejected = client.patch(
        f"/api/v1/teams/{team['id']}/join-requests/{request['id']}",
        headers=leader_headers,
        json={"approve": False},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    again = client.post(
        f"/api/v1/teams/{team['id']}/join-requests",
        headers=worker_headers,
    )
    assert again.status_code == 201
    assert again.json()["status"] == "pending"


def test_private_team_cannot_be_found_or_joined(client: TestClient) -> None:
    leader_headers = register_and_login(client, "private-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Invite only"},
    ).json()
    worker_headers = register_and_login(client, "private-worker@example.com")

    assert client.get(
        "/api/v1/teams/discover?q=invite", headers=worker_headers
    ).json() == []
    assert client.post(
        f"/api/v1/teams/{team['id']}/join-requests",
        headers=worker_headers,
    ).status_code == 404


def test_non_leader_cannot_change_discoverability_or_approve_join_requests(
    client: TestClient,
) -> None:
    leader_headers = register_and_login(client, "owner@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Review team", "is_discoverable": True},
    ).json()
    worker_headers = register_and_login(client, "joiner@example.com")
    request = client.post(
        f"/api/v1/teams/{team['id']}/join-requests",
        headers=worker_headers,
    ).json()
    approved = client.patch(
        f"/api/v1/teams/{team['id']}/join-requests/{request['id']}",
        headers=leader_headers,
        json={"approve": True},
    )
    assert approved.status_code == 200

    assert client.patch(
        f"/api/v1/teams/{team['id']}/discoverability",
        headers=worker_headers,
        json={"is_discoverable": False},
    ).status_code == 409
    assert client.patch(
        f"/api/v1/teams/{team['id']}/join-requests/{request['id']}",
        headers=worker_headers,
        json={"approve": True},
    ).status_code == 409


def test_leader_assigns_task_worker_submits_and_leader_reviews(
    client: TestClient,
    db_session: Session,
) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    deadline = start + timedelta(hours=4)

    created = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(worker_id, start, deadline),
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert created.json()["status"] == "assigned"
    assert created.json()["start_at"].endswith("Z")

    worker_view = client.get(
        f"/api/v1/tasks/{task_id}", headers=worker_headers
    )
    assert worker_view.status_code == 200
    assert worker_view.json()["assignee_email"] == "worker@example.com"

    new_start = start + timedelta(minutes=15)
    new_deadline = deadline + timedelta(hours=2)
    updated_schedule = client.patch(
        f"/api/v1/tasks/{task_id}/schedule",
        headers=leader_headers,
        json={
            "start_at": new_start.isoformat(),
            "deadline_at": new_deadline.isoformat(),
        },
    )
    assert updated_schedule.status_code == 200
    assert updated_schedule.json()["deadline_at"].endswith("Z")

    worker_list = client.get(
        f"/api/v1/teams/{team_id}/tasks", headers=worker_headers
    )
    assert [task["id"] for task in worker_list.json()] == [task_id]

    submitted = client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=worker_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    submitted_schedule = client.patch(
        f"/api/v1/tasks/{task_id}/schedule",
        headers=leader_headers,
        json=task_payload(worker_id, new_start, new_deadline + timedelta(hours=2)),
    )
    assert submitted_schedule.status_code == 200
    review_deadline = new_deadline + timedelta(hours=2)

    rejected = client.post(
        f"/api/v1/tasks/{task_id}/review",
        headers=leader_headers,
        json={"approved": False, "comment": "Please add the missing summary."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "assigned"
    assert rejected.json()["review_comment"] == "Please add the missing summary."

    resubmitted = client.post(
        f"/api/v1/tasks/{task_id}/submit", headers=worker_headers
    )
    assert resubmitted.status_code == 200
    approved = client.post(
        f"/api/v1/tasks/{task_id}/review",
        headers=leader_headers,
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["completed_at"] is not None

    task = db_session.get(TeamTask, task_id)
    assert task is not None
    assert task.status == "completed"
    locked_schedule = client.patch(
        f"/api/v1/tasks/{task_id}/schedule",
        headers=leader_headers,
        json=task_payload(worker_id, new_start, review_deadline + timedelta(hours=1)),
    )
    assert locked_schedule.status_code == 409


def test_leader_assigns_same_task_to_all_workers(client: TestClient) -> None:
    team_id, leader_headers, first_worker_headers = create_team_with_worker(
        client, "bulk-leader@example.com"
    )
    second_invite = client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "second-worker@example.com"},
    )
    assert second_invite.status_code == 201
    second_worker_headers = register_and_login(client, "second-worker@example.com")
    members = client.get(
        f"/api/v1/teams/{team_id}", headers=leader_headers
    ).json()["members"]
    worker_ids = {
        member["user_id"] for member in members if member["role"] == "worker"
    }
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    deadline = start + timedelta(hours=4)

    created = client.post(
        f"/api/v1/teams/{team_id}/tasks/bulk",
        headers=leader_headers,
        json={
            "title": "Review release checklist",
            "description": "Complete the shared release checklist.",
            "assignee_ids": sorted(worker_ids),
            "start_at": start.isoformat(),
            "deadline_at": deadline.isoformat(),
        },
    )

    assert created.status_code == 201, created.text
    task = created.json()
    task_id = task["id"]
    assert len(task["assignments"]) == 2
    assert {assignment["user_id"] for assignment in task["assignments"]} == worker_ids
    assert {assignment["status"] for assignment in task["assignments"]} == {"assigned"}
    for headers in (first_worker_headers, second_worker_headers):
        worker_tasks = client.get(
            f"/api/v1/teams/{team_id}/tasks", headers=headers
        )
        assert [item["id"] for item in worker_tasks.json()] == [task_id]

    first_worker_id = next(
        assignment["user_id"]
        for assignment in task["assignments"]
        if assignment["email"] == "worker@example.com"
    )
    first_submission = client.post(
        f"/api/v1/tasks/{task_id}/submit", headers=first_worker_headers
    )
    assert first_submission.status_code == 200
    assert first_submission.json()["current_assignment"]["status"] == "submitted"
    first_approval = client.post(
        f"/api/v1/tasks/{task_id}/review",
        headers=leader_headers,
        json={"approved": True, "assignee_id": first_worker_id},
    )
    assert first_approval.status_code == 200
    assert first_approval.json()["id"] == task_id
    assert first_approval.json()["status"] == "assigned"
    assert {
        assignment["status"] for assignment in first_approval.json()["assignments"]
    } == {"assigned", "completed"}

    second_submission = client.post(
        f"/api/v1/tasks/{task_id}/submit", headers=second_worker_headers
    )
    assert second_submission.status_code == 200
    second_worker_id = next(
        assignment["user_id"]
        for assignment in task["assignments"]
        if assignment["email"] == "second-worker@example.com"
    )
    second_approval = client.post(
        f"/api/v1/tasks/{task_id}/review",
        headers=leader_headers,
        json={"approved": True, "assignee_id": second_worker_id},
    )
    assert second_approval.status_code == 200
    assert second_approval.json()["id"] == task_id
    assert second_approval.json()["status"] == "completed"
    assert {
        assignment["status"] for assignment in second_approval.json()["assignments"]
    } == {"completed"}


def test_only_team_leader_can_invite_assign_or_change_schedule(
    client: TestClient,
) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    deadline = start + timedelta(hours=3)

    forbidden_invite = client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=worker_headers,
        json={"email": "another@example.com"},
    )
    assert forbidden_invite.status_code == 409

    forbidden_assign = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=worker_headers,
        json=task_payload(worker_id, start, deadline),
    )
    assert forbidden_assign.status_code == 409

    task = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(worker_id, start, deadline),
    ).json()
    unauthorized_schedule = client.patch(
        f"/api/v1/tasks/{task['id']}/schedule",
        headers=worker_headers,
        json={
            "start_at": start.isoformat(),
            "deadline_at": (deadline + timedelta(hours=1)).isoformat(),
        },
    )
    assert unauthorized_schedule.status_code == 409


def test_task_arguments_and_authorization_are_validated(client: TestClient) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    start = datetime.now(timezone.utc)
    invalid_schedule = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(worker_id, start, start),
    )
    assert invalid_schedule.status_code == 422

    naive_schedule = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(
            worker_id,
            start.replace(tzinfo=None),
            (start + timedelta(hours=1)).replace(tzinfo=None),
        ),
    )
    assert naive_schedule.status_code == 422

    unauthenticated = client.get(f"/api/v1/teams/{team_id}")
    assert unauthenticated.status_code == 401

    stranger_headers = register_and_login(client, "stranger@example.com")
    assert client.get(
        f"/api/v1/teams/{team_id}", headers=stranger_headers
    ).status_code == 404


def test_workers_cannot_submit_another_workers_task(client: TestClient) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )
    stranger_headers = register_and_login(client, "stranger@example.com")
    start = datetime.now(timezone.utc) + timedelta(minutes=10)
    deadline = start + timedelta(hours=2)
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    task = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(worker_id, start, deadline),
    ).json()

    assert client.post(
        f"/api/v1/tasks/{task['id']}/submit", headers=stranger_headers
    ).status_code == 404
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=stranger_headers).status_code == 404
    assert client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers=worker_headers,
        json={"approved": True},
    ).status_code == 409


@pytest.mark.parametrize("payload", [{}, {"approved": True}])
def test_review_only_resolves_submitted_task(client: TestClient, payload: dict) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "leader@example.com"
    )
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    start = datetime.now(timezone.utc) + timedelta(minutes=10)
    deadline = start + timedelta(hours=2)
    task = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json=task_payload(worker_id, start, deadline),
    ).json()

    response = client.post(
        f"/api/v1/tasks/{task['id']}/review",
        headers=leader_headers,
        json=payload,
    )
    assert response.status_code in {409, 422}


def test_worker_task_request_requires_leader_approval_before_work_starts(
    client: TestClient,
) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "request-leader@example.com"
    )
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    leader_id = client.get("/api/v1/auth/me", headers=leader_headers).json()["id"]
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    deadline = start + timedelta(hours=2)
    payload = {
        "title": "Document deployment steps",
        "description": "Write and verify the team's deployment guide.",
        "start_at": start.isoformat(),
        "deadline_at": deadline.isoformat(),
    }

    created = client.post(
        f"/api/v1/teams/{team_id}/task-requests",
        headers=worker_headers,
        json=payload,
    )
    assert created.status_code == 201
    request = created.json()
    assert request["status"] == "pending_approval"
    assert request["assignee_id"] == worker_id
    assert request["requested_by"] == worker_id

    assert client.get(
        f"/api/v1/teams/{team_id}/tasks", headers=leader_headers
    ).json()[0]["id"] == request["id"]
    assert client.get(
        f"/api/v1/teams/{team_id}/tasks", headers=worker_headers
    ).json()[0]["id"] == request["id"]
    assert client.post(
        f"/api/v1/tasks/{request['id']}/submit",
        headers=worker_headers,
    ).status_code == 409
    assert client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=worker_headers,
        json={"approved": True},
    ).status_code == 409

    approved = client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=leader_headers,
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "assigned"
    assert approved.json()["assigned_by"] == leader_id
    submitted = client.post(
        f"/api/v1/tasks/{request['id']}/submit",
        headers=worker_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"


def test_leader_can_decline_worker_task_request(
    client: TestClient,
) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "decline-leader@example.com"
    )
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    request = client.post(
        f"/api/v1/teams/{team_id}/task-requests",
        headers=worker_headers,
        json={
            "title": "Improve onboarding",
            "description": "Create a short onboarding checklist.",
            "start_at": start.isoformat(),
            "deadline_at": (start + timedelta(hours=2)).isoformat(),
        },
    ).json()

    declined = client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=leader_headers,
        json={"approved": False, "comment": "Please narrow the scope first."},
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"
    assert declined.json()["review_comment"] == "Please narrow the scope first."
    assert client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=leader_headers,
        json={"approved": True},
    ).status_code == 409


def test_worker_can_edit_and_resubmit_declined_task_request(
    client: TestClient,
) -> None:
    team_id, leader_headers, worker_headers = create_team_with_worker(
        client, "edit-declined-leader@example.com"
    )
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    request = client.post(
        f"/api/v1/teams/{team_id}/task-requests",
        headers=worker_headers,
        json={
            "title": "Improve onboarding",
            "description": "Create a broad onboarding program.",
            "start_at": start.isoformat(),
            "deadline_at": (start + timedelta(hours=2)).isoformat(),
        },
    ).json()
    client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=leader_headers,
        json={"approved": False, "comment": "Please narrow the scope."},
    )

    edited_start = start + timedelta(hours=2)
    edited = client.patch(
        f"/api/v1/tasks/{request['id']}/request",
        headers=worker_headers,
        json={
            "title": "Create onboarding checklist",
            "description": "Write a concise checklist for new team members.",
            "start_at": edited_start.isoformat(),
            "deadline_at": (edited_start + timedelta(hours=1)).isoformat(),
        },
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "pending_approval"
    assert edited.json()["title"] == "Create onboarding checklist"
    assert edited.json()["description"] == "Write a concise checklist for new team members."
    assert edited.json()["review_comment"] is None
    assert client.post(
        f"/api/v1/tasks/{request['id']}/submit",
        headers=worker_headers,
    ).status_code == 409
    assert client.post(
        f"/api/v1/tasks/{request['id']}/approval",
        headers=leader_headers,
        json={"approved": True},
    ).json()["status"] == "assigned"

    not_declined = client.patch(
        f"/api/v1/tasks/{request['id']}/request",
        headers=worker_headers,
        json={
            "title": "Another edit",
            "description": "Cannot edit after approval.",
            "start_at": edited_start.isoformat(),
            "deadline_at": (edited_start + timedelta(hours=1)).isoformat(),
        },
    )
    assert not_declined.status_code == 409
