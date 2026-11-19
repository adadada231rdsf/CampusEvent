"""测试夹具：每个用例一个全新的 SQLite 文件，避免共享状态。"""
from __future__ import annotations

import os
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from app.domain import repository as repo  # noqa: E402
from app.domain.entities import Activity  # noqa: E402
from app.domain.notification import NotificationService  # noqa: E402
from app.domain.registration_service import RegistrationService  # noqa: E402

TMP_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmpdb")

FUTURE = "2099-01-01 10:00"
PAST = "2000-01-01 10:00"


@pytest.fixture()
def db_path():
    os.makedirs(TMP_DB_DIR, exist_ok=True)
    path = os.path.join(TMP_DB_DIR, f"t_{uuid.uuid4().hex}.sqlite")
    yield path
    for suffix in ("", "-journal", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


@pytest.fixture()
def app(db_path):
    application = create_app({"DATABASE": db_path, "TESTING": True, "SECRET_KEY": "test-key"})
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def conn(db_path):
    connection = repo.connect(db_path)
    repo.ensure_students(connection)
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture()
def notifier():
    return NotificationService()


@pytest.fixture()
def svc(conn, notifier):
    return RegistrationService(conn, notifier)


@pytest.fixture()
def make_activity(conn):
    def _make(
        title: str = "测试活动",
        capacity: int = 2,
        policy: str = "DIRECT",
        start_at: str = FUTURE,
        category: str = "讲座",
        location: str = "报告厅",
    ) -> int:
        aid = repo.insert_activity(
            conn,
            Activity(
                activity_id=None,
                title=title,
                category=category,
                start_at=start_at,
                location=location,
                capacity=capacity,
                policy_type=policy,
            ),
        )
        conn.commit()
        return aid

    return _make


# ---------------- 便捷登录 ----------------


def login_student(client, student_id: str = "2024001"):
    return client.post("/login", data={"student_id": student_id}, follow_redirects=True)


def login_admin(client):
    return client.post("/login", data={"student_id": "admin"}, follow_redirects=True)


def messages_text(conn, student_id: str) -> str:
    rows = repo.messages_of(conn, student_id)
    return "\n".join(r["content"] for r in rows)
