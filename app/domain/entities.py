"""领域对象：纯数据，不含业务规则，不 import Flask。

Activity / Student / Registration / Message 对应指导书 附录 B.1 表22。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .constants import POLICY_APPROVAL, POLICY_LABELS


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str


@dataclass
class Activity:
    activity_id: Optional[int]
    title: str
    category: str
    start_at: str          # 'YYYY-MM-DD HH:MM'
    location: str
    capacity: int
    policy_type: str       # 'DIRECT' | 'APPROVAL'

    @property
    def policy_label(self) -> str:
        return POLICY_LABELS.get(self.policy_type, self.policy_type)

    @property
    def needs_approval(self) -> bool:
        return self.policy_type == POLICY_APPROVAL


@dataclass
class Registration:
    registration_id: Optional[int]
    activity_id: int
    student_id: str
    status: str
    created_at: str
    updated_at: str
    note: str = ""
    # 以下为联表查询带出的展示字段，不入库
    activity_title: str = ""


@dataclass
class Message:
    message_id: Optional[int]
    student_id: str
    activity_id: Optional[int]
    content: str
    created_at: str
    is_read: bool = False
    kind: str = "INFO"
    seq: int = 0