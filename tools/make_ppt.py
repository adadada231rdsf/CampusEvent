# -*- coding: utf-8 -*-
"""生成《实验二 CampusEvent》演示 PPT（16:9，15 页）。

与实验一 PPT 保持同一套视觉语言：浅灰底 + 深蓝主色 + 橙红点缀，微软雅黑。

    C:\\Users\\alice\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe tools\\make_ppt.py
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "实验二_演示_宋逸轩.pptx"

FONT = "微软雅黑"
BG = RGBColor(0xF7, 0xF8, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1F, 0x23, 0x28)
MUTED = RGBColor(0x6B, 0x72, 0x80)
PRIMARY = RGBColor(0x1A, 0x5C, 0x8A)
ACCENT = RGBColor(0xC8, 0x4B, 0x31)
LINE = RGBColor(0xDD, 0xE2, 0xE8)
CARD = RGBColor(0xFF, 0xFF, 0xFF)

W, H = Inches(13.333), Inches(7.5)


# ------------------------------------------------------------------ 基础绘制
def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    return prs


def blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    return sh


def text(slide, x, y, w, h, runs, size=16, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.25, space_after=4):
    """runs: 字符串（按 \n 分段）或 list，元素为 (文字, dict(覆盖属性))。"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    if isinstance(runs, str):
        runs = [(line, {}) for line in runs.split("\n")]
    for idx, item in enumerate(runs):
        body, over = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = over.get("align", align)
        p.line_spacing = over.get("spacing", spacing)
        p.space_after = Pt(over.get("space_after", space_after))
        run = p.add_run()
        run.text = body
        f = run.font
        f.name = FONT
        f.size = Pt(over.get("size", size))
        f.bold = over.get("bold", bold)
        f.color.rgb = over.get("color", color)
    return box


def page(prs, kicker, title, number, bg=WHITE):
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, fill=bg)
    rect(s, 0.75, 0.62, 0.09, 0.5, fill=PRIMARY)
    text(s, 1.0, 0.6, 10.5, 0.4, kicker, size=12, color=PRIMARY, bold=True)
    text(s, 1.0, 0.92, 11.0, 0.6, title, size=28, bold=True)
    text(s, 12.15, 0.78, 0.55, 0.4, number, size=13, color=RGBColor(0xB9, 0xC2, 0xCC), bold=True)
    rect(s, 0.75, 1.62, 11.83, 0.01, fill=LINE)
    return s


def card(slide, x, y, w, h, top_color=PRIMARY, fill=CARD):
    rect(slide, x, y, w, h, fill=fill, line=LINE)
    rect(slide, x, y, w, 0.06, fill=top_color)


def image_fit(slide, path: Path, x, y, w, h, caption=None):
    from PIL import Image

    with Image.open(path) as im:
        iw, ih = im.size
    ratio = iw / ih
    box_ratio = w / h
    if ratio >= box_ratio:
        dw, dh = w, w / ratio
    else:
        dh, dw = h, h * ratio
    left = x + (w - dw) / 2
    top = y + (h - dh) / 2
    slide.shapes.add_picture(str(path), Inches(left), Inches(top), Inches(dw), Inches(dh))
    if caption:
        text(slide, x, y + h + 0.08, w, 0.3, caption, size=11, color=MUTED, align=PP_ALIGN.CENTER)


# ------------------------------------------------------------------ 各页
def slide_cover(prs):
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, fill=BG)
    rect(s, 0, 0, 0.28, 7.5, fill=PRIMARY)
    text(s, 1.5, 1.85, 10.0, 0.45, "软件工程实验二", size=18, color=PRIMARY, bold=True)
    text(s, 1.5, 2.4, 10.6, 2.05, [
        ("CampusEvent 校园活动报名系统", {"size": 44, "bold": True, "color": INK, "space_after": 2}),
        ("策略模式 + 观察者模式　·　名额与通知的事务边界", {"size": 22, "bold": True, "color": PRIMARY}),
    ])
    rect(s, 1.5, 4.3, 1.6, 0.035, fill=ACCENT)
    text(s, 1.5, 4.7, 10.5, 1.0, [
        ("Python · Flask · SQLite　｜　P2-F01 ~ P2-F08　｜　65 条测试全通过", {"size": 16, "color": MUTED}),
        ("计科一班　242806010116　宋逸轩", {"size": 16, "color": INK, "bold": True, "space_after": 0}),
    ])
    text(s, 10.3, 6.75, 2.4, 0.35, "2026.11.19", size=12, color=RGBColor(0x9A, 0xA4, 0xB0), align=PP_ALIGN.RIGHT)


