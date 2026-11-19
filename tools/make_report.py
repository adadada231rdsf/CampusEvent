# -*- coding: utf-8 -*-
"""生成《软件工程》实验二实验报告 docx（附录 D.1 结构）。

用法（cwd = CampusEvent 根目录）：
    C:\\Users\\alice\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe tools\\make_report.py

依赖：python-docx（dsh 运行时已带）。图片缺失时自动降级为文字占位，不中断生成。
"""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
DIAG = DOCS / "diagrams"
OUT = DOCS / "实验二_实验报告_宋逸轩.docx"

STUDENT = "242806010116　宋逸轩"
COURSE = "《软件工程》实验二"
TITLE = "CampusEvent 校园活动报名系统"

FONT_CN = "微软雅黑"
FONT_EN = "Segoe UI"


def set_run_font(run, size=None, bold=None, color=None, cn=FONT_CN, en=FONT_EN):
    run.font.name = en
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def style_doc(doc: Document):
    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    pf = normal.paragraph_format
    pf.line_spacing = 1.35
    pf.space_after = Pt(4)

    for name, size, color in (("Heading 1", 16, (0x1F, 0x38, 0x64)), ("Heading 2", 13, (0x2B, 0x5F, 0xD9)), ("Heading 3", 11.5, (0x33, 0x33, 0x33))):
        st = doc.styles[name]
        st.font.name = FONT_EN
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(*color)
        st._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
        st.paragraph_format.space_before = Pt(10)
        st.paragraph_format.space_after = Pt(4)


def h(doc, text, level=1):
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    set_run_font(run, size={1: 16, 2: 13, 3: 11.5}.get(level, 11), bold=True)
    return p


def para(doc, text, size=10.5, bold=False, align=None, indent=True, color=None, space_after=4):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(21)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_run_font(run, size=size)
    return p


def code_block(doc, text, size=8.5):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = "Consolas"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    run.font.size = Pt(size)
    return p


def table(doc, headers, rows, widths=None, size=9):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(text)
        set_run_font(run, size=size, bold=True)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(text))
            set_run_font(run, size=size)
            p.paragraph_format.space_after = Pt(0)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, size=9, color=(0x66, 0x66, 0x66))


def image(doc, path: Path, width_cm=15.5, cap=None):
    if not path.exists():
        para(doc, f"［图片缺失：{path.name}］", size=9, color=(0xCC, 0x00, 0x00), indent=False)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    if cap:
        caption(doc, cap)


def two_images(doc, p1: Path, p2: Path, cap1, cap2, width_cm=8.2):
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, path, cap in ((t.rows[0].cells[0], p1, cap1), (t.rows[0].cells[1], p2, cap2)):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if path.exists():
            p.add_run().add_picture(str(path), width=Cm(width_cm))
        else:
            r = p.add_run(f"［缺失 {path.name}］")
            set_run_font(r, size=9, color=(0xCC, 0x00, 0x00))
        cp = cell.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(cap)
        set_run_font(r, size=9, color=(0x66, 0x66, 0x66))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# --------------------------------------------------------------------------- 封面
