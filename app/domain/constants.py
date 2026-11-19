"""领域常量：报名状态、报名策略类型、业务异常。

约束来源：实验指导书 附录 B.1（表22）与 B.2 业务规则。
状态只允许 待审核 / 已通过 / 已拒绝 / 已取消 四种。
"""
from __future__ import annotations

# ---------- 报名状态 ----------
ST_PENDING = "待审核"
ST_APPROVED = "已通过"
ST_REJECTED = "已拒绝"
ST_CANCELLED = "已取消"
ALL_STATUSES = (ST_PENDING, ST_APPROVED, ST_REJECTED, ST_CANCELLED)
# 有效报名：同一学生对同一活动最多只能有一条
ACTIVE_STATUSES = (ST_PENDING, ST_APPROVED)

# ---------- 报名策略类型 ----------
POLICY_DIRECT = "DIRECT"    # 直接报名：提交即通过
POLICY_APPROVAL = "APPROVAL"  # 审核型：提交后进入待审核
ALL_POLICIES = (POLICY_DIRECT, POLICY_APPROVAL)

POLICY_LABELS = {
    POLICY_DIRECT: "直接报名",
    POLICY_APPROVAL: "需审核",
}


class SealError(Exception):
    """业务规则被拒绝。一句话说明原因，直接展示给学生看。"""

    def __init__(self, message: str, code: str = "BUSINESS_RULE"):
        super().__init__(message)
        self.message = message
        self.code = code