def slide_overview(prs):
    s = page(prs, "OVERVIEW", "项目概览", "02")
    stats = [
        ("8", "项功能需求", "P2-F01 ~ P2-F08 全部实现\n并通过 10 个验收用例", PRIMARY),
        ("2", "个设计模式", "策略模式管报名规则\n观察者模式管通知", ACCENT),
        ("65", "条自动化测试", "pytest 2.7 秒跑完\n0 失败 0 跳过", PRIMARY),
        ("20", "张验收截图", "C1–C10 真实浏览器取证\n含云端部署实例", PRIMARY),
    ]
    for i, (num, label, desc, color) in enumerate(stats):
        x = 0.75 + i * 3.05
        card(s, x, 2.0, 2.85, 2.05, top_color=color)
        text(s, x + 0.25, 2.22, 2.35, 0.72, num, size=40, color=PRIMARY, bold=True, spacing=1.0)
        text(s, x + 0.25, 2.95, 2.35, 0.32, label, size=16, bold=True)
        text(s, x + 0.25, 3.33, 2.42, 0.72, desc, size=11, color=MUTED, spacing=1.2)
    text(s, 0.75, 4.5, 11.8, 2.3, [
        ("要解决的问题", {"size": 17, "bold": True, "color": PRIMARY}),
        ("—　同一个活动，报名方式不同：有的提交即通过，有的要管理员审核；审核期间名额怎么算、取消了能不能再报，规则一乱就会超卖。", {"size": 14.5}),
        ("·　目标：活动管理 → 学生报名 → 审批 → 站内通知 → 统计口径，全流程闭环，且名额只按「已通过」计。", {"size": 14.5, "color": INK}),
        ("—　范围：本期做单机 Flask + SQLite，登录用演示账号；指导书 3.6 要求等老师发 CR 后再做变更版。", {"size": 14.5, "color": MUTED}),
    ])


def slide_rules(prs):
    s = page(prs, "BUSINESS RULES", "先定规则，再谈设计：B.2 七条与四种状态", "03")
    text(s, 0.75, 1.95, 5.6, 4.8, [
        ("状态机", {"size": 16, "bold": True, "color": PRIMARY}),
        ("待审核 ──批准──▶ 已通过 ──取消──▶ 已取消", {"size": 13, "color": INK}),
        ("　　└──拒绝──▶ 已拒绝　　　已取消 / 已拒绝保留历史，可再次申请", {"size": 12, "color": MUTED}),
        ("名额口径", {"size": 16, "bold": True, "color": PRIMARY, "space_after": 2}),
        ("只按「已通过」计数：待审核不占名额，但满员后不得再批准；", {"size": 13}),
        ("数据库用部分唯一索引兜底——同一学生同一活动最多一条活跃记录。", {"size": 13}),
        ("七条硬约束", {"size": 16, "bold": True, "color": PRIMARY, "space_after": 2}),
        ("1 直接报名名额足 → 已通过 + 通知　　2 审核型 → 待审核，批准时再查名额", {"size": 13}),
        ("3 满员不得批准　　4 无重复活跃报名　　5 开始后不再允许新增报名", {"size": 13}),
        ("6 通知失败要留痕，但不能吞掉合法报名　　7 删除活动走软删除", {"size": 13}),
    ])
    card(s, 6.75, 1.95, 5.85, 2.55, top_color=ACCENT)
    text(s, 7.0, 2.15, 5.35, 2.2, [
        ("规则 6 是设计的分水岭", {"size": 15, "bold": True, "color": ACCENT}),
        ("「通知失败不能导致合法报名消失」意味着通知不能和报名写在同一个事务里：", {"size": 12.5}),
        ("报名先 COMMIT，再发通知；通知通道异常只写 NOTIFY_FAILED 审计行，不回滚。", {"size": 12.5, "bold": True}),
        ("规则 7 选了软删除：活动在学生端消失，报名记录作为参与凭证保留。", {"size": 12.5, "color": MUTED}),
    ])
    card(s, 6.75, 4.7, 5.85, 2.05, top_color=PRIMARY)
    text(s, 7.0, 4.9, 5.35, 1.7, [
        ("为什么先写规则再写代码", {"size": 15, "bold": True, "color": PRIMARY}),
        ("七条规则逐条落到「规则 → 代码位置 → 测试函数」三列清单，写代码时对着勾；漏掉的规则 5 就是这样在自查里暴露的。", {"size": 12.5}),
    ])


