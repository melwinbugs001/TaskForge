import json
import base64
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from pywebpush import WebPushException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import app
from app.models.push_subscription import WebPushSubscription
from app.services import push_notifications

PUSH_SETTINGS = Settings(
    database_url="sqlite://",
    jwt_secret="push-test-secret-that-is-long-enough-for-tests",
    vapid_public_key="B" * 65,
    vapid_private_key="unused-private-key-for-mocked-push",
    vapid_subject="mailto:push-tests@example.com",
)
P256DH_KEY = base64.urlsafe_b64encode(b"p" * 65).rstrip(b"=").decode()
AUTH_KEY = base64.urlsafe_b64encode(b"a" * 16).rstrip(b"=").decode()


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


def set_push_settings() -> None:
    app.dependency_overrides[get_settings] = lambda: PUSH_SETTINGS


def subscribe(client: TestClient, headers: dict[str, str], endpoint: str) -> None:
    response = client.post(
        "/api/v1/notifications/subscriptions",
        headers=headers,
        json={
            "endpoint": endpoint,
            "keys": {"p256dh": P256DH_KEY, "auth": AUTH_KEY},
        },
    )
    assert response.status_code == 201, response.text


def test_subscriptions_require_auth_and_are_isolated_per_user(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/notifications/subscriptions").status_code == 401
    assert client.get("/api/v1/notifications/vapid-public-key").status_code == 401
    set_push_settings()
    first_user = register_and_login(client, "first-push-user@example.com")
    second_user = register_and_login(client, "second-push-user@example.com")

    subscribe(client, first_user, "https://push.example.test/device-one")
    subscribe(client, first_user, "https://push.example.test/device-two")

    first_status = client.get(
        "/api/v1/notifications/subscriptions", headers=first_user
    )
    second_status = client.get(
        "/api/v1/notifications/subscriptions", headers=second_user
    )
    assert first_status.json() == {"enabled": True, "subscription_count": 2}
    assert second_status.json() == {"enabled": True, "subscription_count": 0}

    duplicate_on_other_account = client.post(
        "/api/v1/notifications/subscriptions",
        headers=second_user,
        json={
            "endpoint": "https://push.example.test/device-one",
            "keys": {"p256dh": P256DH_KEY, "auth": AUTH_KEY},
        },
    )
    assert duplicate_on_other_account.status_code == 409

    cannot_remove_other_users_subscription = client.request(
        "DELETE",
        "/api/v1/notifications/subscriptions",
        headers=second_user,
        json={"endpoint": "https://push.example.test/device-one"},
    )
    assert cannot_remove_other_users_subscription.json() == {"removed": False}
    still_owned = client.get(
        "/api/v1/notifications/subscriptions", headers=first_user
    )
    assert still_owned.json()["subscription_count"] == 2


def test_rejects_insecure_subscription_endpoint(client: TestClient) -> None:
    headers = register_and_login(client, "invalid-endpoint@example.com")
    response = client.post(
        "/api/v1/notifications/subscriptions",
        headers=headers,
        json={
            "endpoint": "http://push.example.test/device",
            "keys": {"p256dh": P256DH_KEY, "auth": AUTH_KEY},
        },
    )
    assert response.status_code == 422
    private_ip_endpoint = client.post(
        "/api/v1/notifications/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://127.0.0.1/device",
            "keys": {"p256dh": P256DH_KEY, "auth": AUTH_KEY},
        },
    )
    assert private_ip_endpoint.status_code == 422


