import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ---------- Users ----------
def test_create_user(client):
    res = client.post("/users", json={"name": "Ada", "email": "ada@example.com", "role": "writer"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Ada"
    assert data["id"] is not None


def test_create_user_duplicate_email_fails(client):
    client.post("/users", json={"name": "Ada", "email": "ada@example.com"})
    res = client.post("/users", json={"name": "Ada2", "email": "ada@example.com"})
    assert res.status_code == 400


def test_list_users(client):
    client.post("/users", json={"name": "Ada", "email": "ada@example.com"})
    client.post("/users", json={"name": "Grace", "email": "grace@example.com"})
    res = client.get("/users")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_user_404(client):
    res = client.get("/users/999")
    assert res.status_code == 404


# ---------- Documents ----------
def _make_user(client, name="Ada", email="ada@example.com"):
    return client.post("/users", json={"name": name, "email": email}).json()


def test_create_document(client):
    user = _make_user(client)
    res = client.post(
        "/documents", json={"title": "Chapter One", "content": "It was a dark night.", "owner_id": user["id"]}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Chapter One"
    assert data["version"] == 1
    assert data["status"] == "draft"


def test_document_creation_snapshots_version_one(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "Chapter One", "content": "Draft text", "owner_id": user["id"]}).json()
    versions = client.get(f"/documents/{doc['id']}/versions").json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["content"] == "Draft text"


def test_list_documents(client):
    user = _make_user(client)
    client.post("/documents", json={"title": "A", "owner_id": user["id"]})
    client.post("/documents", json={"title": "B", "owner_id": user["id"]})
    res = client.get("/documents")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_documents_filter_by_status(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    client.put(f"/documents/{doc['id']}", json={"status": "published", "editor_id": user["id"]})
    res = client.get("/documents?status=published")
    assert len(res.json()) == 1
    res_draft = client.get("/documents?status=draft")
    assert len(res_draft.json()) == 0


def test_get_document_404(client):
    res = client.get("/documents/999")
    assert res.status_code == 404


def test_update_document_content_bumps_version(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "content": "v1", "owner_id": user["id"]}).json()
    res = client.put(f"/documents/{doc['id']}", json={"content": "v2 text", "editor_id": user["id"]})
    assert res.status_code == 200
    updated = res.json()
    assert updated["version"] == 2
    assert updated["content"] == "v2 text"

    versions = client.get(f"/documents/{doc['id']}/versions").json()
    assert len(versions) == 2


def test_update_document_status_only_does_not_bump_version(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "content": "same", "owner_id": user["id"]}).json()
    res = client.put(f"/documents/{doc['id']}", json={"status": "in_review", "editor_id": user["id"]})
    assert res.json()["version"] == 1
    assert res.json()["status"] == "in_review"


def test_delete_document(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    res = client.delete(f"/documents/{doc['id']}")
    assert res.status_code == 204
    assert client.get(f"/documents/{doc['id']}").status_code == 404


def test_restore_version(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "content": "original", "owner_id": user["id"]}).json()
    client.put(f"/documents/{doc['id']}", json={"content": "changed", "editor_id": user["id"]})
    res = client.post(f"/documents/{doc['id']}/versions/1/restore")
    assert res.status_code == 200
    assert res.json()["content"] == "original"
    assert res.json()["version"] == 3  # v1 original, v2 changed, v3 restored snapshot


def test_restore_missing_version_404(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    res = client.post(f"/documents/{doc['id']}/versions/99/restore")
    assert res.status_code == 404


def test_upload_document_creates_document_with_file_content(client):
    user = _make_user(client)
    files = {"file": ("notes.txt", b"Some uploaded notes content", "text/plain")}
    res = client.post("/documents/upload", data={"owner_id": user["id"]}, files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "notes.txt"
    assert data["content"] == "Some uploaded notes content"
    assert data["version"] == 1

    versions = client.get(f"/documents/{data['id']}/versions").json()
    assert len(versions) == 1


def test_upload_document_rejects_non_utf8_binary(client):
    files = {"file": ("image.png", b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/png")}
    res = client.post("/documents/upload", files=files)
    assert res.status_code == 400


# ---------- Comments ----------
def test_add_and_list_comments(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    res = client.post(f"/documents/{doc['id']}/comments", json={"author_id": user["id"], "text": "Nice opening line"})
    assert res.status_code == 201
    comments = client.get(f"/documents/{doc['id']}/comments").json()
    assert len(comments) == 1
    assert comments[0]["resolved"] is False


def test_resolve_comment(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    comment = client.post(f"/documents/{doc['id']}/comments", json={"author_id": user["id"], "text": "fix typo"}).json()
    res = client.patch(f"/documents/comments/{comment['id']}/resolve")
    assert res.status_code == 200
    assert res.json()["resolved"] is True


def test_comment_on_missing_document_404(client):
    res = client.post("/documents/999/comments", json={"text": "hi"})
    assert res.status_code == 404


# ---------- Tasks / Coordination ----------
def test_create_task(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    res = client.post(
        "/tasks",
        json={"document_id": doc["id"], "assignee_id": user["id"], "title": "Review intro", "description": "Check tone"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "todo"


def test_list_tasks_filter_by_status(client):
    user = _make_user(client)
    t1 = client.post("/tasks", json={"title": "T1"}).json()
    client.post("/tasks", json={"title": "T2"})
    client.patch(f"/tasks/{t1['id']}", json={"status": "done"})

    done_tasks = client.get("/tasks?status=done").json()
    todo_tasks = client.get("/tasks?status=todo").json()
    assert len(done_tasks) == 1
    assert len(todo_tasks) == 1


def test_update_task(client):
    user = _make_user(client)
    task = client.post("/tasks", json={"title": "T1", "assignee_id": user["id"]}).json()
    res = client.patch(f"/tasks/{task['id']}", json={"status": "in_progress"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_update_task_404(client):
    res = client.patch("/tasks/999", json={"status": "done"})
    assert res.status_code == 404


def test_delete_task(client):
    task = client.post("/tasks", json={"title": "T1"}).json()
    res = client.delete(f"/tasks/{task['id']}")
    assert res.status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


# ---------- Dashboard ----------
def test_dashboard_summary_counts(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "owner_id": user["id"]}).json()
    client.put(f"/documents/{doc['id']}", json={"status": "published", "editor_id": user["id"]})
    client.post("/tasks", json={"title": "T1"})
    client.post("/tasks", json={"title": "T2"})

    res = client.get("/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_documents"] == 1
    assert data["documents_by_status"]["published"] == 1
    assert data["total_tasks"] == 2
    assert data["tasks_by_status"]["todo"] == 2
    assert data["total_users"] == 1


def test_dashboard_activity_feed_records_events(client):
    user = _make_user(client)
    doc = client.post("/documents", json={"title": "A", "content": "x", "owner_id": user["id"]}).json()
    client.put(f"/documents/{doc['id']}", json={"content": "y", "editor_id": user["id"]})
    client.post(f"/documents/{doc['id']}/comments", json={"author_id": user["id"], "text": "note"})

    res = client.get("/dashboard/activity")
    assert res.status_code == 200
    actions = [a["action"] for a in res.json()]
    assert "document_created" in actions
    assert "document_edited" in actions
    assert "comment_added" in actions


def test_dashboard_overdue_tasks(client):
    res = client.post("/tasks", json={"title": "Late task", "due_date": "2020-01-01T00:00:00"})
    assert res.status_code == 201
    summary = client.get("/dashboard/summary").json()
    assert summary["overdue_tasks"] == 1