def slide_arch(prs):
    s = page(prs, "ARCHITECTURE", "四层结构：路由只做转发，规则都在域层", "04")
    layers = [
        ("装配层　app/web/__init__.py", "Flask 路由 · 会话 · flash · 模板渲染 · 事务边界之外", 262),
        ("领域服务　registration_service.py", "报名 / 取消 / 审批 / 统计 · BEGIN IMMEDIATE 事务", 243),
        ("策略与通知　policy.py", "报名规则（策略） · 消息发布与通道（观察者）", 169),
        ("数据访问　repository.py", "全部 SQL 集中于此 · 参数化占位符 · 部分唯一索引", 215),
    ]
    for i, (name, desc, _lines) in enumerate(layers):
        y = 2.0 + i * 1.02
        rect(s, 0.85, y, 7.4, 0.82, fill=WHITE, line=LINE)
        rect(s, 0.85, y, 0.08, 0.82, fill=PRIMARY if i < 2 else ACCENT)
        text(s, 1.15, y + 0.1, 6.9, 0.3, name, size=14, bold=True)
        text(s, 1.15, y + 0.43, 6.9, 0.3, desc, size=11.5, color=MUTED)
        if i < 3:
            rect(s, 4.25, y + 0.84, 0.26, 0.16, fill=LINE, shape=MSO_SHAPE.DOWN_ARROW)
    card(s, 8.7, 2.0, 3.9, 4.25, top_color=ACCENT)
    text(s, 8.95, 2.2, 3.45, 3.9, [
        ("设计取舍", {"size": 15, "bold": True, "color": ACCENT}),
        ("·　路由不写 SQL、不写规则，改需求只动一处", {"size": 12.5}),
        ("·　不用 ORM：四张表，手写 SQL 更好审查", {"size": 12.5}),
        ("·　应用工厂 create_app(config)，测试注入临时库", {"size": 12.5}),
        ("·　域层不 import Flask，可脱离 Web 单测", {"size": 12.5}),
        ("·　7 个域模块 701 行，配 65 条测试", {"size": 12.5, "color": MUTED}),
    ])