def test_vapid_key_endpoint_only_returns_the_public_key(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/notifications/vapid-public-key").status_code == 401
    set_push_settings()
    headers = register_and_login(client, "vapid-key-user@example.com")
    response = client.get(
        "/api/v1/notifications/vapid-public-key", headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {"public_key": PUSH_SETTINGS.vapid_public_key}


def test_cors_allows_only_configured_frontend_origins(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/notifications/subscriptions",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    rejected = client.options(
        "/api/v1/notifications/subscriptions",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_task_submission_and_review_notify_right_users_once(
    client: TestClient,
    monkeypatch,
) -> None:
    set_push_settings()
    sender = Mock()
    monkeypatch.setattr(push_notifications, "webpush", sender)
    leader_headers = register_and_login(client, "push-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Push team"},
    ).json()
    team_id = team["id"]
    client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "push-worker@example.com"},
    )
    worker_headers = register_and_login(client, "push-worker@example.com")
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    subscribe(client, leader_headers, "https://push.example.test/leader")
    subscribe(client, worker_headers, "https://push.example.test/worker")

    start = datetime.now(timezone.utc) + timedelta(hours=1)
    deadline = start + timedelta(hours=2)
    created = client.post(
        f"/api/v1/teams/{team_id}/tasks",
        headers=leader_headers,
        json={
            "title": "Prepare release notes",
            "description": "Summarize the release changes.",
            "assignee_id": worker_id,
            "start_at": start.isoformat(),
            "deadline_at": deadline.isoformat(),
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert sender.call_count == 1
    assignment_notice = json.loads(sender.call_args.kwargs["data"])
    assert assignment_notice["title"] == "New task assigned"
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/worker"
    )

    submitted = client.post(
        f"/api/v1/tasks/{task_id}/submit", headers=worker_headers
    )
    assert submitted.status_code == 200
    assert sender.call_count == 2
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/leader"
    )
    submission_notice = json.loads(sender.call_args.kwargs["data"])
    assert submission_notice["title"] == "Task submitted for review"

    retry = client.post(f"/api/v1/tasks/{task_id}/submit", headers=worker_headers)
    assert retry.status_code == 409
    assert sender.call_count == 2

    rejected = client.post(
        f"/api/v1/tasks/{task_id}/review",
        headers=leader_headers,
        json={"approved": False, "comment": "Please include the test summary."},
    )
    assert rejected.status_code == 200
    assert sender.call_count == 3
    rejection_notice = json.loads(sender.call_args.kwargs["data"])
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/worker"
    )
    assert "Please include the test summary" in rejection_notice["body"]

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
    assert sender.call_count == 5
    approval_notice = json.loads(sender.call_args.kwargs["data"])
    assert approval_notice["title"] == "Task approved"


def test_bulk_task_assignment_notifies_each_worker(
    client: TestClient,
    monkeypatch,
) -> None:
    set_push_settings()
    sender = Mock()
    monkeypatch.setattr(push_notifications, "webpush", sender)
    leader_headers = register_and_login(client, "bulk-push-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Bulk notification team"},
    ).json()
    team_id = team["id"]
    client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "bulk-worker-one@example.com"},
    )
    first_worker_headers = register_and_login(client, "bulk-worker-one@example.com")
    client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "bulk-worker-two@example.com"},
    )
    second_worker_headers = register_and_login(client, "bulk-worker-two@example.com")
    worker_ids = [
        client.get("/api/v1/auth/me", headers=headers).json()["id"]
        for headers in (first_worker_headers, second_worker_headers)
    ]
    subscribe(client, first_worker_headers, "https://push.example.test/bulk-one")
    subscribe(client, second_worker_headers, "https://push.example.test/bulk-two")
    start = datetime.now(timezone.utc) + timedelta(hours=1)

    created = client.post(
        f"/api/v1/teams/{team_id}/tasks/bulk",
        headers=leader_headers,
        json={
            "title": "Check shared assignment",
            "description": "Verify each worker received this assignment.",
            "assignee_ids": worker_ids,
            "start_at": start.isoformat(),
            "deadline_at": (start + timedelta(hours=2)).isoformat(),
        },
    )

    assert created.status_code == 201
    assert sender.call_count == 2
    assert {
        call.kwargs["subscription_info"]["endpoint"]
        for call in sender.call_args_list
    } == {
        "https://push.example.test/bulk-one",
        "https://push.example.test/bulk-two",
    }
    notices = [json.loads(call.kwargs["data"]) for call in sender.call_args_list]
    assert {notice["title"] for notice in notices} == {"New task assigned"}
    assert {notice["url"] for notice in notices} == {f"/teams/{team_id}"}


