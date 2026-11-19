"""报名策略（Strategy 模式）。

对照实验指导书 关键任务 B：
- 定义抽象策略 RegistrationPolicy，把"一次报名申请应该落到什么状态"抽成接口；
- DirectPolicy / ApprovalPolicy 是两个实现；
- RegistrationService 只依赖接口，不写 if / elif 判类型；
- 后续新增"班级限定""抽签"等策略，只要加一个类并在 register_policy() 里注册即可，
  Service 一行都不用改。

真正需要"审核"这个动作的只有 ApprovalPolicy，所以接口里多了一个
requires_approval() 钩子，直接报名的策略直接返回 False。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .constants import (
    ALL_POLICIES,
    POLICY_APPROVAL,
    POLICY_DIRECT,
    ST_APPROVED,
    ST_PENDING,
    SealError,
)


class RegistrationPolicy(ABC):
    """报名策略接口。"""

    code: str = ""
    label: str = ""

    @abstractmethod
    def decide(self, seats_left: int) -> str:
        """返回这次申请最终落到哪个状态。seats_left 为当前剩余名额。"""

    @abstractmethod
    def requires_approval(self) -> bool:
        """是否需要管理员二次审核。"""

    # ---- 公共规则检查（所有策略共享，放在基类里，各实现不用重复写） ----
    def check(self, *, seats_left: int, capacity: int) -> None:
        if self.requires_approval():
            # 审核型报名只登记意向，不占名额；满员时连申请都不收
            if seats_left <= 0:
                raise SealError("活动名额已满，无法提交申请", "CAPACITY_FULL")
        else:
            if seats_left <= 0:
                raise SealError("活动名额已满，无法报名", "CAPACITY_FULL")


class DirectPolicy(RegistrationPolicy):
    """直接报名：提交即通过。"""

    code = POLICY_DIRECT
    label = "直接报名"

    def decide(self, seats_left: int) -> str:
        return ST_APPROVED

    def requires_approval(self) -> bool:
        return False


class ApprovalPolicy(RegistrationPolicy):
    """审核型：提交后进入待审核，待审核不占名额。"""

    code = POLICY_APPROVAL
    label = "需审核"

    def decide(self, seats_left: int) -> str:
        return ST_PENDING

    def requires_approval(self) -> bool:
        return True


_POLICIES = {p.code: p for p in (DirectPolicy(), ApprovalPolicy())}


def get_policy(code: Optional[str]) -> RegistrationPolicy:
    """按活动上的 policy_type 取策略实例（无状态，可共享）。"""
    try:
        return _POLICIES[code or ""]
    except KeyError:
        raise SealError(f"未知的报名策略：{code}", "UNKNOWN_POLICY")


def policy_labels() -> dict:
    return {code: get_policy(code).label for code in ALL_POLICIES}