def slide_policy(prs):
    s = page(prs, "PATTERN 1 · STRATEGY", "策略模式：报名方式决定「落哪个状态」", "05")
    rect(s, 0.75, 1.95, 5.9, 2.35, fill=RGBColor(0xF2, 0xF6, 0xFA), line=LINE)
    text(s, 0.95, 2.08, 5.5, 2.2, [
        ("class RegistrationPolicy(ABC):", {"size": 10.5, "color": MUTED}),
        ("    def check(self, *, seats_left, capacity):   # 公共规则", {"size": 10.5, "color": INK}),
        ("        if seats_left <= 0: raise SealError(…, \"CAPACITY_FULL\")", {"size": 10.5, "color": INK}),
        ("    @abstractmethod", {"size": 10.5, "color": MUTED}),
        ("    def decide(self, seats_left) -> str: …", {"size": 10.5, "color": INK}),
        ("    def requires_approval(self) -> bool: …", {"size": 10.5, "color": INK}),
        ("DirectPolicy → 已通过　　　ApprovalPolicy → 待审核", {"size": 10.5, "color": PRIMARY, "bold": True}),
    ], spacing=1.2, space_after=1)
    text(s, 0.75, 4.45, 5.9, 2.4, [
        ("新增一种报名方式时", {"size": 15, "bold": True, "color": PRIMARY}),
        ("只加一个子类 + 注册进 _POLICIES，Service 与路由一行都不用改——这是指导书「变更适应」部分要看的扩展点。", {"size": 13}),
    ])
    card(s, 6.95, 1.95, 5.65, 4.85, top_color=ACCENT)
    text(s, 7.2, 2.15, 5.15, 4.45, [
        ("名额检查到底属于谁？", {"size": 16, "bold": True, "color": ACCENT}),
        ("放进策略，看起来更「可插拔」，但代价是：", {"size": 12.5}),
        ("·　两个策略各写一遍，新策略容易漏写；", {"size": 12.5}),
        ("·　审批复查名额时还得再复制一次判断。", {"size": 12.5}),
        ("放基类 check() 的理由：", {"size": 12.5, "bold": True, "space_after": 2}),
        ("1　「名额满不能报」是活动约束，与报名方式无关；", {"size": 12.5}),
        ("2　报名与审批共用同一份判断，口径不会漂；", {"size": 12.5}),
        ("3　策略只回答「该落哪个状态」，职责单一；", {"size": 12.5}),
        ("4　新增策略不会因为漏写检查而超卖。", {"size": 12.5}),
        ("结论：公共规则上移基类，策略只保留差异。", {"size": 12.5, "bold": True, "color": ACCENT, "space_after": 0}),
    ])


def slide_observer(prs):
    s = page(prs, "PATTERN 2 · OBSERVER", "观察者模式：通知在事务提交之后", "06")
    steps = [
        ("① 报名写入", "BEGIN IMMEDIATE → insert registration → COMMIT", PRIMARY),
        ("② 组装消息", "Message(student, activity, content, kind)", PRIMARY),
        ("③ 逐个通道投递", "publish() 逐通道 try/except，互不影响", ACCENT),
        ("④ 失败留痕", "写 NOTIFY_FAILED 审计行，不回滚报名", ACCENT),
    ]
    for i, (title, desc, color) in enumerate(steps):
        x = 0.75 + i * 3.02
        card(s, x, 1.95, 2.82, 1.5, top_color=color)
        text(s, x + 0.2, 2.12, 2.45, 0.35, title, size=14, bold=True)
        text(s, x + 0.2, 2.5, 2.5, 0.85, desc, size=11, color=MUTED, spacing=1.2)
    text(s, 0.75, 3.7, 5.9, 3.1, [
        ("两个通道", {"size": 15, "bold": True, "color": PRIMARY}),
        ("InboxChannel　写 message 表，按（学生, 活动, 内容）幂等去重——重试不会重复打扰。", {"size": 12.5}),
        ("AuditChannel　写审计行，保留投递轨迹，失败也有据可查。", {"size": 12.5}),
        ("为什么拆通道", {"size": 15, "bold": True, "color": PRIMARY, "space_after": 2}),
        ("以后加短信/邮件只注册一个新通道，报名流程不动；", {"size": 12.5}),
        ("通道故障被隔离在 publish() 内部，不会冒泡成 500。", {"size": 12.5}),
    ])
    card(s, 6.95, 3.7, 5.65, 3.1, top_color=ACCENT)
    text(s, 7.2, 3.9, 5.15, 2.7, [
        ("通知失败会影响报名吗？", {"size": 15, "bold": True, "color": ACCENT}),
        ("不会。通知在 COMMIT 之后发送，失败只写审计行——这正是规则 6 要的「留痕但不吞单」。", {"size": 12.5}),
        ("同一事务内发送的版本被否决了：邮件服务抖一下，学生明明报名成功却看到报错，还会重复提交。", {"size": 12.5, "color": MUTED}),
        ("幂等去重解决「避免重复通知」：重试或重放只会命中同一条消息。", {"size": 12.5}),
    ])


