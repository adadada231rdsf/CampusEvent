"""活动管理与表单校验（P2-F01 / P2-F02 / B.2-7）。"""
from __future__ import annotations

import pytest

from app.domain import repository as repo
from app.domain.activity_service import ActivityService, parse_activity_form
from app.domain.constants import SealError
from app.domain.entities import Activity
from app.domain.notification import NotificationService
from app.domain.registration_service import RegistrationService

from conftest import FUTURE


def form(**over):
    base = {
        "title": "测试讲座", "category": "讲座", "start_at": "2026-12-01T14:00",
        "location": "报告厅", "capacity": "20", "policy_type": "DIRECT",
    }
    base.update(over)
    return base


def test_parse_form_ok():
    a = parse_activity_form(form())
    assert a.title == "测试讲座"
    assert a.start_at == "2026-12-01 14:00"
    assert a.capacity == 20
    assert a.policy_type == "DIRECT"


@pytest.mark.parametrize(
    "over, code",
    [
        ({"title": "  "}, "TITLE_REQUIRED"),
        ({"title": "长" * 61}, "TITLE_TOO_LONG"),
        ({"start_at": "2026/12/01 14:00"}, "BAD_START"),
        ({"location": ""}, "LOCATION_REQUIRED"),
        ({"capacity": "0"}, "BAD_CAPACITY"),
        ({"capacity": "-3"}, "BAD_CAPACITY"),
        ({"capacity": "abc"}, "BAD_CAPACITY"),
        ({"policy_type": "LOTTERY"}, "BAD_POLICY"),
    ],
)
def test_parse_form_invalid(over, code):
    with pytest.raises(SealError) as exc:
        parse_activity_form(form(**over))
    assert exc.value.code == code


def test_category_defaults_to_other():
    assert parse_activity_form(form(category="")).category == "其他"


def test_create_list_filter(conn):
    svc = ActivityService(conn)
    svc.create(parse_activity_form(form(title="人工智能讲座")))
    svc.create(parse_activity_form(form(title="程序设计竞赛", policy_type="APPROVAL")))
    assert len(repo.list_activities(conn)) == 2
    assert [a["title"] for a in repo.list_activities(conn, "讲座")] == ["人工智能讲座"]
    assert repo.list_activities(conn, "不存在") == []


def test_update_activity(conn, make_activity):
    aid = make_activity(capacity=2)
    act = parse_activity_form(form(title="改名后", capacity="8", activity_id=str(aid)))
    ActivityService(conn).update(act)
    row = repo.get_activity(conn, aid)
    assert row["title"] == "改名后" and row["capacity"] == 8


def test_update_missing_activity_raises(conn):
    svc = ActivityService(conn)
    act = Activity(9999, "x", "讲座", FUTURE, "地点", 3, "DIRECT")
    with pytest.raises(SealError) as exc:
        svc.update(act)
    assert exc.value.code == "ACTIVITY_NOT_FOUND"


def test_soft_delete_hides_activity_but_keeps_history(conn, make_activity):
    aid = make_activity(capacity=3, policy="DIRECT")
    svc = RegistrationService(conn, NotificationService())
    rid = svc.register(aid, "2024001")["registration_id"]

    info = ActivityService(conn).delete(aid)
    assert info["title"] == "测试活动"
    assert info["affected_approved"] == 1

    assert repo.get_activity(conn, aid) is None
    assert repo.list_activities(conn) == []
    # 历史报名保留
    assert repo.get_registration(conn, rid)["status"] == "已通过"
    # 学生收到活动被取消的通知
    msgs = [m["content"] for m in repo.messages_of(conn, "2024001")]
    assert any("已被管理员取消" in m for m in msgs)


def test_approve_on_deleted_activity_fails(conn, make_activity):
    aid = make_activity(capacity=3, policy="APPROVAL")
    svc = RegistrationService(conn, NotificationService())
    rid = svc.register(aid, "2024001")["registration_id"]
    ActivityService(conn).delete(aid)
    with pytest.raises(SealError) as exc:
        svc.approve(rid)
    assert exc.value.code == "ACTIVITY_NOT_FOUND"


def test_delete_twice_fails(conn, make_activity):
    aid = make_activity()
    svc = ActivityService(conn)
    svc.delete(aid)
    with pytest.raises(SealError) as exc:
        svc.delete(aid)
    assert exc.value.code == "ACTIVITY_NOT_FOUND"
