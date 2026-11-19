"""C10：重启（重新建立连接 / 新建应用实例）后数据仍然一致。"""
from __future__ import annotations

from app import create_app
from app.domain import repository as repo
from app.domain.entities import Activity
from app.domain.notification import NotificationService
from app.domain.registration_service import RegistrationService


def test_data_survives_new_connection(db_path):
    c1 = repo.connect(db_path)
    repo.ensure_students(c1)
    aid = repo.insert_activity(
        c1, Activity(None, "持久化活动", "讲座", "2099-01-01 10:00", "报告厅", 3, "DIRECT")
    )
    c1.commit()
    svc = RegistrationService(c1, NotificationService())
    rid = svc.register(aid, "2024001")["registration_id"]
    c1.close()  # 模拟停止服务

    c2 = repo.connect(db_path)  # 模拟重启
    try:
        assert repo.get_registration(c2, rid)["status"] == "已通过"
        assert repo.get_activity(c2, aid)["title"] == "持久化活动"
        st = RegistrationService(c2, NotificationService()).stats(aid)
        assert st["approved"] == 1 and st["seats_left"] == 2
        assert any("报名成功" in m["content"] for m in repo.messages_of(c2, "2024001"))
    finally:
        c2.close()


def test_web_data_survives_new_app_instance(db_path):
    app1 = create_app({"DATABASE": db_path, "TESTING": True, "SECRET_KEY": "k1"})
    c1 = app1.test_client()
    c1.post("/login", data={"student_id": "admin"})
    c1.post(
        "/admin/activity/new",
        data={"title": "重启也要在", "category": "讲座", "start_at": "2099-05-01T14:00",
              "location": "报告厅", "capacity": "2", "policy_type": "DIRECT"},
    )
    c1.get("/logout")
    c1.post("/login", data={"student_id": "2024001"})
    c1.post("/activity/1/register")

    # 新建一个应用实例（新的 Flask、新的连接池），读同一个数据库文件
    app2 = create_app({"DATABASE": db_path, "TESTING": True, "SECRET_KEY": "k2"})
    c2 = app2.test_client()
    c2.post("/login", data={"student_id": "2024001"})
    body = c2.get("/my").get_data(as_text=True)
    assert "重启也要在" in body
    assert "已通过" in body

    c2.get("/logout")
    c2.post("/login", data={"student_id": "2024002"})
    detail = c2.get("/activity/1").get_data(as_text=True)
    assert "剩余名额" in detail

    # 直接查库做最终断言：重启后仍只有一条已通过报名
    conn = repo.connect(db_path)
    try:
        assert repo.count_approved(conn, 1) == 1
    finally:
        conn.close()