def slide_diagram(prs, kicker, title, number, path, caption):
    s = page(prs, kicker, title, number)
    image_fit(s, path, 0.9, 1.8, 11.5, 5.1, caption)


def slide_data(prs):
    s = page(prs, "DATA MODEL", "四张表 + 一条部分唯一索引", "10")
    rect(s, 0.75, 1.95, 6.6, 4.55, fill=RGBColor(0xF2, 0xF6, 0xFA), line=LINE)
    text(s, 0.95, 2.1, 6.2, 4.25, [
        ("-- 活跃报名唯一性：唯一靠数据库兜底，不靠应用层自觉", {"size": 11, "color": MUTED}),
        ("CREATE UNIQUE INDEX ux_reg_active", {"size": 11.5}),
        ("  ON registration(activity_id, student_id)", {"size": 11.5}),
        ("  WHERE status IN ('待审核', '已通过');", {"size": 11.5}),
        ("", {"size": 8}),
        ("student(student_id PK, name)", {"size": 11.5, "color": PRIMARY}),
        ("activity(activity_id PK, title, category, start_at, location,", {"size": 11.5, "color": PRIMARY}),
        ("         capacity CHECK > 0, policy_type, deleted_at)", {"size": 11.5, "color": PRIMARY}),
        ("registration(registration_id PK, activity_id FK, student_id FK,", {"size": 11.5, "color": PRIMARY}),
        ("             status CHECK IN 四种状态, note, created_at, updated_at)", {"size": 11.5, "color": PRIMARY}),
        ("message(message_id PK, student_id, activity_id, kind, content, created_at, is_read)", {"size": 11.5, "color": PRIMARY}),
    ], spacing=1.4, space_after=1)
    card(s, 7.65, 1.95, 4.95, 2.2, top_color=PRIMARY)
    text(s, 7.9, 2.15, 4.45, 1.85, [
        ("为什么用部分索引", {"size": 14, "bold": True, "color": PRIMARY}),
        ("只约束「待审核 / 已通过」两态，已取消、已拒绝的历史记录不参与，所以被拒后还能重新申请。", {"size": 12}),
    ])
    card(s, 7.65, 4.35, 4.95, 2.15, top_color=ACCENT)
    text(s, 7.9, 4.55, 4.45, 1.8, [
        ("持久化与软删除", {"size": 14, "bold": True, "color": ACCENT}),
        ("SQLite 单文件随实例保存，重启不丢；删除活动只写 deleted_at，报名记录仍可追溯（规则 7）。", {"size": 12}),
    ])


def slide_test(prs):
    s = page(prs, "TESTING", "65 条自动化测试 + 10 个验收用例", "11")
    rows = [("文件", "覆盖内容", "用例数")] + [
        ("test_registration.py", "报名 / 取消 / 审批 / 名额 / 通知", "22"),
        ("test_activity.py", "表单校验 / 增改 / 软删除", "16"),
        ("test_web.py", "登录 / 权限 / 页面流程", "15"),
        ("test_policy.py", "两个策略与公共名额检查", "10"),
        ("test_persistence.py", "重启后数据一致（C10）", "2"),
    ]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.75), Inches(1.95), Inches(6.9), Inches(2.6)).table
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c == 1 else PP_ALIGN.CENTER
            for run in p.runs:
                run.font.name = FONT
                run.font.size = Pt(11 if r else 11.5)
                run.font.bold = r == 0
                run.font.color.rgb = WHITE if r == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = PRIMARY if r == 0 else (WHITE if r % 2 else RGBColor(0xF7, 0xF8, 0xFA))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    text(s, 0.75, 4.75, 6.9, 2.1, [
        ("断言的是行为，不是状态码", {"size": 14, "bold": True, "color": PRIMARY}),
        ("UI 把满员 / 重复报名的按钮藏了，但测试直接打路由，验证后端一定拒绝——隐藏按钮不等于安全边界。", {"size": 12}),
    ])
    card(s, 7.85, 1.95, 4.75, 2.4, top_color=ACCENT)
    text(s, 8.1, 2.15, 4.25, 2.05, [
        ("开发中自查出的问题", {"size": 14, "bold": True, "color": ACCENT}),
        ("1　活动开始后仍能报名（漏了规则 5）→ 补校验 + 2 条测试", {"size": 11.5}),
        ("2　通知失败只记内存 → 改写入 NOTIFY_FAILED 审计行", {"size": 11.5}),
        ("3　批准失败文案让管理员「联系管理员」→ 改主语", {"size": 11.5}),
    ])
    card(s, 7.85, 4.55, 4.75, 2.3, top_color=PRIMARY)
    text(s, 8.1, 4.75, 4.25, 1.95, [
        ("C1–C10 手工验收", {"size": 14, "bold": True, "color": PRIMARY}),
        ("10 个用例逐条在真实浏览器里跑，20 张截图留证；回归命令一条：python -m pytest -q。", {"size": 11.5}),
    ])