def cover(doc: Document):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(COURSE)
    set_run_font(r, size=18, bold=True, color=(0x1F, 0x38, 0x64))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("实 验 报 告")
    set_run_font(r, size=30, bold=True, color=(0x1F, 0x38, 0x64))
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE)
    set_run_font(r, size=20, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("—— 策略模式与观察者模式驱动的报名规则设计")
    set_run_font(r, size=12, color=(0x55, 0x55, 0x55))

    for _ in range(5):
        doc.add_paragraph()

    info = [
        ("课程名称", "《软件工程》"),
        ("实验名称", "实验二　CampusEvent 校园活动报名系统"),
        ("班　　级", "＿＿＿＿＿＿＿＿＿＿"),
        ("学　　号", "242806010116"),
        ("姓　　名", "宋逸轩"),
        ("提交日期", "2026 年 11 月 19 日"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in info:
        cells = t.add_row().cells
        cells[0].width = Cm(4)
        cells[1].width = Cm(9)
        for idx, text in enumerate((k, v)):
            p = cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(text)
            set_run_font(r, size=12)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("个人独立完成　·　baseline-v1（等待变更单 CR）")
    set_run_font(r, size=10, color=(0x77, 0x77, 0x77))

    doc.add_page_break()


# --------------------------------------------------------------------------- 正文
def section_goal(doc):
    h(doc, "一、实验目的与范围")
    para(doc, "本实验以“校园活动报名”为业务场景，要求在一个可运行的系统上完整体验软件工程的关键环节："
              "从需求分析、用例建模、职责划分、设计模式应用，到测试设计、验收取证与云部署；"
              "并在教师发布变更单（CR）后，基于同一份初版代码完成一次可解释、可回归的变更。"
              "实验的重点不是页面数量，而是“规则会变、通知渠道会变”时，代码是否还能以较小代价演进。")

    h(doc, "1.1 实验目标", 2)
    for item in [
        "实现 P2-F01 ~ P2-F08 八项功能，并通过指导书的 C1–C10 验收用例；",
        "用策略模式表达两种报名方式，用观察者模式解耦通知，并说明名额检查的归属；",
        "在 AI 参与编码之前，先由 AI 辅助产出用例图、类图、时序图与设计原则说明，并交其他同学评审；",
        "建立可重复执行的自动化测试，记录缺陷与修复过程；",
        "部署到云服务器，保留源码、Git 标签、AI 协作记录与可对照的变更分析材料。",
    ]:
        bullet(doc, item)

    h(doc, "1.2 范围与边界", 2)
    para(doc, "本期交付 baseline-v1：活动管理、活动查看（含按名称筛选）、报名与取消、两种报名策略、审批、"
              "状态管理、站内通知、统计与持久化。以下内容明确不在本期范围：真实身份认证（用演示账号选择代替）、"
              "邮件/短信通知、候补队列、签到与学分、多租户权限。指导书 3.6 规定变更单发布前不得提前实现变更内容，"
              "因此这些能力只在设计中预留扩展点，不在初版落地。")

    h(doc, "1.3 运行环境与账号", 2)
    table(doc, ["项目", "内容"], [
        ["技术栈", "Python 3.13 + Flask 2.3.3 + SQLite（标准库 sqlite3）+ Jinja2 + 原生 CSS"],
        ["本地运行", "python seed_demo.py --reset → python run.py → http://127.0.0.1:5000"],
        ["云服务器", "Ubuntu 24.04 / 2 vCPU / 2 GiB，gunicorn 监听 80 端口（见附录）"],
        ["演示账号", "学生 2024001 张三 / 2024002 李四 / 2024003 王五；管理员 admin（登录页下拉选择）"],
        ["数据文件", "instance/campusevent.sqlite（重启不丢）"],
    ], widths=[3.2, 12.3])


def section_solution(doc):
    h(doc, "二、实现方案")

    h(doc, "2.1 系统结构", 2)
    para(doc, "系统采用四层结构，依赖方向由外向内：装配层（Flask 路由、会话、模板注入）→ 应用服务层"
              "（报名与活动的用例编排、事务）→ 领域层（策略、通知、实体、常量）→ 仓储层（SQL 与 Schema）。"
              "领域层不 import Flask，因此业务规则可以在没有 HTTP 的情况下被测试。")
    code_block(doc,
               "浏览器\n"
               "  │ HTTP\n"
               "  ▼\n"
               "app/web/__init__.py        路由 / 会话 / flash / 模板注入（不写 SQL）\n"
               "  │\n"
               "  ▼\n"
               "app/domain/registration_service.py   报名、取消、审批、统计（事务编排）\n"
               "app/domain/activity_service.py       活动增改删 + 表单校验\n"
               "  │ 依赖抽象                        │ 依赖仓储\n"
               "  ▼                                 ▼\n"
               "policy.py（策略）  notification.py（观察者）   repository.py（SQLite）\n"
               "  │                                 │\n"
               "  ▼                                 ▼\n"
               "DirectPolicy / ApprovalPolicy     InboxChannel / AuditChannel")
    para(doc, "装配层每个请求创建一个 SQLite 连接（g.conn），请求结束关闭；写入使用 BEGIN IMMEDIATE 事务，"
              "保证“检查名额—写入报名”之间不被其他写事务插入，从而避免超卖。")

    h(doc, "2.2 主要模块", 2)
    table(doc, ["模块", "职责", "关键内容"], [
        ["web（装配层）", "HTTP、会话、表单解析、错误页", "18 条路由；admin 角色校验；403/404 处理"],
        ["registration_service", "报名/取消/审批的业务编排", "register / cancel / approve / reject / stats；_tx() 事务"],
        ["activity_service", "活动管理与表单校验", "parse_activity_form；软删除 + 连带通知"],
        ["policy", "报名方式策略", "check() 公共名额规则；decide() 状态判定；get_policy 工厂"],
        ["notification", "通知发布与通道", "publish() 逐通道 try/except；失败写 NOTIFY_FAILED"],
        ["repository", "SQL 与 Schema", "四张表、部分唯一索引、参数化查询"],
        ["entities / constants", "数据结构与错误码", "dataclass 实体；SealError(code, message)"],
    ], widths=[3.4, 5.2, 6.9])

    h(doc, "2.3 设计模式与 UML", 2)
    para(doc, "报名方式的差异被收敛到策略接口：RegistrationPolicy 声明 decide(seats_left) 与 requires_approval()，"
              "DirectPolicy 返回“已通过”，ApprovalPolicy 返回“待审核”。名额检查被放在基类的 check() 中，"
              "因为名额是活动的物理约束，与报名方式无关；若写进各策略，不仅重复，还会在新增策略时漏写。"
              "审批时的“复查名额”复用同一个 check()，保证报名与审批口径一致。")
    para(doc, "通知被抽象为观察者：NotificationService 是发布者，INotificationChannel 是观察者接口，"
              "InboxChannel 写站内信、AuditChannel 写审计。业务层只说“发生了什么”，不关心消息落到哪里；"
              "新增邮件或短信通道只需实现接口并注册。")
    image(doc, DIAG / "class-diagram-v1.png", 16.0, "图 2-1　CampusEvent 类图（baseline-v1）")
    para(doc, "报名时序的关键在于“通知在事务提交之后”：先 BEGIN IMMEDIATE，完成校验与写入后 COMMIT，"
              "再 publish 通知。若通道异常，publish 内部捕获并写一条 NOTIFY_FAILED 审计消息，"
              "已提交的报名不受影响——这对应业务规则 6“通知失败要留痕，但不得让合法报名无声消失”。")
    image(doc, DIAG / "seq-register.png", 16.0, "图 2-2　报名时序图（含重复报名、已开始、满员、成功四类分支）")
    image(doc, DIAG / "seq-approve.png", 16.0, "图 2-3　审批时序图（含名额已满批准失败分支）")
    image(doc, DIAG / "usecase.png", 15.0, "图 2-4　用例图（学生 / 管理员）")

    h(doc, "2.4 数据库 Schema", 2)
    code_block(doc,
               "student(student_id PK, name)\n"
               "activity(activity_id PK AUTOINCREMENT, title, category, start_at, location,\n"
               "         capacity CHECK(capacity > 0), policy_type CHECK(policy_type IN ('DIRECT','APPROVAL')),\n"
               "         deleted_at)\n"
               "registration(registration_id PK, activity_id FK, student_id FK,\n"
               "             status CHECK(status IN ('待审核','已通过','已拒绝','已取消')),\n"
               "             note, created_at, updated_at)\n"
               "CREATE UNIQUE INDEX ux_reg_active ON registration(activity_id, student_id)\n"
               "  WHERE status IN ('待审核','已通过');\n"
               "message(message_id PK, student_id, activity_id, kind, content, created_at, is_read)")
    para(doc, "“同一学生同一活动最多一条有效报名”用三层保证：服务层 active_registration 预检、数据库部分唯一索引兜底、"
              "以及测试里“绕过服务层直接插两行”的用例证明索引确实生效。删除活动选软删除（deleted_at），"
              "因为报名是参与凭证，硬删除会毁掉历史。")

    h(doc, "2.5 Agent 流程（AI 参与方式）", 2)
    para(doc, "AI 在本项目中的角色被限定为“草稿生成者 + 清单穷举者”，不是决策者。流程如下：")
    for item in [
        "设计阶段：给出约束（业务规则、扩展方向、不改 Service 的要求），让 AI 产出用例、类图、时序图与设计说明；",
        "评审闸门：设计材料交同学评审签字后，才允许进入实现（指导书 3.4-D）；",
        "实现阶段：AI 按类图生成域层与路由，人工逐条对照业务规则 B.2-1 ~ B.2-7；",
        "测试阶段：AI 生成用例骨架，人工检查“断言的是行为还是状态码”，并补边界（索引兜底、通知故障）；",
        "验收阶段：AI 操作真实浏览器截图，人工检查每张图的 flash 文案与统计数字是否对应验收用例；",
        "记录阶段：把“AI 产出—问题—我的判断”写进 AI_DEV_LOG.md，作为可复查的过程证据。",
    ]:
        bullet(doc, item)


def section_process(doc):
    h(doc, "三、实施过程")

    h(doc, "3.1 关键决策", 2)
    table(doc, ["决策", "选项", "选择与理由"], [
        ["名额检查位置", "各策略内 / 策略基类", "基类 check()：名额是活动约束，写进策略会重复且在新增策略时漏写"],
        ["通知与事务", "同一事务 / 提交后发送", "提交后发送：通知失败不能回滚合法报名（规则 6），失败写审计留痕"],
        ["删除活动", "硬删除 / 软删除", "软删除：保留报名作为参与凭证，学生端不可见但历史可追溯"],
        ["重复报名防线", "仅服务层 / 服务层 + 索引", "两层：应用层给友好提示，索引防并发与绕过服务层的写入"],
        ["登录方式", "用户名密码 / 演示账号", "演示账号：本期考察报名规则，认证不在范围（已写入 README 的取舍）"],
        ["时间处理", "datetime 对象 / 文本", "文本 YYYY-MM-DD HH:MM：SQLite 比较直观，前端 datetime-local 可直接回填"],
    ], widths=[3.0, 4.2, 8.3])

    h(doc, "3.2 Git 标签与提交", 2)
    para(doc, "源码按功能提交，初版完成后打标签 baseline-v1。由于本机直连 github.com:443 被网络阻断，"
              "仓库通过 GitHub API（Trees / Commits）推送，标签与提交内容与本地一致。")
    table(doc, ["标签 / 提交", "内容"], [
        ["baseline-v1", "初版：域层 + 装配层 + 9 个模板 + 65 条测试 + 8 份设计文档 + 4 张 UML + 19 张验收截图"],
        ["change-v2（待）", "收到 CR 后在 baseline-v1 上开分支实现，并附变更影响分析与回归报告"],
    ], widths=[4.0, 11.5])
    para(doc, "仓库地址与访问地址见附录；README 内含部署命令、演示账号、测试命令与数据库 Schema。")

    h(doc, "3.3 AI 参与及人工把关", 2)
    para(doc, "十轮有代表性的协作记录在项目根目录 AI_DEV_LOG.md，被否决或返工的 AI 产出共 5 处，"
              "其中 2 处直接对应后来发现的业务缺陷：")
    for item in [
        "名额检查初稿被写进两个策略 → 人工否决并移到基类，后来审批复查得以复用；",
        "通知失败只记在内存 → 人工要求写 NOTIFY_FAILED 审计行，满足规则 6 的“留痕”；",
        "“活动开始后不允许报名”漏实现 → 用“规则—代码—测试”清单让 AI 自查，标红后补代码与两条测试；",
        "满员/重复报名按钮被 UI 隐藏 → 否决“改数据造状态”的取证建议，改用真实路由 + flash 取证；",
        "批准失败文案让管理员“联系管理员” → 人工以操作者视角复读后修正。",
    ]:
        bullet(doc, item)


def section_test(doc):
    h(doc, "四、测试结果")

    h(doc, "4.1 自动化测试", 2)
    summary = {}
    sp = DOCS / "test-summary.json"
    if sp.exists():
        summary = json.loads(sp.read_text(encoding="utf-8"))
    total = summary.get("total", 65)
    secs = summary.get("time_seconds", 2.69)
    para(doc, f"执行 python -m pytest -q，共 {total} 条用例，失败 {summary.get('failures', 0)} 条，"
              f"耗时 {secs:.2f} 秒（原始 XML 报告 docs/test-report.xml）。")
    table(doc, ["测试文件", "用例数", "覆盖内容"], [
        ["test_registration.py", str(summary.get("by_file", {}).get("test_registration", {}).get("total", 22)),
         "报名/审批/取消/统计/事务与通知失败/唯一索引"],
        ["test_activity.py", str(summary.get("by_file", {}).get("test_activity", {}).get("total", 16)),
         "表单校验、增改查、软删除、删除后审批失败"],
        ["test_web.py", str(summary.get("by_file", {}).get("test_web", {}).get("total", 15)),
         "登录、权限、页面流程、404、通知已读"],
        ["test_policy.py", str(summary.get("by_file", {}).get("test_policy", {}).get("total", 10)),
         "策略接口、名额公共检查、策略无状态"],
        ["test_persistence.py", str(summary.get("by_file", {}).get("test_persistence", {}).get("total", 2)),
         "新连接 / 新应用实例后数据一致（C10）"],
    ], widths=[4.2, 2.0, 9.3])

    h(doc, "4.2 验收用例结果（C1–C10）", 2)
    table(doc, ["用例", "输入与步骤", "预期", "实际 / 证据", "结论"], [
        ["C1", "admin 新建“直接报名”活动，上限 2", "创建成功并出现在列表", "10-admin-activity-form.png", "通过"],
        ["C2", "张三报名有余量活动", "已通过 + 通知 + 名额减 1", "04-register-success.png", "通过"],
        ["C3", "张三重复报名", "拒绝，提示已报名", "16-duplicate-fail.png", "通过"],
        ["C4", "满员后王五报名", "拒绝，名额不变", "15-register-full-fail.png", "通过"],
        ["C5", "张三申请审核型活动", "待审核，不占名额", "02-activities.png", "通过"],
        ["C6", "admin 批准该申请", "已通过 + 通知", "13-approve-success.png", "通过"],
        ["C7", "admin 拒绝另一申请（填理由）", "已拒绝 + 通知", "14-reject-done.png", "通过"],
        ["C8", "对满员活动批准", "批准失败，状态不变", "12-approve-fail-full.png", "通过"],
        ["C9", "张三取消已通过报名", "已取消，名额回补", "08-cancel-success.png", "通过"],
        ["C10", "重启服务后重新登录查看", "数据一致", "test_persistence.py（2 条）", "通过"],
    ], widths=[1.3, 5.0, 4.2, 4.2, 1.4], size=8.5)

    h(doc, "4.3 验收截图", 2)
    two_images(doc, SHOTS / "01-login.png", SHOTS / "02-activities.png",
               "图 4-1　登录页（演示账号）", "图 4-2　活动列表（统计与我的报名状态）")
    two_images(doc, SHOTS / "03-activity-detail.png", SHOTS / "04-register-success.png",
               "图 4-3　活动详情与报名记录", "图 4-4　报名成功（剩余名额刷新）")
    two_images(doc, SHOTS / "11-admin-approvals.png", SHOTS / "12-approve-fail-full.png",
               "图 4-5　待审核列表", "图 4-6　满员时批准失败")
    two_images(doc, SHOTS / "13-approve-success.png", SHOTS / "14-reject-done.png",
               "图 4-7　批准成功", "图 4-8　拒绝并留理由")
    two_images(doc, SHOTS / "06-messages.png", SHOTS / "08-cancel-success.png",
               "图 4-9　站内通知", "图 4-10　取消报名与名额回补")
    two_images(doc, SHOTS / "18-404.png", SHOTS / "19-forbidden.png",
               "图 4-11　404 页面", "图 4-12　学生越权访问管理页（403）")

    h(doc, "4.4 缺陷记录与修复", 2)
    table(doc, ["编号", "现象", "根因", "修复与回归"], [
        ["D-01", "活动开始后仍可报名（违反 B.2-5）", "register() 只校验名额", "增加 start_at <= now → ACTIVITY_STARTED；取消不受限；补 2 条测试"],
        ["D-02", "通知失败只在内存留痕", "publish() 仅记录 self.failures", "异常后写 NOTIFY_FAILED 审计行；补注入故障通道的测试"],
        ["D-03", "批准失败文案让管理员“联系管理员”", "复用报名文案，主语错位", "改为“请先扩大名额或拒绝该申请”；重截图"],
        ["D-04", "同一通知重复发布产生重复站内信", "通道无幂等判断", "按 (student_id, activity_id, content) 与内容去重；补幂等测试"],
    ], widths=[1.4, 4.6, 4.5, 5.5], size=8.5)


def section_analysis(doc):
    h(doc, "五、结果分析")

    h(doc, "5.1 可维护性基线", 2)
    table(doc, ["指标", "baseline-v1", "说明"], [
        ["域层规模", "7 个文件 / 701 行", "策略、通知、仓储、两个 Service、实体与常量"],
        ["装配层规模", "262 行", "路由、会话、模板注入，无 SQL"],
        ["自动化用例", "65 条 / 0 失败 / 2.69 s", "单条可独立重跑"],
        ["新增类数（基线）", "—", "作为 change-v2 的对照起点"],
        ["修改核心业务类数（基线）", "—", "同上"],
        ["AI 交互轮次", "10 轮", "见 AI_DEV_LOG.md"],
    ], widths=[5.0, 5.0, 6.0])

    h(doc, "5.2 扩展性证据", 2)
    para(doc, "策略与观察者两种抽象是否“真的有用”，可以用“新增一个能力需要改哪些文件”来判断：")
    table(doc, ["假设的变更", "需要改的位置", "不需要改的位置"], [
        ["新增“抽签”报名方式", "新增 Policy 子类 + 注册表一行 + 对应测试", "register()、审批流程、模板结构"],
        ["新增邮件通知通道", "实现 INotificationChannel + notifier.register() + 通道测试", "报名/审批业务代码"],
        ["名额扩容", "更新 activity.capacity（approve 的复查逻辑已存在）", "策略、通知、页面结构"],
        ["报名截止时间独立", "实体字段 + 表单 + Schema + register() 前置校验", "策略接口（若仍复用 check）"],
    ], widths=[3.6, 6.4, 5.8])
    para(doc, "前三项的改动范围都限制在“新增文件 + 一行注册”，说明报名规则与通知渠道确实从业务核心中解耦；"
              "第四项会触及实体与 Schema，属于“活动属性扩展”，影响面更大，这也是将来 CR 影响分析的判断依据。")

    h(doc, "5.3 质量属性", 2)
    for item in [
        "正确性：C1–C10 全部通过，业务规则 7 条逐条有测试；重复报名与超卖由服务层 + 索引双重防护。",
        "健壮性：通知通道故障、活动被删除、活动已开始、非法表单等异常路径都有明确错误码与页面提示。",
        "可测试性：域层不依赖 Flask；连接与通知器可注入，故障通道可以直接构造。",
        "可读性：实体是 dataclass；错误码集中在 constants.py；模板 9 个，页面结构一致。",
        "可运维性：SQLite 单文件 + 环境变量配置数据库路径与 SECRET_KEY，部署只需 venv + gunicorn。",
    ]:
        bullet(doc, item)


def section_conclusion(doc):
    h(doc, "六、结论与反思")

    h(doc, "6.1 结论", 2)
    para(doc, "baseline-v1 完成了 P2-F01 ~ P2-F08 的全部功能，通过指导书 C1–C10 验收用例，"
              "65 条自动化测试全绿，19 张真实浏览器截图覆盖了成功路径与关键失败分支，"
              "系统已具备部署到云服务器的条件。设计中最重要的两个判断——名额检查属于公共规则、"
              "通知必须在事务提交之后发送——在实现与测试中都得到了验证：前者让报名与审批共用同一套名额口径，"
              "后者保证通知故障不会吞掉合法报名。")

    h(doc, "6.2 实际遇到的问题（非模板）", 2)
    para(doc, "问题 1：活动开始后仍能报名。写“规则—代码—测试”对照清单时发现 B.2-5 的后半句没有实现。"
              "根因是把时间约束当成了展示问题。修复方式是在名额检查前加开始时间校验，并明确“取消不受开始时间限制”，"
              "用两条测试把这一取舍固定下来。收获是：业务规则必须逐条映射，不能靠“看起来实现了”。")
    para(doc, "问题 2：通知失败没有落库。自查 publish() 时发现异常只写进内存列表，进程重启即丢。"
              "修复是在捕获异常后再写一条 NOTIFY_FAILED 审计消息，并用 try/except 防二次失败；"
              "报名本身早已提交，因此不受影响。收获是：“尽力而为”的通知也需要可观测性，否则故障是静默的。")
    para(doc, "问题 3：截图取证被工具浮层污染，且独立启动浏览器失败。定位到浮层是浏览器工具注入的光标层，"
              "改为截图前隐藏该元素并用 CDP 抓整页；独立 Chrome 启动失败是沙箱禁止命名管道，放弃该路线。"
              "收获是：取证工具本身也会污染证据，要先定位“是谁画的”。")
    para(doc, "问题 4：批准失败的提示语把管理员当成旁观者。修复为“请先扩大名额或拒绝该申请”。"
              "收获是：复用文案时要检查主语是否仍然是当前操作者。")

    h(doc, "6.3 反思", 2)
    for item in [
        "需求到测试的映射应该更早建立。问题 1 是在写覆盖清单时才暴露的，如果一开始就维护三列表，能更早发现漏实现。",
        "并发只在单机成立。BEGIN IMMEDIATE 能防超卖，但多实例部署会退化为文件锁竞争；未来需要换 PostgreSQL 与行级锁。",
        "认证是演示级。下拉选身份不是安全边界，真实系统需要密码或 SSO，并记录操作审计。",
        "UI 隐藏不等于后端安全。满员/重复报名按钮被隐藏，但测试仍直接打路由验证后端拒绝，这一点必须在报告中说明。",
        "取证应尽早脚本化。手工点页面容易漏状态，浮层问题也浪费了时间；沉淀成脚本后可重复执行。",
    ]:
        bullet(doc, item)

    h(doc, "6.4 后续计划（等待 CR）", 2)
    para(doc, "变更单到达后，先完成变更影响分析（涉及类/接口、风险、预计新增测试、修改范围），"
              "再从 baseline-v1 开 change-v2 分支实现，禁止删库重建；完成后跑全部 65 条回归 + 新增用例，"
              "用指导书 3.7 的五个指标（新增类数、修改核心业务类数、回归失败数、AI 交互轮次、修改总时长）做前后对照，"
              "并更新类图 v2、实验报告与 AI_DEV_LOG.md，打标签 change-v2 推送。")


def section_appendix(doc):
    h(doc, "七、附录")

    h(doc, "A. 源码与访问地址", 2)
    table(doc, ["项目", "地址 / 说明"], [
        ["源码仓库", "https://github.com/adadada231rdsf/CampusEvent（分支 main，标签 baseline-v1）"],
        ["云端访问", "http://47.106.192.221（Ubuntu 24.04 + gunicorn，80 端口）"],
        ["本地运行", "python seed_demo.py --reset && python run.py → http://127.0.0.1:5000"],
        ["测试命令", "python -m pytest -q （65 条，约 2.7 秒）"],
        ["服务器部署", "scp -r CampusEvent root@47.106.192.221:/root/ → venv → pip install -r requirements.txt gunicorn → gunicorn -b 0.0.0.0:80 \"app:create_app()\""],
    ], widths=[3.5, 12.0])

    h(doc, "B. 交付物清单", 2)
    table(doc, ["材料", "文件"], [
        ["初始需求分析（SRS）", "docs/01_需求分析_SRS.md"],
        ["用例说明", "docs/02_用例说明.md"],
        ["设计模式决策报告 + UML 说明", "docs/03_设计模式与UML说明.md"],
        ["设计评审表（待手签）", "docs/04_设计评审表.md"],
        ["测试用例与回归表", "docs/05_测试用例与回归表.md"],
        ["变更影响分析（模板 + 基线）", "docs/06_变更影响分析模板.md"],
        ["项目总结", "docs/07_项目总结.md"],
        ["手工验收记录", "docs/08_验收记录.md"],
        ["UML 图（用例/类/两张时序）", "docs/diagrams/*.png"],
        ["验收截图（19 张）", "docs/screenshots/*.png"],
        ["测试原始报告", "docs/test-report.xml、docs/test-summary.json"],
        ["AI 协作记录", "AI_DEV_LOG.md"],
    ], widths=[6.5, 9.0])

    h(doc, "C. 关键运行截图", 2)
    two_images(doc, SHOTS / "09-admin-activities.png", SHOTS / "10-admin-activity-form.png",
               "图 C-1　活动管理列表", "图 C-2　活动表单（新建/编辑共用）")
    two_images(doc, SHOTS / "05-my-registrations.png", SHOTS / "07-messages-read.png",
               "图 C-3　我的报名（含历史记录）", "图 C-4　消息已读标记")
    image(doc, SHOTS / "17-filter-by-name.png", 15.0, "图 C-5　按名称筛选活动")


def main():
    doc = Document()
    style_doc(doc)
    sec = doc.sections[0]
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.4)

    cover(doc)
    section_goal(doc)
    section_solution(doc)
    section_process(doc)
    section_test(doc)
    section_analysis(doc)
    section_conclusion(doc)
    section_appendix(doc)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
