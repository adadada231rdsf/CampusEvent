"""生成演示数据，便于验收与截图。

    python seed_demo.py          # 已有数据时不动
    python seed_demo.py --reset  # 清空 instance/campusevent.sqlite 后重建

演示场景覆盖验收用例 C1–C9 的可观察状态：
  · 直接报名、名额已满的讲座（C1/C2/C4）
  · 需审核的活动：待审核若干、已批准若干（C5/C6/C7）
  · 学生已取消的历史记录（C9）
  · 站内通知（报名成功、审批结果）
"""
from __future__ import annotations

import os
import sys

from app import create_app
from app.domain import repository as repo
from app.domain.entities import Activity
from app.domain.registration_service import RegistrationService

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "campusevent.sqlite")


def seed(conn, notifier):
    svc = RegistrationService(conn, notifier)
    created = []

    def add_activity(title, category, start_at, location, capacity, policy):
        aid = repo.insert_activity(
            conn,
            Activity(
                activity_id=None, title=title, category=category, start_at=start_at,
                location=location, capacity=capacity, policy_type=policy,
            ),
        )
        conn.commit()
        created.append((aid, title, capacity, policy))
        return aid

    # 1) 直接报名 + 名额只有 2 个：报满后第三人会失败（C1/C2/C4）
    a1 = add_activity("人工智能前沿讲座", "讲座", "2026-12-03 14:00", "图书馆报告厅", 2, "DIRECT")
    svc.register(a1, "2024001")   # 张三 → 已通过
    svc.register(a1, "2024002")   # 李四 → 已通过，此时名额已满

    # 2) 需审核：两条待审核 + 一条已批准（C5/C6/C7）
    a2 = add_activity("校园程序设计竞赛", "竞赛", "2026-12-10 09:00", "实验楼 A305", 3, "APPROVAL")
    r1 = svc.register(a2, "2024001")["registration_id"]
    svc.register(a2, "2024003")       # 王五 → 待审核
    svc.register(a2, "2024002")       # 李四 → 待审核
    svc.approve(r1)                   # 张三 → 已通过（触发通知 + 审计）

    # 3) 直接报名 + 取消：留下“已取消”历史（C9）
    a3 = add_activity("图书馆志愿服务", "志愿", "2026-12-15 15:30", "图书馆一层", 30, "DIRECT")
    r = svc.register(a3, "2024002")["registration_id"]
    svc.register(a3, "2024003")
    svc.cancel(r, "2024002")

    # 4) 需审核 + 名额 2：三条待审核，批准两条后满员，第三条批准会失败（C8）
    a4 = add_activity("校园歌手大赛决赛", "文艺", "2026-12-20 19:00", "大学生活动中心", 2, "APPROVAL")
    r1 = svc.register(a4, "2024003")["registration_id"]
    r2 = svc.register(a4, "2024001")["registration_id"]
    svc.register(a4, "2024002")       # 李四 → 保持待审核（管理员点批准会失败）
    svc.approve(r1)
    svc.approve(r2)

    return created


def main() -> int:
    reset = "--reset" in sys.argv
    if os.path.exists(DB) and reset:
        os.remove(DB)
        print(f"已删除 {DB}")
    app = create_app()
    with app.app_context():
        conn = repo.connect(DB)
        repo.ensure_students(conn)
        conn.commit()
        existing = repo.list_activities(conn)
        if existing:
            print(f"数据库已有 {len(existing)} 个活动，未重复生成（加 --reset 可重建）。")
        else:
            created = seed(conn, app.config["NOTIFIER"])
            print(f"已生成 {len(created)} 个活动：")
            for aid, title, cap, policy in created:
                stats = RegistrationService(conn, app.config["NOTIFIER"]).stats(aid)
                print(
                    f"  #{aid} {title} [{policy}] 上限 {cap} "
                    f"已通过 {stats['approved']} 待审核 {stats['pending']} 剩余 {stats['seats_left']}"
                )
        print(f"数据库：{DB}")
        print("启动：python run.py  →  http://127.0.0.1:5000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