def slide_deploy(prs):
    s = page(prs, "DEPLOYMENT", "上云：与实验一共用一台服务器，占用 8080", "12")
    steps = [
        ("打包上传", "git archive 导出 HEAD\nscp 到 /root/ 并解压"),
        ("装依赖", "venv + 清华镜像\nrequirements + gunicorn"),
        ("systemd 托管", "campusevent.service\nRestart=always"),
        ("放行端口", "防火墙 TCP 8080\n0.0.0.0/0"),
    ]
    for i, (title, desc) in enumerate(steps):
        y = 1.95 + i * 1.02
        rect(s, 0.75, y, 4.3, 0.86, fill=WHITE, line=LINE)
        rect(s, 0.75, y, 0.06, 0.86, fill=PRIMARY)
        text(s, 0.95, y + 0.08, 3.95, 0.3, title, size=13, bold=True)
        text(s, 0.95, y + 0.4, 3.95, 0.42, desc, size=10.5, color=MUTED, spacing=1.15)
    text(s, 0.75, 6.15, 4.35, 0.55, "线上地址：http://47.106.192.221:8080", size=12, color=PRIMARY, bold=True)
    image_fit(s, DOCS / "screenshots" / "20-deployed-cloud.png", 5.35, 1.95, 7.25, 4.6,
              "云端实例：管理员登录后的活动管理页（真实截图）")


def slide_ai(prs):
    s = page(prs, "AI COLLABORATION", "11 轮协作，6 处被否决或返工", "13")
    items = [
        ("设计材料先出", "用例图 / 类图 / 两张时序图先评审再写代码（指导书 3.4-D）"),
        ("名额检查被改位", "AI 初稿写进两个策略 → 否决，移到基类 check()"),
        ("通知失败要留痕", "AI 只记内存 → 要求写 NOTIFY_FAILED 审计行"),
        ("规则 5 漏实现", "让 AI 自查「规则—代码—测试」清单才发现，已补"),
        ("取证方式被否决", "AI 想改数据造满员状态 → 改为真实路由 + flash 取证"),
        ("部署脚本 CRLF", "服务器报 set: pipefail → .gitattributes 强制 LF"),
    ]
    for i, (title, desc) in enumerate(items):
        col, row = i % 2, i // 2
        x = 0.75 + col * 6.05
        y = 1.95 + row * 1.5
        card(s, x, y, 5.8, 1.3, top_color=PRIMARY if i % 2 == 0 else ACCENT)
        text(s, x + 0.22, y + 0.13, 5.35, 0.3, title, size=13, bold=True)
        text(s, x + 0.22, y + 0.5, 5.4, 0.72, desc, size=11, color=MUTED, spacing=1.2)
    text(s, 0.75, 6.5, 11.8, 0.4,
         "完整记录见 AI_DEV_LOG.md：每条都写「我的判断」，验收看的是人有没有把关，而不是 AI 会不会写代码。",
         size=11, color=MUTED)


