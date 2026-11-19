"""业务规则测试：对应指导书附录 B.2 的 1–7 条与验收用例 C1–C10。"""
from __future__ import annotations

import sqlite3

import pytest

from app.domain import repository as repo
from app.domain.constants import SealError
from app.domain.notification import INotificationChannel, NotificationService
from app.domain.registration_service import RegistrationService

from conftest import PAST, FUTURE, messages_text


# ---------------- 报名（B.2-1 / B.2-2 / C2 / C5） ----------------
def test_direct_policy_auto_approves(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="DIRECT")
    r = svc.register(aid, "2024001")
    assert r["status"] == "已通过"
    assert r["seats_left"] == 1
    assert "报名成功" in messages_text(conn, "2024001")
    assert svc.stats(aid)["approved"] == 1


def test_approval_policy_goes_pending(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="APPROVAL")
    r = svc.register(aid, "2024001")
    assert r["status"] == "待审核"
    assert "等待管理员审核" in messages_text(conn, "2024001")
    assert svc.stats(aid)["pending"] == 1
    assert svc.stats(aid)["approved"] == 0


def test_duplicate_active_registration_rejected(svc, make_activity):
    aid = make_activity(capacity=5, policy="DIRECT")
    svc.register(aid, "2024001")
    with pytest.raises(SealError) as exc:
        svc.register(aid, "2024001")
    assert exc.value.code == "DUPLICATE_ACTIVE"


def test_pending_duplicate_also_rejected(svc, make_activity):
    aid = make_activity(capacity=5, policy="APPROVAL")
    svc.register(aid, "2024001")
    with pytest.raises(SealError) as exc:
        svc.register(aid, "2024001")
    assert exc.value.code == "DUPLICATE_ACTIVE"


def test_capacity_full_blocks_direct_registration(svc, make_activity, conn):
    aid = make_activity(capacity=1, policy="DIRECT")
    svc.register(aid, "2024001")
    with pytest.raises(SealError) as exc:
        svc.register(aid, "2024002")
    assert exc.value.code == "CAPACITY_FULL"
    assert svc.stats(aid)["approved"] == 1  # 不超卖


def test_pending_does_not_consume_seat(svc, make_activity):
    aid = make_activity(capacity=1, policy="APPROVAL")
    svc.register(aid, "2024001")
    svc.register(aid, "2024002")
    st = svc.stats(aid)
    assert st["pending"] == 2
    assert st["seats_left"] == 1  # 待审核不占名额


# ---------------- 审批（B.2-2 / B.2-3 / C6 / C7 / C8） ----------------
def test_approve_pending_and_notify(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="APPROVAL")
    rid = svc.register(aid, "2024001")["registration_id"]
    out = svc.approve(rid)
    assert out["status"] == "已通过"
    assert out["seats_left"] == 1
    assert "审核通过" in messages_text(conn, "2024001")


def test_reject_pending_and_notify(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="APPROVAL")
    rid = svc.register(aid, "2024001")["registration_id"]
    svc.reject(rid, "材料不全")
    row = repo.get_registration(conn, rid)
    assert row["status"] == "已拒绝"
    assert row["note"] == "材料不全"
    assert "材料不全" in messages_text(conn, "2024001")


def test_approve_when_capacity_full_fails(svc, make_activity):
    aid = make_activity(capacity=1, policy="APPROVAL")
    first = svc.register(aid, "2024001")["registration_id"]
    second = svc.register(aid, "2024002")["registration_id"]
    svc.approve(first)
    with pytest.raises(SealError) as exc:
        svc.approve(second)
    assert exc.value.code == "CAPACITY_FULL"
    assert svc.stats(aid)["approved"] == 1
    assert svc.stats(aid)["seats_left"] == 0


def test_approve_non_pending_rejected(svc, make_activity):
    aid = make_activity(capacity=2, policy="APPROVAL")
    rid = svc.register(aid, "2024001")["registration_id"]
    svc.reject(rid)
    with pytest.raises(SealError) as exc:
        svc.approve(rid)
    assert exc.value.code == "INVALID_STATUS"


# ---------------- 取消（B.2-4 / B.2-5 / C9） ----------------
def test_cancel_own_registration_and_stats(svc, make_activity):
    aid = make_activity(capacity=2, policy="DIRECT")
    rid = svc.register(aid, "2024001")["registration_id"]
    out = svc.cancel(rid, "2024001")
    assert out["status"] == "已取消"
    assert out["seats_left"] == 2
    st = svc.stats(aid)
    assert st["approved"] == 0 and st["cancelled"] == 1


