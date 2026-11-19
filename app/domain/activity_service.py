"""活动管理（管理员用）：校验 + 增改删。

删除策略——我们选的是"软删除（deleted_at）"：
1. 报名记录是学生参加活动的凭证，硬删会连带毁掉历史，和 B.2 第 4 条
   "已取消/已拒绝保留历史"的精神不一致；
2. 软删除后学生侧列表自动看不到该活动，管理员也能反悔；
3. 成本只有一列 deleted_at 和查询里的一个 AND，代价最小。
"""
from __future__ import annotations

from datetime import datetime

from . import repository as repo
from .constants import ALL_POLICIES, SealError
from .entities import Activity

FMT = "%Y-%m-%dT%H:%M"


def parse_activity_form(form) -> Activity:
    title = (form.get("title") or "").strip()
    category = (form.get("category") or "").strip() or "其他"
    start_raw = (form.get("start_at") or "").strip()
    location = (form.get("location") or "").strip()
    cap_raw = (form.get("capacity") or "").strip()
    policy_type = (form.get("policy_type") or "").strip()
    activity_id = form.get("activity_id")

    if not title:
        raise SealError("活动名称不能为空", "TITLE_REQUIRED")
    if len(title) > 60:
        raise SealError("活动名称不能超过 60 个字", "TITLE_TOO_LONG")
    try:
        start_at = datetime.strptime(start_raw, FMT).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        raise SealError("活动时间格式应为 2026-12-01T14:00", "BAD_START")
    if not location:
        raise SealError("活动地点不能为空", "LOCATION_REQUIRED")
    try:
        capacity = int(cap_raw)
    except (TypeError, ValueError):
        raise SealError("人数上限必须是正整数", "BAD_CAPACITY")
    if capacity <= 0:
        raise SealError("人数上限必须大于 0", "BAD_CAPACITY")
    if policy_type not in ALL_POLICIES:
        raise SealError("报名方式只能是 直接报名 / 需审核", "BAD_POLICY")

    return Activity(
        activity_id=int(activity_id) if activity_id else None,
        title=title, category=category, start_at=start_at,
        location=location, capacity=capacity, policy_type=policy_type,
    )


class ActivityService:
    def __init__(self, conn):
        self.conn = conn

    def create(self, activity: Activity) -> int:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            aid = repo.insert_activity(self.conn, activity)
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")
        return aid

    def update(self, activity: Activity) -> None:
        if repo.get_activity(self.conn, activity.activity_id) is None:
            raise SealError("活动不存在或已被删除", "ACTIVITY_NOT_FOUND")
        repo.update_activity(self.conn, activity)
        self.conn.commit()

    def delete(self, activity_id: int) -> dict:
        """软删除。返回提示信息用的统计。"""
        act = repo.get_activity(self.conn, activity_id)
        if act is None:
            raise SealError("活动不存在或已被删除", "ACTIVITY_NOT_FOUND")
        counts = repo.count_by_status(self.conn, activity_id)
        repo.soft_delete_activity(self.conn, activity_id)
        self.conn.commit()
        now_str = repo.now()
        # 给仍处于待审核/已通过状态的报名人各发一条通知
        rows = self.conn.execute(
            """SELECT student_id, status FROM registration
                WHERE activity_id = ? AND status IN ('待审核', '已通过')""",
            (activity_id,),
        ).fetchall()
        for r in rows:
            repo.insert_message(
                self.conn, r["student_id"], activity_id,
                f"活动「{act['title']}」已被管理员取消，你的报名自动失效", kind="ACTIVITY_DELETED",
            )
        self.conn.commit()
        return {
            "title": act["title"],
            "affected_pending": counts["待审核"],
            "affected_approved": counts["已通过"],
            "soft_deleted_at": now_str,
        }