def slide_change(prs):
    s = page(prs, "CHANGE READINESS", "为变更留的门：改一处，而不是改一片", "14")
    rows = [("3.7 对照指标", "baseline-v1", "change-v2"),] + [
        ("新增类数", "7 个域模块 · 9 个业务类（策略 3 / 通道 4 / 服务 2）", "待 CR 后填"),
        ("修改的核心业务类数", "0（还没改）", "待填"),
        ("回归失败数", "0 / 65", "待填"),
        ("AI 交互轮次", "11 轮", "待填"),
        ("修改总时长", "—", "待填"),
    ]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.75), Inches(1.95), Inches(7.0), Inches(2.9)).table
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            for run in cell.text_frame.paragraphs[0].runs:
                run.font.name = FONT
                run.font.size = Pt(10.5 if c else 11)
                run.font.bold = r == 0
                run.font.color.rgb = WHITE if r == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = PRIMARY if r == 0 else (WHITE if r % 2 else RGBColor(0xF7, 0xF8, 0xFA))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    card(s, 8.05, 1.95, 4.55, 4.85, top_color=ACCENT)
    text(s, 8.3, 2.15, 4.05, 4.5, [
        ("已经预留的扩展点", {"size": 14, "bold": True, "color": ACCENT}),
        ("·　报名方式：加策略子类即可", {"size": 11.5}),
        ("·　通知渠道：注册新 channel", {"size": 11.5}),
        ("·　活动字段：加列 + 表单 + 校验", {"size": 11.5}),
        ("·　统计口径：stats() 一处集中", {"size": 11.5}),
        ("变更流程", {"size": 14, "bold": True, "color": ACCENT, "space_after": 2}),
        ("收到 CR → 先写影响分析（涉及类 / 风险 / 新增测试 / 修改范围）→ 从 baseline-v1 开 change-v2 分支 → 跑 65 条回归 + 新增用例 → 打标签。", {"size": 11.5}),
    ])


def slide_end(prs):
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, fill=RGBColor(0x14, 0x3E, 0x5C))
    text(s, 1.5, 2.2, 10.5, 0.85, "谢谢", size=40, color=WHITE, bold=True)
    text(s, 1.5, 3.0, 10.5, 0.45, "源代码 · 测试 · 设计文档 · 验收截图　全部可查", size=17, color=RGBColor(0xC7, 0xD6, 0xE2))
    rect(s, 1.5, 3.75, 1.6, 0.035, fill=ACCENT)
    text(s, 1.5, 4.1, 10.6, 1.5, [
        ("仓库　github.com/adadada231rdsf/CampusEvent　（main + 标签 baseline-v1）", {"size": 14, "color": WHITE}),
        ("在线　http://47.106.192.221:8080　（Ubuntu 24.04 + gunicorn + systemd）", {"size": 14, "color": WHITE}),
        ("计科一班　242806010116　宋逸轩", {"size": 14, "color": RGBColor(0xC7, 0xD6, 0xE2)}),
    ])


def main():
    prs = new_deck()
    slide_cover(prs)
    slide_overview(prs)
    slide_rules(prs)
    slide_arch(prs)
    slide_policy(prs)
    slide_observer(prs)
    slide_diagram(prs, "CLASS DIAGRAM", "类图：实体只带数据，规则在服务与策略里", "07",
                  DOCS / "diagrams" / "class-diagram-v1.png",
                  "图 1　CampusEvent 类图（baseline-v1）")
    slide_diagram(prs, "SEQUENCE · REGISTER", "报名时序：四条拒绝分支 + 提交后通知", "08",
                  DOCS / "diagrams" / "seq-register.png",
                  "图 2　报名时序图（直接报名 / 审核型两条分支）")
    slide_diagram(prs, "SEQUENCE · APPROVE", "审批时序：批准时再查一次名额", "09",
                  DOCS / "diagrams" / "seq-approve.png",
                  "图 3　审批时序图（满员批准失败，状态保持待审核）")
    slide_data(prs)
    slide_test(prs)
    slide_deploy(prs)
    slide_ai(prs)
    slide_change(prs)
    slide_end(prs)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"saved: {OUT}  slides={len(prs.slides)}")


if __name__ == "__main__":
    main()