def test_cancel_someone_elses_registration_forbidden(svc, make_activity):
    aid = make_activity(capacity=2, policy="DIRECT")
    rid = svc.register(aid, "2024001")["registration_id"]
    with pytest.raises(SealError) as exc:
        svc.cancel(rid, "2024002")
    assert exc.value.code == "NOT_OWNER"


def test_cancel_then_reapply_allowed(svc, make_activity):
    aid = make_activity(capacity=2, policy="DIRECT")
    rid = svc.register(aid, "2024001")["registration_id"]
    svc.cancel(rid, "2024001")
    again = svc.register(aid, "2024001")
    assert again["registration_id"] != rid
    assert again["status"] == "已通过"
    assert svc.stats(aid)["approved"] == 1


def test_rejected_record_kept_and_student_can_reapply(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="APPROVAL")
    rid = svc.register(aid, "2024001")["registration_id"]
    svc.reject(rid, "不符合")
    assert repo.get_registration(conn, rid)["status"] == "已拒绝"
    assert svc.register(aid, "2024001")["status"] == "待审核"


def test_registration_after_activity_start_blocked(svc, make_activity):
    aid = make_activity(capacity=2, policy="DIRECT", start_at=PAST)
    with pytest.raises(SealError) as exc:
        svc.register(aid, "2024001")
    assert exc.value.code == "ACTIVITY_STARTED"


def test_cancel_still_allowed_after_start(svc, make_activity, conn):
    aid = make_activity(capacity=2, policy="DIRECT", start_at=FUTURE)
    rid = svc.register(aid, "2024001")["registration_id"]
    conn.execute("UPDATE activity SET start_at = ? WHERE activity_id = ?", (PAST, aid))
    conn.commit()
    assert svc.cancel(rid, "2024001")["status"] == "已取消"


# ---------------- 非法输入 ----------------
def test_register_unknown_activity(svc):
    with pytest.raises(SealError) as exc:
        svc.register(9999, "2024001")
    assert exc.value.code == "ACTIVITY_NOT_FOUND"


def test_register_unknown_student(svc, make_activity):
    aid = make_activity()
    with pytest.raises(SealError) as exc:
        svc.register(aid, "9999999")
    assert exc.value.code == "STUDENT_NOT_FOUND"


def test_database_index_blocks_two_active_rows(conn, make_activity):
    """部分唯一索引是最后一道防线：即使绕过 Service 也不能有两条有效报名。"""
    aid = make_activity(capacity=5)
    repo.insert_registration(conn, aid, "2024001", "已通过")
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_registration(conn, aid, "2024001", "待审核")


# ---------------- 事务与通知（B.2-6） ----------------
class BoomChannel(INotificationChannel):
    name = "boom"

    def deliver(self, conn, message):
        raise RuntimeError("通道故障")


def test_notification_failure_does_not_lose_registration(conn, make_activity, db_path, notifier):
    aid = make_activity(capacity=3, policy="DIRECT")
    notifier.register(BoomChannel())
    svc = RegistrationService(conn, notifier)
    r = svc.register(aid, "2024001")

    assert r["status"] == "已通过"
    assert notifier.failures and notifier.failures[0]["channel"] == "boom"
    # 报名已经提交，且失败留痕写在审计表里
    other = repo.connect(db_path)
    try:
        assert repo.get_registration(other, r["registration_id"])["status"] == "已通过"
        audit = other.execute(
            "SELECT content FROM message WHERE kind = 'NOTIFY_FAILED'"
        ).fetchall()
        assert audit and "通知失败[boom]" in audit[0]["content"]
        # 站内信通道仍然成功，学生能看到报名结果
        assert any("报名成功" in m["content"] for m in repo.messages_of(other, "2024001"))
    finally:
        other.close()


def test_duplicate_notification_is_idempotent(conn, make_activity):
    """同一条消息重复发布只落一条（通知重试不会刷屏）。"""
    aid = make_activity(capacity=3, policy="DIRECT")
    svc = RegistrationService(conn, NotificationService())
    svc.register(aid, "2024001")
    rows = [m for m in repo.messages_of(conn, "2024001") if m["kind"] == "REGISTERED"]
    assert len(rows) == 1


# ---------------- 统计（P2-F08） ----------------
def test_stats_after_mixed_statuses(svc, make_activity, conn):
    aid = make_activity(capacity=5, policy="APPROVAL")
    a = svc.register(aid, "2024001")["registration_id"]
    b = svc.register(aid, "2024002")["registration_id"]
    svc.register(aid, "2024003")
    svc.approve(a)
    svc.reject(b)
    st = svc.stats(aid)
    assert st == {
        "capacity": 5, "approved": 1, "pending": 1,
        "rejected": 1, "cancelled": 0, "seats_left": 4,
    }