def test_worker_task_proposal_and_leader_decision_send_notifications(
    client: TestClient,
    monkeypatch,
) -> None:
    set_push_settings()
    sender = Mock()
    monkeypatch.setattr(push_notifications, "webpush", sender)
    leader_headers = register_and_login(client, "proposal-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Proposal notifications"},
    ).json()
    team_id = team["id"]
    client.post(
        f"/api/v1/teams/{team_id}/invites",
        headers=leader_headers,
        json={"email": "proposal-worker@example.com"},
    )
    worker_headers = register_and_login(client, "proposal-worker@example.com")
    subscribe(client, leader_headers, "https://push.example.test/proposal-leader")
    subscribe(client, worker_headers, "https://push.example.test/proposal-worker")
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    proposal = {
        "title": "Prepare onboarding guide",
        "description": "Draft a guide for new teammates.",
        "start_at": start.isoformat(),
        "deadline_at": (start + timedelta(hours=2)).isoformat(),
    }

    created = client.post(
        f"/api/v1/teams/{team_id}/task-requests",
        headers=worker_headers,
        json=proposal,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert sender.call_count == 1
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/proposal-leader"
    )
    assert json.loads(sender.call_args.kwargs["data"])["title"] == (
        "Task proposal needs review"
    )

    rejected = client.post(
        f"/api/v1/tasks/{task_id}/approval",
        headers=leader_headers,
        json={"approved": False, "comment": "Please add a due-date section."},
    )
    assert rejected.status_code == 200
    assert sender.call_count == 2
    rejection = json.loads(sender.call_args.kwargs["data"])
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/proposal-worker"
    )
    assert rejection["title"] == "Task proposal declined"
    assert "Please add a due-date section" in rejection["body"]

    resubmitted = client.patch(
        f"/api/v1/tasks/{task_id}/request",
        headers=worker_headers,
        json=proposal,
    )
    assert resubmitted.status_code == 200
    assert sender.call_count == 3
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/proposal-leader"
    )

    approved = client.post(
        f"/api/v1/tasks/{task_id}/approval",
        headers=leader_headers,
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert sender.call_count == 4
    approval = json.loads(sender.call_args.kwargs["data"])
    assert sender.call_args.kwargs["subscription_info"]["endpoint"].endswith(
        "/proposal-worker"
    )
    assert approval["title"] == "Task proposal approved"


def test_push_failure_does_not_undo_task_submission(
    client: TestClient,
    monkeypatch,
) -> None:
    set_push_settings()
    monkeypatch.setattr(
        push_notifications,
        "webpush",
        Mock(side_effect=RuntimeError("push service unavailable")),
    )
    leader_headers = register_and_login(client, "failure-leader@example.com")
    team = client.post(
        "/api/v1/teams",
        headers=leader_headers,
        json={"name": "Failure isolation"},
    ).json()
    client.post(
        f"/api/v1/teams/{team['id']}/invites",
        headers=leader_headers,
        json={"email": "failure-worker@example.com"},
    )
    worker_headers = register_and_login(client, "failure-worker@example.com")
    worker_id = client.get("/api/v1/auth/me", headers=worker_headers).json()["id"]
    subscribe(client, leader_headers, "https://push.example.test/failure-leader")
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    created = client.post(
        f"/api/v1/teams/{team['id']}/tasks",
        headers=leader_headers,
        json={
            "title": "Save before notifying",
            "description": "The submit must survive notification failure.",
            "assignee_id": worker_id,
            "start_at": start.isoformat(),
            "deadline_at": (start + timedelta(hours=1)).isoformat(),
        },
    )

    submitted = client.post(
        f"/api/v1/tasks/{created.json()['id']}/submit", headers=worker_headers
    )

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"


def test_expired_push_subscription_is_removed(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    set_push_settings()
    headers = register_and_login(client, "expired-push@example.com")
    user_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    endpoint = "https://push.example.test/expired"
    subscribe(client, headers, endpoint)
    monkeypatch.setattr(
        push_notifications,
        "webpush",
        Mock(
            side_effect=WebPushException(
                "subscription expired",
                response=SimpleNamespace(status_code=410),
            )
        ),
    )

    push_notifications.send_to_user(
        db_session,
        user_id,
        {"title": "Test", "body": "Test"},
        PUSH_SETTINGS,
    )

    remaining = db_session.scalar(
        select(WebPushSubscription).where(
            WebPushSubscription.endpoint == endpoint
        )
    )
    assert remaining is None