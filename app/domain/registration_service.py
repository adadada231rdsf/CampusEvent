"""报名业务服务：规则都在这里，是本次实验的"核心业务代码"。

事务边界（B.2 第 6 条要求说明）：
- 报名 / 审批 / 取消各自是一个事务：先 BEGIN IMMEDIATE 抢占写锁，
  再做"名额检查 → 写报名表 → 写通知"，最后 COMMIT。
- 名额检查与插入在同一事务内，两个学生同时抢最后一个名额时，
  后到的一方在拿到写锁后重新检查，会看到已满而被拒绝，不会超卖。
- 通知在事务内写库（站内信和数据同生共死），但通道异常被 NotificationService
  吞掉并留痕，不会让"合法报名"因为通知失败而消失。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from . import repository as repo
from .constants import (
    ST_APPROVED,
    ST_CANCELLED,
    ST_PENDING,
    ST_REJECTED,
    SealError,
)
from .entities import Message
from .notification import NotificationService
from .policy import get_policy


class RegistrationService:
    def __init__(self, conn: sqlite3.Connection, notifier: NotificationService):
        self.conn = conn
        self.notifier = notifier

    # ---------- 事务 ----------
    @contextmanager
    def _tx(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    # ---------- 通用检查 ----------
    def _load_activity(self, activity_id: int) -> sqlite3.Row:
        act = repo.get_activity(self.conn, activity_id)
        if act is None:
            raise SealError("活动不存在或已被删除", "ACTIVITY_NOT_FOUND")
        return act

    def seats_left(self, activity_id: int) -> int:
        act = self._load_activity(activity_id)
        return max(0, int(act["capacity"]) - repo.count_approved(self.conn, activity_id))

    # ---------- 报名 ----------
    def register(self, activity_id: int, student_id: str) -> dict:
        with self._tx():
            act = self._load_activity(activity_id)
            st = repo.get_student(self.conn, student_id)
            if st is None:
                raise SealError("学生不存在", "STUDENT_NOT_FOUND")

            # 规则：同一学生同一活动不得有两条有效报名（已取消/已拒绝保留历史，可再申请）
            dup = repo.active_registration(self.conn, activity_id, student_id)
            if dup is not None:
                raise SealError(
                    f"你已经报过这个活动了（当前状态：{dup['status']}）", "DUPLICATE_ACTIVE"
                )

            # 规则 B.2-5：活动开始后不再接受新增报名（取消不受限制）
            if act["start_at"] <= repo.now():
                raise SealError("活动已经开始，不能报名", "ACTIVITY_STARTED")

            left = int(act["capacity"]) - repo.count_approved(self.conn, activity_id)
            policy = get_policy(act["policy_type"])
            policy.check(seats_left=left, capacity=int(act["capacity"]))
            status = policy.decide(seats_left=left)
            reg_id = repo.insert_registration(self.conn, activity_id, student_id, status)
            left_after = max(0, left - (1 if status == ST_APPROVED else 0))

        self._notify(activity_id, act["title"], [
            (student_id, self._register_text(act["title"], status, left_after),
             self._register_kind(status)),
        ])
        return {"registration_id": reg_id, "status": status, "seats_left": left_after}

    @staticmethod
    def _register_text(title: str, status: str, left: int) -> str:
        if status == ST_APPROVED:
            return f"「{title}」报名成功，当前剩余名额 {left}"
        return f"「{title}」申请已提交，等待管理员审核"

    @staticmethod
    def _register_kind(status: str) -> str:
        return "REGISTERED" if status == ST_APPROVED else "PENDING"

    # ---------- 取消 ----------
    def cancel(self, registration_id: int, student_id: str) -> dict:
        with self._tx():
            reg = repo.get_registration(self.conn, registration_id)
            if reg is None:
                raise SealError("报名记录不存在", "REGISTRATION_NOT_FOUND")
            if reg["student_id"] != student_id:
                raise SealError("只能取消自己的报名", "NOT_OWNER")
            if reg["status"] not in (ST_PENDING, ST_APPROVED):
                raise SealError(f"当前状态为「{reg['status']}」，不能取消", "INVALID_STATUS")
            act = self._load_activity(reg["activity_id"])
            repo.update_status(self.conn, registration_id, ST_CANCELLED)
            left = max(0, int(act["capacity"]) - repo.count_approved(self.conn, act["activity_id"]))

        self._notify(act["activity_id"], act["title"], [
            (student_id, f"你已取消「{act['title']}」的报名，当前剩余名额 {left}（已取消）", "CANCELLED"),
        ])
        return {"status": ST_CANCELLED, "seats_left": left}

    # ---------- 审批 ----------
    def approve(self, registration_id: int) -> dict:
        with self._tx():
            reg = repo.get_registration(self.conn, registration_id)
            if reg is None:
                raise SealError("报名记录不存在", "REGISTRATION_NOT_FOUND")
            if reg["status"] != ST_PENDING:
                raise SealError(f"当前状态为「{reg['status']}」，不是待审核，无法审批", "INVALID_STATUS")
            act = self._load_activity(reg["activity_id"])
            # 批准时再次检查名额（待审核不占名额，可能已被别人占满）
            left = int(act["capacity"]) - repo.count_approved(self.conn, act["activity_id"])
            if left <= 0:
                raise SealError("名额已满，无法批准；请先扩大名额或拒绝该申请", "CAPACITY_FULL")
            repo.update_status(self.conn, registration_id, ST_APPROVED)
            left_after = left - 1

        self._notify(act["activity_id"], act["title"], [
            (reg["student_id"], f"「{act['title']}」审核通过，当前剩余名额 {left_after}", "APPROVED"),
            # 审批结果本身也留审计轨迹：审批冲突时可以追溯是谁、何时批的
            ("__admin__", f"批准报名 #{registration_id}（活动「{act['title']}」）", "AUDIT"),
        ])
        return {"status": ST_APPROVED, "seats_left": left_after}

    def reject(self, registration_id: int, reason: str = "名额已满或不符合报名条件") -> dict:
        with self._tx():
            reg = repo.get_registration(self.conn, registration_id)
            if reg is None:
                raise SealError("报名记录不存在", "REGISTRATION_NOT_FOUND")
            if reg["status"] != ST_PENDING:
                raise SealError(f"当前状态为「{reg['status']}」，不是待审核，无法审批", "INVALID_STATUS")
            act = self._load_activity(reg["activity_id"])
            repo.update_status(self.conn, registration_id, ST_REJECTED, note=reason)
            left = max(0, int(act["capacity"]) - repo.count_approved(self.conn, act["activity_id"]))

        self._notify(act["activity_id"], act["title"], [
            (reg["student_id"], f"「{act['title']}」申请未通过：{reason}（已拒绝）", "REJECTED"),
            ("__admin__", f"拒绝报名 #{registration_id}（活动「{act['title']}」）：{reason}", "AUDIT"),
        ])
        return {"status": ST_REJECTED, "seats_left": left}

    # ---------- 统计 ----------
    def stats(self, activity_id: int) -> dict:
        act = self._load_activity(activity_id)
        counts = repo.count_by_status(self.conn, activity_id)
        return {
            "capacity": int(act["capacity"]),
            "approved": counts[ST_APPROVED],
            "pending": counts[ST_PENDING],
            "rejected": counts[ST_REJECTED],
            "cancelled": counts[ST_CANCELLED],
            "seats_left": max(0, int(act["capacity"]) - counts[ST_APPROVED]),
        }

    # ---------- 通知 ----------
    def _notify(self, activity_id: int, title: str, items) -> None:
        """items: [(student_id, content, kind), ...]"""
        ts = repo.now()
        for i, (sid, content, kind) in enumerate(items):
            msg = Message(None, sid, activity_id, content, ts, False, kind, seq=i)
            self.notifier.publish(self.conn, msg)
        self.conn.commit()