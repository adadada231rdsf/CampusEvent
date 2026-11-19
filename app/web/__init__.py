"""Flask 装配层：路由在这里，业务判断一律下沉到 domain/。"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from ..domain import repository as repo
from ..domain.activity_service import ActivityService, parse_activity_form
from ..domain.constants import POLICY_LABELS, SealError, ST_APPROVED, ST_PENDING
from ..domain.notification import NotificationService
from ..domain.policy import policy_labels
from ..domain.registration_service import RegistrationService

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CAMPUSEVENT_SECRET", "campus-event-dev-key"),
        DATABASE=str(BASE_DIR.parent / "instance" / "campusevent.sqlite"),
    )
    if config:
        app.config.update(config)

    app.config["NOTIFIER"] = NotificationService()

    # ---------- 每请求一个连接 ----------
    def get_conn():
        if "conn" not in g:
            g.conn = repo.connect(app.config["DATABASE"])
            repo.ensure_students(g.conn)
            g.conn.commit()
        return g.conn

    @app.teardown_appcontext
    def _close(exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    app.extensions["get_conn"] = get_conn

    @app.context_processor
    def inject():
        conn = get_conn() if not app.config.get("TESTING") else None
        sid = session.get("student_id")
        return {
            "APP_NAME": "CampusEvent 校园活动报名",
            "CURRENT": get_current_student(sid),
            "IS_ADMIN": session.get("role") == "admin",
            "POLICY_LABELS": POLICY_LABELS,
            "POLICY_OPTIONS": policy_labels(),
            "STATUSES": ("待审核", "已通过", "已拒绝", "已取消"),
        }

    # ================= 登录 / 角色切换 =================
    def get_current_student(sid):
        if not sid:
            return None
        try:
            row = repo.get_student(get_conn(), sid)
        except Exception:
            return None
        return dict(row) if row else None

    @app.route("/login", methods=("GET", "POST"))
    def login():
        conn = get_conn()
        students = repo.all_students(conn)
        if request.method == "POST":
            sid = (request.form.get("student_id") or "").strip()
            if sid == "admin":
                session.clear()
                session["role"] = "admin"
                flash("已以管理员身份登录", "success")
                return redirect(url_for("admin_activities"))
            if repo.get_student(conn, sid) is None:
                flash("学号不存在，请从下拉框选择演示账号", "error")
            else:
                session.clear()
                session["student_id"] = sid
                flash("登录成功", "success")
                return redirect(url_for("activity_list"))
        return render_template("login.html", students=[dict(s) for s in students])

    @app.route("/logout")
    def logout():
        session.clear()
        flash("已退出", "success")
        return redirect(url_for("login"))

    # ================= 学生端 =================
    @app.route("/")
    def activity_list():
        conn = get_conn()
        if session.get("role") != "admin" and not session.get("student_id"):
            return redirect(url_for("login"))
        keyword = (request.args.get("q") or "").strip()
        activities = repo.list_activities(conn, keyword)
        svc = RegistrationService(conn, app.config["NOTIFIER"])
        rows = []
        for a in activities:
            d = dict(a)
            d.update(svc.stats(a["activity_id"]))
            d["my_reg"] = None
            if session.get("student_id"):
                d["my_reg"] = repo.active_registration(conn, a["activity_id"], session["student_id"])
            rows.append(d)
        return render_template("activities.html", activities=rows, keyword=keyword)

    @app.route("/activity/<int:activity_id>")
    def activity_detail(activity_id):
        conn = get_conn()
        act = repo.get_activity(conn, activity_id)
        if act is None:
            abort(404)
        svc = RegistrationService(conn, app.config["NOTIFIER"])
        d = dict(act)
        d.update(svc.stats(activity_id))
        d["registrations"] = [dict(r) for r in repo.registrations_of_activity(conn, activity_id)]
        d["my_reg"] = None
        if session.get("student_id"):
            d["my_reg"] = repo.active_registration(conn, activity_id, session["student_id"])
        return render_template("activity_detail.html", a=d)

    @app.post("/activity/<int:activity_id>/register")
    def register(activity_id):
        sid = session.get("student_id")
        if not sid:
            flash("请先登录学生账号", "error")
            return redirect(url_for("login"))
        svc = RegistrationService(get_conn(), app.config["NOTIFIER"])
        try:
            r = svc.register(activity_id, sid)
        except SealError as e:
            flash(e.message, "error")
        else:
            if r["status"] == ST_APPROVED:
                flash(f"报名成功，剩余名额 {r['seats_left']}", "success")
            else:
                flash("申请已提交，等待管理员审核", "success")
        return redirect(url_for("activity_detail", activity_id=activity_id))

    @app.post("/registration/<int:registration_id>/cancel")
    def cancel(registration_id):
        sid = session.get("student_id")
        if not sid:
            flash("请先登录学生账号", "error")
            return redirect(url_for("login"))
        svc = RegistrationService(get_conn(), app.config["NOTIFIER"])
        back = request.form.get("back") or url_for("my_registrations")
        try:
            svc.cancel(registration_id, sid)
            flash("已取消报名", "success")
        except SealError as e:
            flash(e.message, "error")
        return redirect(back)

    @app.route("/my")
    def my_registrations():
        sid = session.get("student_id")
        if not sid:
            return redirect(url_for("login"))
        conn = get_conn()
        rows = [dict(r) for r in repo.registrations_of_student(conn, sid)]
        return render_template("my_registrations.html", rows=rows)

    @app.route("/messages")
    def messages():
        sid = session.get("student_id")
        if not sid:
            return redirect(url_for("login"))
        conn = get_conn()
        rows = [dict(r) for r in repo.messages_of(conn, sid)]
        repo.mark_all_read(conn, sid)
        conn.commit()
        return render_template("messages.html", rows=rows)

    # ================= 管理员端 =================
    def require_admin():
        if session.get("role") != "admin":
            abort(403)

    @app.route("/admin/activities")
    def admin_activities():
        require_admin()
        conn = get_conn()
        svc = RegistrationService(conn, app.config["NOTIFIER"])
        rows = []
        for a in repo.list_activities(conn):
            d = dict(a)
            d.update(svc.stats(a["activity_id"]))
            rows.append(d)
        return render_template("admin_activities.html", activities=rows)

    @app.route("/admin/activity/new", methods=("GET", "POST"))
    def admin_activity_new():
        require_admin()
        conn = get_conn()
        if request.method == "POST":
            try:
                act = parse_activity_form(request.form)
                aid = ActivityService(conn).create(act)
            except SealError as e:
                flash(e.message, "error")
                return render_template("admin_activity_form.html", a=request.form, mode="new")
            flash(f"活动「{act.title}」已创建（编号 {aid}）", "success")
            return redirect(url_for("admin_activities"))
        return render_template("admin_activity_form.html", a={}, mode="new")

    @app.route("/admin/activity/<int:activity_id>/edit", methods=("GET", "POST"))
    def admin_activity_edit(activity_id):
        require_admin()
        conn = get_conn()
        act = repo.get_activity(conn, activity_id)
        if act is None:
            abort(404)
        if request.method == "POST":
            try:
                data = parse_activity_form(request.form)
                data.activity_id = activity_id
                ActivityService(conn).update(data)
            except SealError as e:
                flash(e.message, "error")
                d = dict(request.form)
                d["activity_id"] = activity_id
                return render_template("admin_activity_form.html", a=d, mode="edit")
            flash("已保存修改", "success")
            return redirect(url_for("admin_activities"))
        d = dict(act)
        d["start_at"] = d["start_at"].replace(" ", "T")
        return render_template("admin_activity_form.html", a=d, mode="edit")

    @app.post("/admin/activity/<int:activity_id>/delete")
    def admin_activity_delete(activity_id):
        require_admin()
        try:
            info = ActivityService(get_conn()).delete(activity_id)
            flash(
                f"活动「{info['title']}」已软删除（{info['soft_deleted_at']}），"
                f"受影响报名：待审核 {info['affected_pending']} 条、已通过 {info['affected_approved']} 条",
                "success",
            )
        except SealError as e:
            flash(e.message, "error")
        return redirect(url_for("admin_activities"))

    @app.route("/admin/approvals")
    def admin_approvals():
        require_admin()
        conn = get_conn()
        rows = [dict(r) for r in repo.pending_registrations(conn)]
        return render_template("admin_approvals.html", rows=rows)

    @app.post("/admin/registration/<int:registration_id>/approve")
    def admin_approve(registration_id):
        require_admin()
        svc = RegistrationService(get_conn(), app.config["NOTIFIER"])
        try:
            r = svc.approve(registration_id)
            flash(f"已批准，剩余名额 {r['seats_left']}", "success")
        except SealError as e:
            flash(e.message, "error")
        return redirect(url_for("admin_approvals"))

    @app.post("/admin/registration/<int:registration_id>/reject")
    def admin_reject(registration_id):
        require_admin()
        svc = RegistrationService(get_conn(), app.config["NOTIFIER"])
        reason = (request.form.get("reason") or "").strip() or "名额已满或不符合报名条件"
        try:
            svc.reject(registration_id, reason)
            flash("已拒绝该申请", "success")
        except SealError as e:
            flash(e.message, "error")
        return redirect(url_for("admin_approvals"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="需要管理员身份"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="页面或活动不存在"), 404

    return app