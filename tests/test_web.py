"""Web 层端到端测试：路由、权限、表单与页面渲染（C1–C9）。"""
from __future__ import annotations

from app.domain import repository as repo

from conftest import login_admin, login_student


def test_anonymous_is_redirected_to_login(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_login_page_lists_demo_accounts(client):
    body = client.get("/login").get_data(as_text=True)
    assert "2024001" in body and "admin" in body


def test_student_login_shows_activity_list(client, make_activity):
    make_activity(title="人工智能讲座")
    r = login_student(client)
    assert r.status_code == 200
    assert "人工智能讲座" in r.get_data(as_text=True)


def test_login_with_unknown_student_shows_error(client):
    r = client.post("/login", data={"student_id": "9999999"})
    assert r.status_code == 200
    assert "学号不存在" in r.get_data(as_text=True)


def test_admin_login_goes_to_admin_page(client):
    r = login_admin(client)
    assert r.status_code == 200
    assert "活动管理" in r.get_data(as_text=True)


def test_student_cannot_open_admin_pages(client):
    login_student(client)
    r = client.get("/admin/activities")
    assert r.status_code == 403
    assert "403" in r.get_data(as_text=True)


def test_create_activity_through_form(client, conn):
    login_admin(client)
    r = client.post(
        "/admin/activity/new",
        data={
            "title": "网页创建的讲座", "category": "讲座", "start_at": "2099-05-01T14:00",
            "location": "报告厅", "capacity": "2", "policy_type": "DIRECT",
        },
        follow_redirects=True,
    )
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "已创建" in body and "网页创建的讲座" in body
    assert len(repo.list_activities(conn)) == 1


def test_create_activity_invalid_form_keeps_input(client):
    login_admin(client)
    r = client.post(
        "/admin/activity/new",
        data={"title": "", "start_at": "bad", "location": "", "capacity": "0", "policy_type": "X"},
    )
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "活动名称不能为空" in body  # flash 提示，表单不丢数据


def test_register_direct_activity_via_web(client, make_activity, conn):
    aid = make_activity(title="直接报名活动", capacity=2, policy="DIRECT")
    login_student(client)
    r = client.post(f"/activity/{aid}/register", follow_redirects=True)
    body = r.get_data(as_text=True)
    assert "报名成功" in body
    assert "已通过" in body
    rows = repo.registrations_of_activity(conn, aid)
    assert len(rows) == 1 and rows[0]["status"] == "已通过"


def test_duplicate_register_via_web_is_rejected(client, make_activity):
    aid = make_activity(capacity=2, policy="DIRECT")
    login_student(client)
    client.post(f"/activity/{aid}/register")
    r = client.post(f"/activity/{aid}/register", follow_redirects=True)
    assert "你已经报过这个活动了" in r.get_data(as_text=True)


def test_full_activity_shows_no_register_button(client, make_activity):
    aid = make_activity(capacity=1, policy="DIRECT")
    login_student(client, "2024001")
    client.post(f"/activity/{aid}/register")
    client.get("/logout")
    login_student(client, "2024002")
    body = client.get("/activity/{}".format(aid)).get_data(as_text=True)
    assert "名额已满" in body


def test_approve_flow_and_capacity_error_when_full(client, make_activity, conn):
    aid = make_activity(capacity=1, policy="APPROVAL")
    login_student(client, "2024001")
    client.post(f"/activity/{aid}/register")
    client.get("/logout")
    login_student(client, "2024002")
    client.post(f"/activity/{aid}/register")
    client.get("/logout")

    login_admin(client)
    body = client.get("/admin/approvals").get_data(as_text=True)
    assert "待审核" in body and "批准" in body

    ids = [r["registration_id"] for r in repo.pending_registrations(conn)]
    assert len(ids) == 2
    r = client.post(f"/admin/registration/{ids[0]}/approve", follow_redirects=True)
    assert "已批准" in r.get_data(as_text=True)

    r = client.post(f"/admin/registration/{ids[1]}/approve", follow_redirects=True)
    assert "名额已满" in r.get_data(as_text=True)
    assert [x["status"] for x in repo.pending_registrations(conn)] == ["待审核"]


def test_messages_page_marks_read(client, make_activity, conn):
    aid = make_activity(capacity=2, policy="DIRECT")
    login_student(client)
    client.post(f"/activity/{aid}/register")
    assert repo.unread_count(conn, "2024001") >= 1
    body = client.get("/messages").get_data(as_text=True)
    assert "报名成功" in body
    assert repo.unread_count(conn, "2024001") == 0


def test_unknown_activity_returns_404(client):
    login_student(client)
    r = client.get("/activity/99999")
    assert r.status_code == 404
    assert "404" in r.get_data(as_text=True)


def test_logout_clears_session(client):
    login_student(client)
    r = client.get("/logout")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]
