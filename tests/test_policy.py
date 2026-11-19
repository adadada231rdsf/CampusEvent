"""策略模式单测（关键任务 B）。"""
from __future__ import annotations

import pytest

from app.domain.constants import SealError
from app.domain.policy import (
    ApprovalPolicy,
    DirectPolicy,
    get_policy,
    policy_labels,
)


def test_labels_cover_both_policies():
    assert policy_labels() == {"DIRECT": "直接报名", "APPROVAL": "需审核"}


def test_get_policy_returns_singletons():
    assert get_policy("DIRECT") is get_policy("DIRECT")
    assert isinstance(get_policy("DIRECT"), DirectPolicy)


def test_get_policy_unknown_raises():
    with pytest.raises(SealError) as exc:
        get_policy("LOTTERY")
    assert exc.value.code == "UNKNOWN_POLICY"


def test_direct_policy_decide_and_flag():
    p = DirectPolicy()
    assert p.decide(seats_left=1) == "已通过"
    assert p.requires_approval() is False


def test_approval_policy_decide_and_flag():
    p = ApprovalPolicy()
    assert p.decide(seats_left=1) == "待审核"
    assert p.requires_approval() is True


@pytest.mark.parametrize("policy", [DirectPolicy(), ApprovalPolicy()])
def test_check_raises_when_full(policy):
    with pytest.raises(SealError) as exc:
        policy.check(seats_left=0, capacity=5)
    assert exc.value.code == "CAPACITY_FULL"


@pytest.mark.parametrize("policy", [DirectPolicy(), ApprovalPolicy()])
def test_check_passes_when_seat_available(policy):
    policy.check(seats_left=1, capacity=5)  # 不抛异常即通过


def test_policy_instances_are_stateless_shareable():
    """同一实例被多个请求复用也不会串状态（无实例字段）。"""
    p = get_policy("APPROVAL")
    assert p.decide(seats_left=0) == "待审核"
    assert vars(p) == {}
