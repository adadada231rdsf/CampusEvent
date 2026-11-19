"""仓储层：唯一接触 SQL 的地方。

设计取舍（写进报告用）：
1. 不引入 ORM。本系统只有 4 张表，SQL 直写更容易被老师和作者本人审查，
   也能精确控制事务边界（名额检查与插入必须在同一事务里）。
2. 全部使用参数化查询（? 占位符），不使用字符串拼接，杜绝 SQL 注入。
3. 仓储只做"增删改查"，不含任何业务判断；业务判断集中在 domain/registration_service.py。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..domain.constants import (
    ACTIVE_STATUSES,
    ST_APPROVED,
    ST_CANCELLED,
    ST_PENDING,
    ST_REJECTED,
)
from ..domain.entities import Activity, Message, Registration

SCHEMA = """
CREATE TABLE IF NOT EXISTS student (
    student_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    start_at    TEXT    NOT NULL,
    location    TEXT    NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity > 0),
    policy_type TEXT    NOT NULL CHECK (policy_type IN ('DIRECT', 'APPROVAL')),
    deleted_at  TEXT              -- 软删除时间；NULL 表示未删除
);

CREATE TABLE IF NOT EXISTS registration (
    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL REFERENCES activity(activity_id),
    student_id      TEXT    NOT NULL REFERENCES student(student_id),
    status          TEXT    NOT NULL
                    CHECK (status IN ('待审核', '已通过', '已拒绝', '已取消')),
    note            TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- 同一学生同一活动最多一条有效报名：由数据库兜底，防止并发下插两条
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_active
    ON registration(activity_id, student_id)
    WHERE status IN ('待审核', '已通过');

CREATE INDEX IF NOT EXISTS ix_reg_activity_status ON registration(activity_id, status);
CREATE INDEX IF NOT EXISTS ix_reg_student         ON registration(student_id);

CREATE TABLE IF NOT EXISTS message (
    message_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT    NOT NULL,
    activity_id INTEGER,
    kind        TEXT    NOT NULL DEFAULT 'INFO',
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_msg_student ON message(student_id, message_id);
"""

SEED_STUDENTS = [
    ("2024001", "张三"),
    ("2024002", "李四"),
    ("2024003", "王五"),
]


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- 学生 ----------------
def ensure_students(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO student(student_id, name) VALUES (?, ?)", SEED_STUDENTS
    )


def get_student(conn: sqlite3.Connection, student_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM student WHERE student_id = ?", (student_id,)
    ).fetchone()


def all_students(conn: sqlite3.Connection):
    return conn.execute("SELECT * FROM student ORDER BY student_id").fetchall()


# ---------------- 活动 ----------------
def insert_activity(conn: sqlite3.Connection, a: Activity) -> int:
    cur = conn.execute(
        """INSERT INTO activity(title, category, start_at, location, capacity, policy_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (a.title, a.category, a.start_at, a.location, a.capacity, a.policy_type),
    )
    return int(cur.lastrowid)


def update_activity(conn: sqlite3.Connection, a: Activity) -> None:
    conn.execute(
        """UPDATE activity
              SET title = ?, category = ?, start_at = ?, location = ?, capacity = ?, policy_type = ?
            WHERE activity_id = ?""",
        (a.title, a.category, a.start_at, a.location, a.capacity, a.policy_type, a.activity_id),
    )


def get_activity(conn: sqlite3.Connection, activity_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM activity WHERE activity_id = ? AND deleted_at IS NULL",
        (activity_id,),
    ).fetchone()


def list_activities(conn: sqlite3.Connection, keyword: str = ""):
    sql = "SELECT * FROM activity WHERE deleted_at IS NULL"
    args: list = []
    if keyword:
        sql += " AND title LIKE ?"
        args.append("%" + keyword + "%")
    sql += " ORDER BY start_at, activity_id"
    return conn.execute(sql, args).fetchall()


def soft_delete_activity(conn: sqlite3.Connection, activity_id: int) -> None:
    conn.execute(
        "UPDATE activity SET deleted_at = ? WHERE activity_id = ?", (now(), activity_id)
    )


def hard_delete_activity(conn: sqlite3.Connection, activity_id: int) -> None:
    conn.execute("DELETE FROM activity WHERE activity_id = ?", (activity_id,))


# ---------------- 报名 ----------------
def insert_registration(
    conn: sqlite3.Connection, activity_id: int, student_id: str, status: str, note: str = ""
) -> int:
    ts = now()
    cur = conn.execute(
        """INSERT INTO registration(activity_id, student_id, status, note, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (activity_id, student_id, status, note, ts, ts),
    )
    return int(cur.lastrowid)


def get_registration(conn: sqlite3.Connection, registration_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM registration WHERE registration_id = ?", (registration_id,)
    ).fetchone()


def update_status(conn: sqlite3.Connection, registration_id: int, status: str, note: str = "") -> None:
    conn.execute(
        "UPDATE registration SET status = ?, note = ?, updated_at = ? WHERE registration_id = ?",
        (status, note, now(), registration_id),
    )


def active_registration(conn: sqlite3.Connection, activity_id: int, student_id: str):
    """该学生在该活动上的有效报名（待审核/已通过），没有则返回 None。"""
    marks = ",".join("?" for _ in ACTIVE_STATUSES)
    return conn.execute(
        f"""SELECT * FROM registration
             WHERE activity_id = ? AND student_id = ? AND status IN ({marks})""",
        (activity_id, student_id, *ACTIVE_STATUSES),
    ).fetchone()


def count_approved(conn: sqlite3.Connection, activity_id: int) -> int:
    """名额只按"已通过"计算，待审核不占名额（B.2 第 3 条）。"""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM registration WHERE activity_id = ? AND status = ?",
        (activity_id, ST_APPROVED),
    ).fetchone()
    return int(row["n"])


def count_by_status(conn: sqlite3.Connection, activity_id: int) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM registration WHERE activity_id = ? GROUP BY status",
        (activity_id,),
    ).fetchall()
    counts = {k: 0 for k in (ST_PENDING, ST_APPROVED, ST_REJECTED, ST_CANCELLED)}
    for r in rows:
        counts[r["status"]] = int(r["n"])
    return counts


def registrations_of_student(conn: sqlite3.Connection, student_id: str):
    return conn.execute(
        """SELECT r.*, a.title AS activity_title, a.start_at AS activity_start_at
             FROM registration r JOIN activity a ON a.activity_id = r.activity_id
            WHERE r.student_id = ? AND a.deleted_at IS NULL
            ORDER BY r.registration_id DESC""",
        (student_id,),
    ).fetchall()


def registrations_of_activity(conn: sqlite3.Connection, activity_id: int):
    return conn.execute(
        """SELECT r.*, s.name AS student_name
             FROM registration r JOIN student s ON s.student_id = r.student_id
            WHERE r.activity_id = ?
            ORDER BY r.registration_id""",
        (activity_id,),
    ).fetchall()


def pending_registrations(conn: sqlite3.Connection):
    return conn.execute(
        """SELECT r.*, s.name AS student_name, a.title AS activity_title,
                  a.capacity AS capacity
             FROM registration r
             JOIN student s  ON s.student_id = r.student_id
             JOIN activity a ON a.activity_id = r.activity_id
            WHERE r.status = ? AND a.deleted_at IS NULL
            ORDER BY r.registration_id""",
        (ST_PENDING,),
    ).fetchall()


# ---------------- 通知 ----------------
def insert_message(
    conn: sqlite3.Connection, student_id: str, activity_id: Optional[int], content: str, kind: str = "INFO"
) -> int:
    cur = conn.execute(
        """INSERT INTO message(student_id, activity_id, kind, content, created_at, is_read)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (student_id, activity_id, kind, content, now()),
    )
    return int(cur.lastrowid)


def messages_of(conn: sqlite3.Connection, student_id: str, limit: int = 50):
    return conn.execute(
        "SELECT * FROM message WHERE student_id = ? ORDER BY message_id DESC LIMIT ?",
        (student_id, limit),
    ).fetchall()


def unread_count(conn: sqlite3.Connection, student_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM message WHERE student_id = ? AND is_read = 0",
        (student_id,),
    ).fetchone()
    return int(row["n"])


def mark_all_read(conn: sqlite3.Connection, student_id: str) -> None:
    conn.execute("UPDATE message SET is_read = 1 WHERE student_id = ?", (student_id,))