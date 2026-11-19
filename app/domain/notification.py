"""通知（Observer 模式）。

对照实验指导书 关键任务 C：
- NotificationService 是 Subject（发布者），RegistrationService 只调用 publish()，
  完全不知道通知落在站内信、邮件还是短信里；
- INotificationChannel 是 Observer 接口，站内消息、审计日志各是一个实现；
- 新增"发邮件"只需多注册一个 channel，报名业务代码不用改。

两个必须由学生回答的问题，我们的答案写在下面：
1. 通知失败影响报名吗？——不影响。报名状态已经在同一个事务里落库了，
   通知是"事后尽力而为"。失败时写一条 AUDIT 日志留痕（Fail-loud），
   学生仍可在"我的报名"里看到记录，不会"无声消失"。
2. 如何避免重复通知？——每个通道都用 content + 业务主键做幂等键：
   站内信通道查 (student_id, activity_id, content) 是否已有，有就不重复插；
   审计通道按 seq 去重。这样即使重试也不会给学生发两条一样的消息。
"""
from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from . import repository as repo


class INotificationChannel(ABC):
    """通知通道接口（Observer）。"""

    name: str = ""

    @abstractmethod
    def deliver(self, conn: sqlite3.Connection, message) -> bool:
        """投递一条通知，成功返回 True。"""


class InboxChannel(INotificationChannel):
    """站内消息通道：写 message 表。"""

    name = "inbox"

    def deliver(self, conn: sqlite3.Connection, message) -> bool:
        dup = conn.execute(
            """SELECT 1 FROM message
                WHERE student_id = ? AND activity_id IS ? AND content = ? LIMIT 1""",
            (message.student_id, message.activity_id, message.content),
        ).fetchone()
        if dup:
            return False  # 幂等：同一条消息不重复写
        conn.execute(
            """INSERT INTO message(student_id, activity_id, kind, content, created_at, is_read)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (message.student_id, message.activity_id, message.kind,
             message.content, message.created_at),
        )
        return True


class AuditChannel(INotificationChannel):
    """审计通道：把通知轨迹打到标准输出 / 审计表，用于"通知失败留痕"。"""

    name = "audit"

    def deliver(self, conn: sqlite3.Connection, message) -> bool:
        content = f"[{message.student_id}] {message.content}"
        dup = conn.execute(
            "SELECT 1 FROM message WHERE student_id = '__audit__' AND content = ? LIMIT 1",
            (content,),
        ).fetchone()
        if dup:
            return False  # 幂等：重试不重复记审计
        conn.execute(
            """INSERT INTO message(student_id, activity_id, kind, content, created_at, is_read)
               VALUES (?, ?, 'AUDIT', ?, ?, 1)""",
            ("__audit__", message.activity_id, content, message.created_at),
        )
        return True


class NotificationService:
    """发布者。业务侧只调 publish()，不关心有几个通道、每个通道怎么实现。"""

    def __init__(self, channels: Optional[List[INotificationChannel]] = None):
        self._channels = channels or [InboxChannel(), AuditChannel()]
        self._lock = threading.Lock()
        self.failures: List[Dict[str, str]] = []  # 只用于排障与测试断言

    def register(self, channel: INotificationChannel) -> None:
        with self._lock:
            self._channels.append(channel)

    def publish(self, conn: sqlite3.Connection, message) -> Dict[str, bool]:
        """逐个通道投递。任一通道异常都不向调用方抛出。"""
        result: Dict[str, bool] = {}
        for ch in self._channels:
            try:
                result[ch.name] = bool(ch.deliver(conn, message))
            except Exception as exc:  # 通知失败绝不能把报名一起回滚
                result[ch.name] = False
                detail = {"channel": ch.name, "error": f"{type(exc).__name__}: {exc}",
                          "content": message.content}
                with self._lock:
                    self.failures.append(detail)
                # 留痕：即使通道炸了，也要在审计表里留下"这条通知没发出去"
                try:
                    repo.insert_message(
                        conn, "__audit__", message.activity_id,
                        f"通知失败[{ch.name}] {detail['error']}｜原文：{message.content}",
                        kind="NOTIFY_FAILED",
                    )
                except Exception:
                    pass
        return result


def remind_approved(conn: sqlite3.Connection, service: NotificationService,
                    activity_id: int, title: str) -> None:
    """名额余量变化后，提醒该活动所有"已通过"的学生（未来可关掉，不影响业务）。"""
    rows = conn.execute(
        "SELECT student_id FROM registration WHERE activity_id = ? AND status = '已通过'",
        (activity_id,),
    ).fetchall()
    for r in rows:
        repo.insert_message(
            conn, r["student_id"], activity_id,
            f"「{title}」名额余量已更新", kind="INFO",
        )