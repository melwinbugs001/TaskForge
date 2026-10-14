from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.goal import Goal


def test_goal_crud_and_list_are_scoped_to_owner(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "Compare frameworks", "description": "Research three frameworks"},
    )
    assert created.status_code == 201
    goal = created.json()
    assert goal["status"] == "draft"

    listed = client.get("/api/v1/goals", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == goal["id"]

    fetched = client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
    assert fetched.status_code == 200

    updated = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=auth_headers,
        json={"title": "Compare open-source frameworks"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Compare open-source frameworks"

    deleted = client.delete(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers).status_code == 404


def test_goal_create_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/goals",
        json={"title": "Goal", "description": "Description"},
    )

    assert response.status_code == 401


def test_goal_plan_endpoint_is_not_available(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/goals/1/plan", headers=auth_headers)
    assert response.status_code == 404


def test_goal_create_validates_input(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "", "description": "Research"},
    )

    assert response.status_code == 422


def test_goal_is_not_visible_or_mutable_to_another_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    goal_response = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "Private", "description": "Owner-only"},
    )
    goal_id = goal_response.json()["id"]

    client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "another-pass-123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "another-pass-123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get(f"/api/v1/goals/{goal_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/v1/goals/{goal_id}",
        headers=other_headers,
        json={"title": "Takeover"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/goals/{goal_id}", headers=other_headers
    ).status_code == 404
    assert client.get("/api/v1/goals", headers=other_headers).json()["total"] == 0


def test_goal_patch_requires_fields_and_rejects_blank_value(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    goal = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "Goal", "description": "Description"},
    ).json()

    assert client.patch(
        f"/api/v1/goals/{goal['id']}", headers=auth_headers, json={}
    ).status_code == 422
    assert client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=auth_headers,
        json={"title": "   "},
    ).status_code == 422


def test_draft_goal_can_be_marked_completed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    goal = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "Goal", "description": "Description"},
    ).json()

    completed = client.post(
        f"/api/v1/goals/{goal['id']}/complete", headers=auth_headers
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None
    assert client.post(
        f"/api/v1/goals/{goal['id']}/complete", headers=auth_headers
    ).status_code == 409


def test_overdue_unfinished_goal_is_marked_failed(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    due_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    goal = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={
            "title": "Overdue goal",
            "description": "Finish this work",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    ).json()
    invalid_due_date = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=auth_headers,
        json={"due_at": due_at},
    )
    assert invalid_due_date.status_code == 422

    goal_record = db_session.get(Goal, goal["id"])
    assert goal_record is not None
    goal_record.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    overdue = client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
    assert overdue.status_code == 200
    assert overdue.json()["status"] == "failed"


def test_only_draft_goals_can_be_edited_or_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    goal_response = client.post(
        "/api/v1/goals",
        headers=auth_headers,
        json={"title": "Goal", "description": "Description"},
    )
    goal = db_session.get(Goal, goal_response.json()["id"])
    assert goal is not None
    goal.status = "running"
    db_session.commit()

    assert client.patch(
        f"/api/v1/goals/{goal.id}",
        headers=auth_headers,
        json={"title": "Updated"},
    ).status_code == 409
    assert client.delete(
        f"/api/v1/goals/{goal.id}", headers=auth_headers
    ).status_code == 409


def test_goal_endpoints_require_authentication(client: TestClient) -> None:
    requests = (
        ("post", "/api/v1/goals", {"title": "Goal", "description": "Description"}),
        ("get", "/api/v1/goals", None),
        ("get", "/api/v1/goals/1", None),
        ("patch", "/api/v1/goals/1", {"title": "Updated"}),
        ("delete", "/api/v1/goals/1", None),
    )
    for method, path, payload in requests:
        response = getattr(client, method)(
            path,
            json=payload,
        ) if payload is not None else getattr(client, method)(path)
        assert response.status_code == 401


def test_goal_list_validates_pagination(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/goals?limit=101", headers=auth_headers)

    assert response.status_code == 422
