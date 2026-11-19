#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CampusEvent 实验二 UML 图生成脚本（纯 matplotlib 手绘，不依赖 graphviz / plantuml）。

一次运行生成 4 张 200dpi 白底 PNG：
    docs/diagrams/usecase.png            图 1 用例图（baseline-v1）
    docs/diagrams/class-diagram-v1.png   图 2 类图（baseline-v1）
    docs/diagrams/seq-register.png       图 3 报名时序图
    docs/diagrams/seq-approve.png        图 4 审批时序图

用法（cwd = CampusEvent 目录）：
    C:\\Users\\alice\\anaconda3\\python.exe tools\\diagrams.py

坐标约定：1 英寸 = 100 绘图单位；y 轴向下（与屏幕一致），单位是英寸的 1/100。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle
from matplotlib.textpath import TextPath

# ---------------------------------------------------------------- 全局设置
FONT = "Microsoft YaHei"
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False

# ①..⑩ 雅黑自带，⑪⑫ 缺字；追加 Segoe UI Symbol 做逐字形回退（雅黑仍为首选）。
FAMILIES = ["Microsoft YaHei", "Segoe UI Symbol"]

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "docs" / "diagrams"
DPI = 200
U = 100.0                      # 每英寸 100 单位

INK = "#1B2733"
NAVY = "#1F3B5C"
BLUE = "#2E5C8A"
FILL = "#E4EDF7"
FILL2 = "#F7FAFD"
FILL3 = "#F1F6FB"
ACTOR = "#FBF0DD"
ALT_EC = "#A9762F"
ALT_FC = "#FBF4E6"
NOTE_FC = "#FFFBEA"
NOTE_EC = "#C9A227"
RED = "#A63A2E"
GREY = "#5A6B7B"
LGREY = "#8A99A8"

PROBLEMS: list[str] = []


# ---------------------------------------------------------------- 文本度量
_FP: dict = {}


def _fp(size: float, weight: str = "normal", style: str = "normal") -> FontProperties:
    key = (size, weight, style)
    if key not in _FP:
        _FP[key] = FontProperties(family=FONT, size=size, weight=weight, style=style)
    return _FP[key]


def tw(text: str, size: float, weight: str = "normal", style: str = "normal") -> float:
    """文本宽度（绘图单位）。"""
    if not text:
        return 0.0
    bb = TextPath((0, 0), text, prop=_fp(size, weight, style)).get_extents()
    return bb.width * U / 72.0


def line_w(entry, size: float, weight: str = "normal") -> float:
    txt = entry[0] if isinstance(entry, tuple) else entry
    st = entry[1] if isinstance(entry, tuple) else {}
    return tw(txt, st.get("size", size), st.get("weight", weight), st.get("style", "normal"))


# ---------------------------------------------------------------- 画布
class Canvas:
    def __init__(self, w_in: float, h_in: float, title: str, zoom: float = 0.74):
        self.w, self.h, self.z = w_in, h_in, zoom
        self.fig = plt.figure(figsize=(w_in * zoom, h_in * zoom), dpi=DPI, facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w_in * U)
        self.ax.set_ylim(h_in * U, 0)
        self.ax.set_axis_off()
        self.obstacles: dict[str, tuple] = {}   # key -> ("rect", x0,y0,x1,y1) / ("ellipse", cx,cy,rx,ry)
        self._segs: list[tuple] = []            # (name, pts, allow)
        self.ax.text(self.w * U / 2, 0.36 * U, title, ha="center", va="center",
                     fontsize=21 * zoom, fontweight="bold", color=NAVY, fontfamily=FAMILIES)

    # ---------- 基本图元 ----------
    def text(self, x, y, s, size=11.5, color=INK, weight="normal", ha="left", va="center",
             style="normal", bbox=False, z=6, rotation=0):
        kw = {}
        if bbox:
            kw["bbox"] = dict(facecolor="white", edgecolor="none", pad=1.6, alpha=1.0)
        return self.ax.text(x, y, s, fontsize=size * self.z, color=color, fontweight=weight,
                            ha=ha, va=va, style=style, zorder=z, rotation=rotation,
                            fontfamily=FAMILIES, **kw)

    def rect(self, x, y, w, h, fc="none", ec=INK, lw=1.3, ls="-", z=2, radius=None):
        if radius:
            from matplotlib.patches import FancyBboxPatch
            p = FancyBboxPatch((x + radius, y + radius), w - 2 * radius, h - 2 * radius,
                               boxstyle=f"round,pad={radius}", fc=fc, ec=ec, lw=lw,
                               ls=ls, zorder=z, mutation_aspect=1)
        else:
            p = Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
        self.ax.add_patch(p)
        return p

    def poly(self, pts, fc=INK, ec=INK, lw=1.2, z=5, ls="-", closed=True):
        p = Polygon(pts, closed=closed, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls,
                    joinstyle="miter")
        self.ax.add_patch(p)
        return p

    def line(self, pts, color=INK, lw=1.4, ls="-", z=4, zorder=None):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=zorder if zorder is not None else z,
                     solid_capstyle="butt", dash_capstyle="butt")
        return pts

    # ---------- 障碍登记 ----------
    def reg_rect(self, key, x, y, w, h):
        self.obstacles[key] = ("rect", x, y, x + w, y + h)

    def reg_ellipse(self, key, cx, cy, rx, ry):
        self.obstacles[key] = ("ellipse", cx, cy, rx, ry)

    def seg(self, name, pts, allow=()):
        self._segs.append((name, pts, set(allow)))

    # ---------- 自检 ----------
    def check(self):
        bad = []
        for name, pts, allow in self._segs:
            for i in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                n = max(2, int(math.dist((x1, y1), (x2, y2)) / 1.5))
                for k in range(n + 1):
                    t = k / n
                    x = x1 + (x2 - x1) * t
                    y = y1 + (y2 - y1) * t
                    for key, ob in self.obstacles.items():
                        if key in allow:
                            continue
                        if ob[0] == "rect":
                            _, a, b, c, d = ob
                            if a + 1 <= x <= c - 1 and b + 1 <= y <= d - 1:
                                bad.append((name, key, round(x), round(y)))
                        else:
                            _, cx, cy, rx, ry = ob
                            if ((x - cx) / (rx - 1)) ** 2 + ((y - cy) / (ry - 1)) ** 2 < 1:
                                bad.append((name, key, round(x), round(y)))
        if bad:
            seen = set()
            for name, key, x, y in bad:
                k = (name, key)
                if k in seen:
                    continue
                seen.add(k)
                PROBLEMS.append(f"  [线穿框] {name} 穿过 {key} @({x},{y})")
        return len(bad)

    # ---------- 输出 ----------
    def save(self, name: str):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / name
        self.fig.savefig(path, dpi=DPI, facecolor="white")
        plt.close(self.fig)
        return path


# ---------------------------------------------------------------- 图元：类框 / 用例 / 参与者
def _entry_size(entry, default: float) -> float:
    return entry[1].get("size", default) if isinstance(entry, tuple) else default


def fit_size(entry, default: float, avail: float) -> float:
    """该行在 avail 宽度内可用的字号（放不下就自动缩字，最低 9.0pt）。"""
    size = _entry_size(entry, default)
    wd = line_w(entry, default)
    if wd > avail > 0:
        size = max(9.0, size * avail / wd * 0.985)
    return size


def class_box(cv: Canvas, key: str, name: str, x: float, y: float, w: float,
              attrs=(), ops=(), stereo: str | None = None,
              name_size: float = 13.0, body_size: float = 11.2,
              header: str = FILL, fill: str = FILL2, edge: str = NAVY,
              abstract: bool = False, min_h: float = 0.0):
    """UML 类框，返回 (x, y, w, h)。"""
    pad = 0.105 * U
    lh = 1.42 * body_size * U / 72.0
    hh = 1.34 * name_size * U / 72.0 + 2 * pad
    if stereo:
        hh += 0.98 * name_size * U / 72.0
    attrs = list(attrs)
    ops = list(ops)
    ah = len(attrs) * lh + 2 * pad if attrs else 0.0
    oh = len(ops) * lh + 2 * pad if ops else 0.0
    h = max(hh + ah + oh, min_h)

    cv.rect(x, y, w, h, fc=fill, ec="none", z=2)
    cv.rect(x, y, w, hh, fc=header, ec="none", z=2.1)
    cv.rect(x, y, w, h, fc="none", ec=edge, lw=1.5, z=3.2)

    cy = y + pad
    if stereo:
        cv.text(x + w / 2, cy + 0.46 * name_size * U / 72.0, stereo, size=name_size * 0.82,
                color=BLUE, ha="center", va="center", style="italic")
        cy += 0.98 * name_size * U / 72.0
    cv.text(x + w / 2, cy + 0.62 * name_size * U / 72.0, name, size=name_size,
            color=NAVY, weight="bold", ha="center", va="center", style="italic" if abstract else "normal")

    top = y + hh
    if attrs:
        cv.line([(x, top), (x + w, top)], color=edge, lw=1.2)
        for i, entry in enumerate(attrs):
            txt = entry[0] if isinstance(entry, tuple) else entry
            st = entry[1] if isinstance(entry, tuple) else {}
            sz = fit_size(entry, body_size, w - 2 * pad - 2)
            cv.text(x + pad, top + pad + i * lh + lh * 0.34, txt,
                    size=sz, color=st.get("color", INK),
                    style=st.get("style", "normal"), weight=st.get("weight", "normal"),
                    va="center")
            if tw(txt, sz, st.get("weight", "normal"), st.get("style", "normal")) > w - 2 * pad + 1:
                PROBLEMS.append(f"  [文字溢出] {key}: {txt!r} 超出框宽")
        top += ah
    if ops:
        cv.line([(x, top), (x + w, top)], color=edge, lw=1.2)
        for i, entry in enumerate(ops):
            txt = entry[0] if isinstance(entry, tuple) else entry
            st = entry[1] if isinstance(entry, tuple) else {}
            sz = fit_size(entry, body_size, w - 2 * pad - 2)
            cv.text(x + pad, top + pad + i * lh + lh * 0.34, txt,
                    size=sz, color=st.get("color", INK),
                    style=st.get("style", "normal"), weight=st.get("weight", "normal"),
                    va="center")
            if tw(txt, sz, st.get("weight", "normal"), st.get("style", "normal")) > w - 2 * pad + 1:
                PROBLEMS.append(f"  [文字溢出] {key}: {txt!r} 超出框宽")

    cv.reg_rect(key, x, y, w, h)
    return (x, y, w, h)


def module_box(cv: Canvas, key: str, name: str, x: float, y: float, w: float,
               lines=(), body_size: float = 11.2):
    return class_box(cv, key, name, x, y, w, attrs=[], ops=list(lines),
                     stereo="«module»", body_size=body_size, header=FILL3)


def usecase(cv: Canvas, key: str, cx: float, cy: float, w: float, h: float, label: str,
            size: float = 12.4):
    cv.ax.add_patch(Ellipse((cx, cy), w, h, fc="#F3F8FD", ec=BLUE, lw=1.5, zorder=2.5))
    cv.text(cx, cy, label, size=size, ha="center", va="center", color=INK)
    if tw(label, size) > w * 0.82:
        PROBLEMS.append(f"  [文字贴边] {key}: {label!r} 宽 {tw(label,size):.0f} / 椭圆 {w:.0f}")
    cv.reg_ellipse(key, cx, cy, w / 2, h / 2)
    return (cx, cy, w, h)


def actor(cv: Canvas, x: float, y: float, label: str, size: float = 13.0):
    """火柴人，(x, y) 为躯干上端；返回连线锚点。"""
    head_r = 0.115 * U
    hy = y + head_r
    cv.ax.add_patch(Circle((x, hy), head_r, fc=ACTOR, ec=INK, lw=1.5, zorder=4))
    top = hy + head_r
    hip = top + 0.34 * U
    cv.line([(x, top), (x, hip)], color=INK, lw=1.6)
    cv.line([(x - 0.20 * U, top + 0.11 * U), (x + 0.20 * U, top + 0.11 * U)], color=INK, lw=1.6)
    cv.line([(x, hip), (x - 0.16 * U, hip + 0.26 * U)], color=INK, lw=1.6)
    cv.line([(x, hip), (x + 0.16 * U, hip + 0.26 * U)], color=INK, lw=1.6)
    cv.text(x, hip + 0.40 * U, label, size=size, weight="bold", ha="center", va="top", color=NAVY)
    cv.reg_rect(f"actor:{label}", x - 0.30 * U, hy - head_r, 0.60 * U, 0.95 * U)
    return (x + 0.26 * U, top + 0.11 * U)


def ellipse_edge(cx, cy, rx, ry, toward):
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx + rx, cy)
    t = 1.0 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
    return (cx + dx * t, cy + dy * t)


# ---------------------------------------------------------------- 箭头
def head_open(cv: Canvas, tip, frm, color=INK, size=13.0, lw=1.5):
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    a = (tip[0] - ux * size + px * size * 0.42, tip[1] - uy * size + py * size * 0.42)
    b = (tip[0] - ux * size - px * size * 0.42, tip[1] - uy * size - py * size * 0.42)
    cv.line([a, tip, b], color=color, lw=lw, z=5)


def head_triangle(cv: Canvas, tip, frm, color=INK, size=17.0, lw=1.5):
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    a = (tip[0] - ux * size + px * size * 0.52, tip[1] - uy * size + py * size * 0.52)
    b = (tip[0] - ux * size - px * size * 0.52, tip[1] - uy * size - py * size * 0.52)
    cv.poly([tip, a, b], fc="white", ec=color, lw=lw, z=5)


def diamond(cv: Canvas, tip, frm, color=INK, size=20.0, lw=1.4):
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    mid = (tip[0] - ux * size * 0.55, tip[1] - uy * size * 0.55)
    end = (tip[0] - ux * size, tip[1] - uy * size)
    a = (mid[0] + px * size * 0.30, mid[1] + py * size * 0.30)
    b = (mid[0] - px * size * 0.30, mid[1] - py * size * 0.30)
    cv.poly([tip, a, end, b], fc=color, ec=color, lw=lw, z=5)


def arrow(cv: Canvas, name: str, pts, kind: str = "assoc", color=INK, lw=1.5,
          allow=(), head: str | None = None, head_size: float = 13.0):
    """pts 为折线点列；kind: assoc / depend / inherit / compose。"""
    pts = [tuple(p) for p in pts]
    if head is None:
        head = {"assoc": None, "depend": "open", "inherit": "tri", "compose": None}[kind]
    ls = (0, (6, 3.6)) if kind == "depend" else "-"
    if kind == "compose":
        diamond(cv, pts[0], pts[1], color=color, lw=lw)
        # 菱形尖端到第一段的 20 单位处
        dx, dy = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        n = math.hypot(dx, dy) or 1.0
        pts = [(pts[0][0] + dx / n * 20, pts[0][1] + dy / n * 20)] + pts[1:]
    if head in ("open", "tri"):
        tip = pts[-1]
        frm = pts[-2]
        dx, dy = tip[0] - frm[0], tip[1] - frm[1]
        n = math.hypot(dx, dy) or 1.0
        cut = head_size * (0.95 if head == "tri" else 1.0)
        pts = pts[:-1] + [(tip[0] - dx / n * cut, tip[1] - dy / n * cut)]
        if head == "open":
            head_open(cv, tip, frm, color=color, size=head_size, lw=lw)
        else:
            head_triangle(cv, tip, frm, color=color, size=head_size + 4, lw=lw)
    cv.line(pts, color=color, lw=lw, ls=ls)
    cv.seg(name, pts, allow)


# ---------------------------------------------------------------- 图 1 用例图
def fig_usecase():
    cv = Canvas(15.2, 9.45, "图 1  CampusEvent 用例图（baseline-v1）", zoom=0.72)
    bx0, by0, bx1, by1 = 2.95 * U, 0.98 * U, 13.05 * U, 8.30 * U
    cv.rect(bx0, by0, bx1 - bx0, by1 - by0, fc="#FCFDFE", ec=BLUE, lw=1.9, z=1.2)
    cv.text((bx0 + bx1) / 2, by0 + 0.30 * U, "系统边界：校园活动报名系统", size=14.0,
            weight="bold", color=BLUE, ha="center", va="center")
    cv.reg_rect("boundary", bx0, by0, bx1 - bx0, by1 - by0)

    student_pt = actor(cv, 1.32 * U, 3.88 * U, "学生")
    admin_pt = actor(cv, 14.20 * U, 3.46 * U, "管理员")

    UC_H = 0.62 * U
    L_CX, M_CX, R_CX = 4.66 * U, 7.78 * U, 11.36 * U
    left = [
        ("浏览活动列表", 1.85, 2.46), ("按名称筛选活动", 2.71, 2.46), ("查看活动详情", 3.57, 2.46),
        ("查看我的报名", 4.43, 2.46), ("查看站内通知", 5.29, 2.46), ("直接报名", 6.15, 2.30),
        ("提交报名申请（审核型）", 7.01, 2.72), ("取消报名", 7.87, 2.30),
    ]
    mid = [("校验名额与重复报名", 6.60, 2.56), ("发送站内通知", 4.43, 2.36)]
    right = [
        ("管理活动（增/改/删）", 2.71, 2.72), ("查看报名统计", 3.57, 2.46),
        ("审批报名（批准/拒绝）", 4.43, 2.72), ("校验剩余名额", 6.15, 2.46),
    ]

    pos, geo = {}, {}
    for name, yc, w in left:
        pos[name] = (L_CX, yc * U)
        geo[name] = (L_CX, yc * U, w * U)
        usecase(cv, name, L_CX, yc * U, w * U, UC_H, name)
    for name, yc, w in mid:
        pos[name] = (M_CX, yc * U)
        geo[name] = (M_CX, yc * U, w * U)
        usecase(cv, name, M_CX, yc * U, w * U, UC_H, name)
    for name, yc, w in right:
        pos[name] = (R_CX, yc * U)
        geo[name] = (R_CX, yc * U, w * U)
        usecase(cv, name, R_CX, yc * U, w * U, UC_H, name)

    # 参与者关联：走 x 方向的“干线 + 短横线”，避免 8 条斜线互相穿插
    def bus(anchor, bus_x, names, actor_key):
        ys = [pos[n][1] for n in names]
        top, bot = min(ys), max(ys)
        cv.line([anchor, (bus_x, anchor[1])], color=GREY, lw=1.25, z=2.6)
        cv.line([(bus_x, top), (bus_x, bot)], color=GREY, lw=1.25, z=2.6)
        cv.seg(f"{actor_key}-干线", [anchor, (bus_x, anchor[1])], allow={actor_key})
        cv.seg(f"{actor_key}-干线v", [(bus_x, top), (bus_x, bot)],
               allow={actor_key} | {f"boundary"})
        for n in names:
            cx, cy, w = geo[n]
            ex = cx - w / 2 if cx < bus_x else cx + w / 2
            cv.line([(bus_x, cy), (ex, cy)], color=GREY, lw=1.25, z=2.6)
            cv.seg(f"{actor_key}-{n}", [(bus_x, cy), (ex, cy)],
                   allow={"boundary", actor_key, n})

    bus(student_pt, 2.58 * U, [n for n, _, _ in left], "actor:学生")
    bus(admin_pt, 13.36 * U, [n for n, _, _ in right], "actor:管理员")


    def inc(src, dst, off=(0.0, -0.12), ha="center", va="bottom"):
        scx, scy, sw = geo[src]
        dcx, dcy, dw = geo[dst]
        p1 = ellipse_edge(scx, scy, sw / 2, UC_H / 2, (dcx, dcy))
        p2 = ellipse_edge(dcx, dcy, dw / 2, UC_H / 2, (scx, scy))
        arrow(cv, f"include:{src}->{dst}", [p1, p2], kind="depend", color=BLUE, lw=1.35,
              allow={src, dst, "boundary"}, head_size=12)
        cv.text((p1[0] + p2[0]) / 2 + off[0] * U, (p1[1] + p2[1]) / 2 + off[1] * U,
                "«include»", size=9.8, color=BLUE, ha=ha, va=va, style="italic", bbox=True)

    inc("直接报名", "校验名额与重复报名", off=(0.0, -0.10))
    inc("提交报名申请（审核型）", "校验名额与重复报名", off=(0.0, -0.10))
    inc("审批报名（批准/拒绝）", "校验剩余名额", off=(0.10, 0.0), ha="left", va="center")
    inc("审批报名（批准/拒绝）", "发送站内通知", off=(0.0, -0.11))
    inc("直接报名", "发送站内通知", off=(0.0, -0.11))

    # 图下小字
    cv.text(7.60 * U, 8.62 * U,
            "注：为免连线交叉，图中只画出示意箭头；「提交报名申请」「取消报名」等其余会改变报名状态的用例同样复用"
            "「发送站内通知」机制（事务提交后发送，通知失败不回滚报名）。",
            size=10.2, color=GREY, ha="center", va="center")
    cv.text(7.60 * U, 9.02 * U,
            "虚线箭头 «include» 表示被包含用例；参与者与用例之间的实线为关联关系。",
            size=10.2, color=GREY, ha="center", va="center")
    cv.check()
    return cv.save("usecase.png")


# ---------------------------------------------------------------- 图 2 类图
def fig_class():
    cv = Canvas(15.9, 12.72, "图 2  CampusEvent 类图（baseline-v1）", zoom=0.74)
    OFF = 0.58 * U
    B = {}

    # ---------------- 第 1 列：实体 ----------------
    x1, w1 = 0.25 * U, 3.10 * U
    B["Activity"] = class_box(
        cv, "Activity", "Activity", x1, OFF + 0.32 * U, w1, stereo="«dataclass»",
        attrs=["activity_id: int | None", "title: str", "category: str", "start_at: str",
               "location: str", "capacity: int", "policy_type: str"],
        ops=["«property» policy_label: str", "«property» needs_approval: bool"])
    y = B["Activity"][1] + B["Activity"][3] + 0.46 * U
    B["Registration"] = class_box(
        cv, "Registration", "Registration", x1, y, w1, stereo="«dataclass»",
        attrs=["registration_id: int | None", "activity_id: int", "student_id: str",
               "status: str", "created_at: str", "updated_at: str", "note: str = \"\"",
               "activity_title: str = \"\""],
        ops=[("// activity_title 为联表展示字段", {"color": LGREY, "size": 9.8, "style": "italic"})])
    y = B["Registration"][1] + B["Registration"][3] + 0.46 * U
    B["Student"] = class_box(
        cv, "Student", "Student", x1, y, w1, stereo="«dataclass»",
        attrs=["student_id: str", "name: str"])
    y = B["Student"][1] + B["Student"][3] + 0.46 * U
    B["Message"] = class_box(
        cv, "Message", "Message", x1, y, w1, stereo="«dataclass»",
        attrs=["message_id: int | None", "student_id: str", "activity_id: int | None",
               "content: str", "created_at: str", "is_read: bool = False",
               "kind: str = \"INFO\"", "seq: int = 0"])

    # ---------------- 第 2 列：服务 ----------------
    x2, w2 = 3.95 * U, 3.80 * U
    B["NotificationService"] = class_box(
        cv, "NotificationService", "NotificationService", x2, OFF + 0.32 * U, w2,
        attrs=["- channels: List[INotificationChannel]", "- failures: List[Dict[str, str]]"],
        ops=["+ publish(conn, message) -> Dict[str, bool]",
             "+ register(channel: INotificationChannel)"])
    y = B["NotificationService"][1] + B["NotificationService"][3] + 0.52 * U
    B["RegistrationService"] = class_box(
        cv, "RegistrationService", "RegistrationService", x2, y, w2,
        attrs=["- conn: sqlite3.Connection", "- notifier: NotificationService"],
        ops=["+ register(activity_id, student_id) -> dict",
             "+ cancel(registration_id, student_id) -> dict",
             "+ approve(registration_id) -> dict",
             "+ reject(registration_id, reason=\"\") -> dict",
             "+ stats(activity_id) -> dict",
             "+ seats_left(activity_id) -> int",
             "- _tx()  «contextmanager»",
             "- _notify(activity_id, title, items)",
             "- _load_activity(activity_id) -> Row"])
    y = B["RegistrationService"][1] + B["RegistrationService"][3] + 0.50 * U
    B["ActivityService"] = class_box(
        cv, "ActivityService", "ActivityService", x2, y, 3.02 * U,
        attrs=["- conn: sqlite3.Connection"],
        ops=["+ create(activity: Activity) -> int", "+ update(activity: Activity)",
             "+ delete(activity_id) -> dict",
             ("+ parse_activity_form(form) -> Activity", {"size": 10.0, "color": BLUE}),
             ("  «module» 模块级函数", {"size": 9.6, "color": BLUE, "style": "italic"})])

    # ---------------- 第 3 列：策略 ----------------
    x3, w3 = 8.55 * U, 3.18 * U
    B["RegistrationPolicy"] = class_box(
        cv, "RegistrationPolicy", "RegistrationPolicy", x3, OFF + 3.66 * U, w3,
        stereo="«abstract»", abstract=True,
        attrs=["code: str", "label: str"],
        ops=[("+ decide(seats_left: int) -> str  «abstract»", {"style": "italic"}),
             ("+ requires_approval() -> bool  «abstract»", {"style": "italic"}),
             "+ check(*, seats_left, capacity) -> None"])
    y = B["RegistrationPolicy"][1] + B["RegistrationPolicy"][3] + 0.46 * U
    B["DirectPolicy"] = class_box(
        cv, "DirectPolicy", "DirectPolicy", x3, y, w3,
        attrs=["code = \"DIRECT\"", "label = \"直接报名\""],
        ops=["+ decide(seats_left) -> \"已通过\"", "+ requires_approval() -> False"])
    y = B["DirectPolicy"][1] + B["DirectPolicy"][3] + 0.46 * U
    B["ApprovalPolicy"] = class_box(
        cv, "ApprovalPolicy", "ApprovalPolicy", x3, y, w3,
        attrs=["code = \"APPROVAL\"", "label = \"需审核\""],
        ops=["+ decide(seats_left) -> \"待审核\"", "+ requires_approval() -> True"])

    # ---------------- 第 4 列：通知通道 ----------------
    x4, w4 = 12.22 * U, 3.35 * U
    B["InboxChannel"] = class_box(
        cv, "InboxChannel", "InboxChannel", x4, OFF + 0.32 * U, w4,
        attrs=["name = \"inbox\""],
        ops=["+ deliver(conn, message) -> bool",
             ("// 按 (student_id, activity_id, content) 幂等去重",
              {"color": LGREY, "size": 9.8, "style": "italic"})])
    B["INotificationChannel"] = class_box(
        cv, "INotificationChannel", "INotificationChannel", x4, OFF + 2.12 * U, w4,
        stereo="«abstract»", abstract=True,
        attrs=["name: str"],
        ops=[("+ deliver(conn, message) -> bool  «abstract»", {"style": "italic"})])
    B["AuditChannel"] = class_box(
        cv, "AuditChannel", "AuditChannel", x4, OFF + 3.86 * U, w4,
        attrs=["name = \"audit\""],
        ops=["+ deliver(conn, message) -> bool",
             ("// 写 __audit__ 轨迹，按 seq 幂等", {"color": LGREY, "size": 9.8, "style": "italic"})])

    # ---------------- 底部：两个模块 ----------------
    B["repository"] = module_box(
        cv, "repository", "repository.py", 3.95 * U, OFF + 8.78 * U, 4.05 * U,
        lines=["connect(path) -> Connection",
               "get_activity(conn, activity_id)",
               "list_activities(conn, keyword=\"\")",
               "insert_registration(conn, aid, sid, status)",
               "update_status(conn, rid, status, note=\"\")",
               "count_approved(conn, activity_id) -> int",
               "active_registration(conn, aid, sid)",
               "pending_registrations(conn)",
               "insert_message(conn, sid, aid, content, kind)",
               ("…（其余 CRUD 略）", {"color": LGREY, "size": 9.8, "style": "italic"})])
    B["constants"] = module_box(
        cv, "constants", "constants.py", 12.22 * U, OFF + 5.62 * U, 3.35 * U,
        lines=["ST_PENDING = \"待审核\"", "ST_APPROVED = \"已通过\"",
               "ST_REJECTED = \"已拒绝\"", "ST_CANCELLED = \"已取消\"",
               "POLICY_DIRECT = \"DIRECT\"", "POLICY_APPROVAL = \"APPROVAL\"",
               "class SealError(message, code)"])

    def bx(k):
        x, y, w, h = B[k]
        return dict(x=x, y=y, w=w, h=h, l=x, r=x + w, t=y, b=y + h,
                    cx=x + w / 2, cy=y + h / 2)

    A = {k: bx(k) for k in B}

    # ---------------- 关系 ----------------
    # 实体关联
    arrow(cv, "Activity-Registration", [(A["Activity"]["l"] + 1.45 * U, A["Activity"]["b"]),
                                        (A["Activity"]["l"] + 1.45 * U, A["Registration"]["t"])],
          kind="assoc", color=INK, lw=1.5, allow={"Activity", "Registration"})
    cv.text(A["Activity"]["l"] + 1.60 * U, A["Activity"]["b"] + 0.13 * U, "1", size=10.5, color=GREY)
    cv.text(A["Activity"]["l"] + 1.60 * U, A["Registration"]["t"] - 0.13 * U, "0..*", size=10.5, color=GREY)
    arrow(cv, "Registration-Student", [(A["Registration"]["l"] + 1.45 * U, A["Registration"]["b"]),
                                       (A["Registration"]["l"] + 1.45 * U, A["Student"]["t"])],
          kind="assoc", color=INK, lw=1.5, allow={"Registration", "Student"})
    cv.text(A["Registration"]["l"] + 1.60 * U, A["Registration"]["b"] + 0.13 * U, "0..*", size=10.5, color=GREY)
    cv.text(A["Registration"]["l"] + 1.60 * U, A["Student"]["t"] - 0.13 * U, "1", size=10.5, color=GREY)

    # 组合：RegistrationService ◆— NotificationService
    xc = A["RegistrationService"]["l"] + 1.30 * U
    arrow(cv, "RS-NS", [(xc, A["RegistrationService"]["t"]), (xc, A["NotificationService"]["b"])],
          kind="compose", color=INK, lw=1.6,
          allow={"RegistrationService", "NotificationService"})
    cv.text(xc + 0.14 * U, A["RegistrationService"]["t"] - 0.10 * U, "1", size=10.5, color=GREY)
    cv.text(xc + 0.14 * U, A["NotificationService"]["b"] + 0.14 * U, "1", size=10.5, color=GREY)

    # 组合：NotificationService ◆— INotificationChannel（1..*）
    arrow(cv, "NS-INC", [(A["NotificationService"]["r"], A["NotificationService"]["cy"]),
                         (A["INotificationChannel"]["l"], A["NotificationService"]["cy"])],
          kind="compose", color=INK, lw=1.6,
          allow={"NotificationService", "INotificationChannel"})
    cv.text(A["NotificationService"]["r"] + 0.12 * U, A["NotificationService"]["cy"] - 0.14 * U,
            "1", size=10.5, color=GREY)
    cv.text(A["INotificationChannel"]["l"] - 0.12 * U, A["NotificationService"]["cy"] - 0.14 * U,
            "1..*", size=10.5, color=GREY, ha="right")

    # 继承：DirectPolicy / ApprovalPolicy → RegistrationPolicy
    arrow(cv, "Direct-extends", [(A["DirectPolicy"]["cx"], A["DirectPolicy"]["t"]),
                                 (A["RegistrationPolicy"]["cx"], A["RegistrationPolicy"]["b"])],
          kind="inherit", color=INK, lw=1.5, allow={"DirectPolicy", "RegistrationPolicy"})
    # ApprovalPolicy 绕右侧走廊回到父类右边缘
    xr = 11.95 * U
    arrow(cv, "Approval-extends",
          [(A["ApprovalPolicy"]["r"], A["ApprovalPolicy"]["cy"]),
           (xr, A["ApprovalPolicy"]["cy"]),
           (xr, A["RegistrationPolicy"]["cy"] + 0.35 * U),
           (A["RegistrationPolicy"]["r"], A["RegistrationPolicy"]["cy"] + 0.35 * U)],
          kind="inherit", color=INK, lw=1.45,
          allow={"ApprovalPolicy", "RegistrationPolicy", "AuditChannel"})

    # 继承：Inbox / Audit → INotificationChannel
    arrow(cv, "Inbox-extends", [(A["InboxChannel"]["cx"], A["InboxChannel"]["b"]),
                                (A["INotificationChannel"]["cx"], A["INotificationChannel"]["t"])],
          kind="inherit", color=INK, lw=1.5, allow={"InboxChannel", "INotificationChannel"})
    arrow(cv, "Audit-extends", [(A["AuditChannel"]["cx"], A["AuditChannel"]["t"]),
                                (A["INotificationChannel"]["cx"], A["INotificationChannel"]["b"])],
          kind="inherit", color=INK, lw=1.5, allow={"AuditChannel", "INotificationChannel"})

    # 依赖：RegistrationService ..> RegistrationPolicy
    ymid = A["RegistrationPolicy"]["cy"] + 0.30 * U
    arrow(cv, "RS-policy", [(A["RegistrationService"]["r"], ymid),
                            (A["RegistrationPolicy"]["l"], ymid)],
          kind="depend", color=BLUE, lw=1.45,
          allow={"RegistrationService", "RegistrationPolicy"}, head_size=12)
    cv.text((A["RegistrationService"]["r"] + A["RegistrationPolicy"]["l"]) / 2,
            ymid - 0.15 * U, "«use» get_policy", size=9.6, color=BLUE,
            ha="center", va="center", style="italic", bbox=True)

    # 依赖：两个服务 ..> repository
    xr2 = A["RegistrationService"]["r"] - 0.55 * U
    arrow(cv, "RS-repo", [(xr2, A["RegistrationService"]["b"]), (xr2, A["repository"]["t"])],
          kind="depend", color=BLUE, lw=1.45,
          allow={"RegistrationService", "ActivityService", "repository"}, head_size=12)
    cv.text(xr2 + 0.14 * U, (A["RegistrationService"]["b"] + A["repository"]["t"]) / 2,
            "«use»", size=9.6, color=BLUE, style="italic", bbox=True)
    xa = A["ActivityService"]["l"] + 1.05 * U
    arrow(cv, "AS-repo", [(xa, A["ActivityService"]["b"]), (xa, A["repository"]["t"])],
          kind="depend", color=BLUE, lw=1.45,
          allow={"ActivityService", "repository"}, head_size=12)

    # ---------------- 说明框 ----------------
    nx, ny, nw = 12.22 * U, OFF + 8.72 * U, 3.35 * U
    notes = ["• 实体为 @dataclass，只有数据、没有业务规则",
             "• «module» 是 Python 模块，框内列的是模块级函数",
             "• RegistrationService 通过 get_policy(code) 工厂",
             "   取得策略，只依赖抽象，不写 if/elif 判类型",
             "• 通知通道可插拔：publish() 逐通道 try/except，",
             "   失败写 NOTIFY_FAILED 审计行，不回滚报名"]
    nh = 0.24 * U + len(notes) * 0.205 * U + 0.10 * U
    cv.rect(nx, ny, nw, nh, fc=NOTE_FC, ec=NOTE_EC, lw=1.4, z=2)
    cv.text(nx + 0.14 * U, ny + 0.20 * U, "设计说明", size=12, weight="bold", color="#7A5C10")
    for i, s in enumerate(notes):
        cv.text(nx + 0.14 * U, ny + 0.42 * U + i * 0.205 * U, s, size=9.8, color="#6B5518")
    cv.reg_rect("notes", nx, ny, nw, nh)

    cv.check()
    return cv.save("class-diagram-v1.png")


# ---------------------------------------------------------------- 时序图公共件
def seq_head(cv: Canvas, x, w, title, sub=None, y=0.80 * U, h=0.68 * U, fill=FILL):
    cv.rect(x - w / 2, y, w, h, fc=fill, ec=NAVY, lw=1.5, z=3)
    if sub:
        cv.text(x, y + h * 0.34, title, size=11.6, weight="bold", color=NAVY, ha="center", va="center")
        cv.text(x, y + h * 0.74, sub, size=9.6, color=BLUE, ha="center", va="center")
    else:
        cv.text(x, y + h / 2, title, size=11.6, weight="bold", color=NAVY, ha="center", va="center")
    return (x - w / 2, y, w, h)


def lifeline(cv: Canvas, x, y0, y1, color=LGREY):
    cv.ax.plot([x, x], [y0, y1], color=color, lw=1.15, ls=(0, (5, 4)), zorder=1.6)


def msg(cv: Canvas, x1, x2, y, lines, color=INK, dashed=False, num=None,
        align="auto", size=10.9, bold_first=True, lw=1.45, label_side="above"):
    """一条消息（水平箭头 + 上方文字）。lines 可为 str 或 list。"""
    if isinstance(lines, str):
        lines = [lines]
    dashed_flag = dashed
    ls = (0, (6, 3.6)) if dashed_flag else "-"
    if x2 > x1:
        tip, frm = (x2, y), (x1, y)
        sgn = 1
    else:
        tip, frm = (x2, y), (x1, y)
        sgn = -1
    cut = 11.0
    cv.line([(x1, y), (x2 - sgn * cut, y)], color=color, lw=lw, ls=ls, z=4)
    head_open(cv, tip, frm, color=color, size=11.5, lw=lw)
    # 文本
    span = abs(x2 - x1)
    wmax = max(tw(s, size) for s in lines)
    if align == "auto":
        align = "center" if wmax < span - 12 else ("left" if sgn > 0 else "right")
    if align == "center":
        tx, ha = (x1 + x2) / 2, "center"
    elif align == "left":
        tx, ha = min(x1, x2) + 6, "left"
    else:
        tx, ha = max(x1, x2) - 6, "right"
    n = len(lines)
    for i, s in enumerate(lines):
        yy = y - 0.065 * U - (n - 1 - i) * 0.185 * U
        cv.text(tx, yy, s, size=size, color=color, ha=ha, va="bottom",
                weight="bold" if (bold_first and i == 0) else "normal", bbox=True)


def frame(cv: Canvas, x0, y0, x1, y1, guard, kind="alt"):
    cv.rect(x0, y0, x1 - x0, y1 - y0, fc="none", ec=ALT_EC, lw=1.5, ls=(0, (7, 4)), z=1.8)
    tw_tab, th = 0.40 * U, 0.235 * U
    pts = [(x0, y0), (x0 + tw_tab, y0), (x0 + tw_tab + 0.10 * U, y0 + th / 2),
           (x0 + tw_tab, y0 + th), (x0, y0 + th)]
    cv.poly(pts, fc=ALT_FC, ec=ALT_EC, lw=1.3, z=3)
    cv.text(x0 + tw_tab / 2, y0 + th / 2, kind, size=10.2, color="#7A5210",
            weight="bold", ha="center", va="center", style="italic", z=6)
    cv.text(x0 + tw_tab + 0.16 * U, y0 + th / 2, guard, size=10.6, color="#7A5210",
            ha="left", va="center", z=6)
    cv.reg_rect(f"frame:{guard[:12]}", x0, y0, x1 - x0, th)


def frame_else(cv: Canvas, x0, x1, y, guard):
    cv.line([(x0, y), (x1, y)], color=ALT_EC, lw=1.2, ls=(0, (7, 4)), z=3)
    cv.text(x0 + 0.52 * U, y + 0.16 * U, guard, size=10.4, color="#7A5210", va="center", z=6)


def note(cv: Canvas, x, y, w, lines, title=None, size=9.9):
    h = 0.16 * U + (0.20 * U if title else 0.0) + len(lines) * 0.195 * U + 0.10 * U
    cv.rect(x, y, w, h, fc=NOTE_FC, ec=NOTE_EC, lw=1.4, z=3)
    # 折角
    cv.poly([(x + w - 0.14 * U, y), (x + w, y + 0.14 * U), (x + w - 0.14 * U, y + 0.14 * U)],
            fc="#F0E2B4", ec=NOTE_EC, lw=1.0, z=4)
    yy = y + 0.12 * U
    if title:
        cv.text(x + 0.14 * U, yy + 0.09 * U, title, size=size + 0.6, weight="bold",
                color="#7A5C10", va="center")
        yy += 0.20 * U
    for s in lines:
        cv.text(x + 0.14 * U, yy + 0.09 * U, s, size=size, color="#6B5518", va="center")
        yy += 0.195 * U
    cv.reg_rect(f"note:{lines[0][:10]}", x, y, w, h)
    return h


# ---------------------------------------------------------------- 图 3 报名时序图
def fig_seq_register():
    cv = Canvas(14.4, 14.05, "图 3  CampusEvent 报名时序图（直接报名 / 审核型 两条分支）", zoom=0.78)
    X = {"stu": 1.30 * U, "web": 3.62 * U, "svc": 6.18 * U,
         "pol": 8.72 * U, "repo": 11.10 * U, "ntf": 13.32 * U}
    TOP, BOT = 1.62 * U, 12.40 * U

    # 参与者与生命线
    for key, w, title, sub in [
        ("web", 1.72 * U, "web.register", "Flask 路由"),
        ("svc", 2.30 * U, "RegistrationService", "领域服务"),
        ("pol", 2.20 * U, "RegistrationPolicy", "策略接口"),
        ("repo", 1.86 * U, "repository", "SQLite"),
        ("ntf", 2.24 * U, "NotificationService", "通知发布者"),
    ]:
        seq_head(cv, X[key], w, title, sub)
        lifeline(cv, X[key], TOP, BOT)
    # 学生：火柴人
    cv.text(X["stu"], 0.98 * U, "学生", size=12.2, weight="bold", color=NAVY, ha="center", va="center")
    cv.text(X["stu"], 1.28 * U, "«actor»", size=9.6, color=BLUE, ha="center", va="center", style="italic")
    a = X["stu"] + 0.0
    hy = 2.02 * U
    cv.ax.add_patch(Circle((X["stu"], hy), 0.115 * U, fc=ACTOR, ec=INK, lw=1.5, zorder=4))
    cv.line([(X["stu"], hy + 0.115 * U), (X["stu"], hy + 0.50 * U)], color=INK, lw=1.6, zorder=4)
    cv.line([(X["stu"] - 0.20 * U, hy + 0.22 * U), (X["stu"] + 0.20 * U, hy + 0.22 * U)], color=INK, lw=1.6, zorder=4)
    cv.line([(X["stu"], hy + 0.50 * U), (X["stu"] - 0.16 * U, hy + 0.74 * U)], color=INK, lw=1.6, zorder=4)
    cv.line([(X["stu"], hy + 0.50 * U), (X["stu"] + 0.16 * U, hy + 0.74 * U)], color=INK, lw=1.6, zorder=4)
    lifeline(cv, X["stu"], 2.86 * U, BOT)

    TOPY = 1.70 * U
    # ① ②
    msg(cv, X["stu"], X["web"], 2.96 * U, ["① POST /activity/{id}/register"])
    msg(cv, X["web"], X["svc"], 3.38 * U, ["② register(activity_id, student_id)"])

    # alt A：重复报名
    frame(cv, 0.62 * U, 3.66 * U, 13.92 * U, 5.30 * U,
          "[该学生在该活动上已有「待审核 / 已通过」的报名]")
    msg(cv, X["svc"], X["repo"], 4.10 * U,
        ["③ get_activity(...) / active_registration(...)"])
    msg(cv, X["repo"], X["svc"], 4.55 * U, ["活动行 / 已有报名行"], dashed=True,
        color=GREY, size=10.4)
    msg(cv, X["svc"], X["web"], 4.95 * U,
        ["④ 抛 SealError(\"DUPLICATE_ACTIVE\")"], dashed=True, color=RED)
    cv.text(X["web"] + 0.12 * U, 5.16 * U, "rollback，返回错误提示", size=9.6,
            color=RED, style="italic")

    # alt B：活动已开始
    frame(cv, 0.62 * U, 5.46 * U, 13.92 * U, 6.30 * U,
          "[act.start_at <= now（活动已开始）]")
    msg(cv, X["svc"], X["web"], 5.92 * U, ["⑤ 抛 SealError(\"ACTIVITY_STARTED\")"],
        dashed=True, color=RED)

    # ⑥ get_policy
    msg(cv, X["svc"], X["pol"], 6.65 * U, ["⑥ get_policy(act.policy_type)"])
    msg(cv, X["pol"], X["svc"], 6.98 * U, ["DirectPolicy / ApprovalPolicy（无状态单例）"],
        dashed=True, color=GREY, size=10.4)

    # alt C：名额已满
    frame(cv, 0.62 * U, 7.16 * U, 13.92 * U, 8.42 * U,
          "[left <= 0（名额已满，待审核不占名额）]")
    msg(cv, X["svc"], X["pol"], 7.62 * U, ["⑦ policy.check(seats_left=left, capacity=...)"])
    msg(cv, X["pol"], X["svc"], 8.10 * U, ["抛 SealError(\"CAPACITY_FULL\")"],
        dashed=True, color=RED)

    # alt D：成功
    frame(cv, 0.62 * U, 8.58 * U, 13.92 * U, 11.30 * U,
          "[成功：DIRECT → 已通过 ； APPROVAL → 待审核]")
    msg(cv, X["svc"], X["pol"], 9.02 * U, ["⑧ policy.decide(seats_left)"])
    msg(cv, X["pol"], X["svc"], 9.36 * U, ["\"已通过\"（DIRECT） / \"待审核\"（APPROVAL）"],
        dashed=True, color=GREY, size=10.4)
    msg(cv, X["svc"], X["repo"], 9.74 * U, ["⑨ insert_registration(...) + COMMIT"])
    msg(cv, X["repo"], X["svc"], 10.08 * U, ["registration_id"], dashed=True,
        color=GREY, size=10.4)
    msg(cv, X["svc"], X["web"], 10.46 * U, ["⑩ {registration_id, status, seats_left}"],
        dashed=True)

    # ⑪ 通知（事务提交之后）
    msg(cv, X["svc"], X["ntf"], 11.10 * U,
        ["⑪ publish(Message)  —  事务提交之后", "InboxChannel 写 message 表（幂等去重）",
         "AuditChannel 写审计；异常则写 NOTIFY_FAILED"], size=10.6)
    msg(cv, X["ntf"], X["svc"], 11.72 * U, ["{inbox: True, audit: True}"], dashed=True,
        color=GREY, size=10.4)

    # ⑫ flash + 302
    msg(cv, X["web"], X["stu"], 12.16 * U, ["⑫ flash「报名成功，剩余名额 N」+ 302 回详情页"])

    note(cv, 9.40 * U, 12.52 * U, 4.60 * U,
         ["通知在事务提交（COMMIT）之后发送；",
          "任一通道异常只写 NOTIFY_FAILED 审计行，",
          "不回滚已提交的报名记录。"],
         title="注解")

    cv.text(0.62 * U, 13.72 * U,
            "事务边界：③–⑨ 在 BEGIN IMMEDIATE … COMMIT 内完成（名额检查与插入同一事务，防超卖）；"
            "⑪ 在 COMMIT 之后执行。",
            size=10.0, color=GREY, va="top")
    cv.check()
    return cv.save("seq-register.png")


# ---------------------------------------------------------------- 图 4 审批时序图
def fig_seq_approve():
    cv = Canvas(11.9, 11.10, "图 4  CampusEvent 审批时序图", zoom=0.78)
    X = {"adm": 1.28 * U, "web": 3.42 * U, "svc": 5.92 * U,
         "repo": 8.42 * U, "ntf": 10.55 * U}
    TOP, BOT = 1.48 * U, 9.20 * U

    for key, w, title, sub in [
        ("web", 1.74 * U, "web.approve", "Flask 路由"),
        ("svc", 2.34 * U, "RegistrationService", "领域服务"),
        ("repo", 1.86 * U, "repository", "SQLite"),
        ("ntf", 2.26 * U, "NotificationService", "通知发布者"),
    ]:
        seq_head(cv, X[key], w, title, sub)
        lifeline(cv, X[key], TOP, BOT)

    cv.text(X["adm"], 1.00 * U, "管理员", size=12.2, weight="bold", color=NAVY,
            ha="center", va="center")
    cv.text(X["adm"], 1.30 * U, "«actor»", size=9.6, color=BLUE, ha="center",
            va="center", style="italic")
    hy = 1.94 * U
    cv.ax.add_patch(Circle((X["adm"], hy), 0.115 * U, fc=ACTOR, ec=INK, lw=1.5, zorder=4))
    cv.line([(X["adm"], hy + 0.115 * U), (X["adm"], hy + 0.50 * U)], color=INK, lw=1.6, zorder=4)
    cv.line([(X["adm"] - 0.20 * U, hy + 0.22 * U), (X["adm"] + 0.20 * U, hy + 0.22 * U)],
            color=INK, lw=1.6, zorder=4)
    cv.line([(X["adm"], hy + 0.50 * U), (X["adm"] - 0.16 * U, hy + 0.74 * U)],
            color=INK, lw=1.6, zorder=4)
    cv.line([(X["adm"], hy + 0.50 * U), (X["adm"] + 0.16 * U, hy + 0.74 * U)],
            color=INK, lw=1.6, zorder=4)
    lifeline(cv, X["adm"], 2.82 * U, BOT)

    msg(cv, X["adm"], X["web"], 2.96 * U, ["① POST /admin/registration/{id}/approve"])
    msg(cv, X["web"], X["svc"], 3.38 * U, ["② approve(registration_id)"])
    msg(cv, X["svc"], X["repo"], 3.82 * U, ["③ get_registration(registration_id)"])
    msg(cv, X["repo"], X["svc"], 4.20 * U, ["报名行（status / activity_id / student_id）"],
        dashed=True, color=GREY, size=10.4)

    frame(cv, 0.60 * U, 4.42 * U, 11.48 * U, 5.10 * U, "[status ≠ 「待审核」]")
    msg(cv, X["svc"], X["web"], 4.86 * U, ["④ 抛 SealError(\"INVALID_STATUS\")"],
        dashed=True, color=RED)

    msg(cv, X["svc"], X["repo"], 5.52 * U,
        ["⑤ count_approved(activity_id)", "left = capacity - approved"])
    msg(cv, X["repo"], X["svc"], 5.92 * U, ["approved 人数"], dashed=True, color=GREY, size=10.4)

    # alt：名额已满（失败）在上，名额充足（成功）在下，两个操作数各占一段
    frame(cv, 0.60 * U, 6.16 * U, 11.48 * U, 9.24 * U,
          "[left <= 0：名额已满，批准失败]")
    msg(cv, X["svc"], X["web"], 6.62 * U, ["抛 SealError(\"CAPACITY_FULL\")"],
        dashed=True, color=RED)
    cv.text(X["web"] + 0.14 * U, 6.86 * U, "状态仍为「待审核」，事务回滚，不写通知",
            size=9.6, color=RED, style="italic")

    cv.line([(0.60 * U, 7.14 * U), (11.48 * U, 7.14 * U)], color=ALT_EC, lw=1.2,
            ls=(0, (7, 4)), z=3)
    cv.text(0.98 * U, 7.30 * U, "[left > 0：名额充足，批准成功]", size=10.4,
            color="#7A5210", va="center", z=6)

    msg(cv, X["svc"], X["repo"], 7.76 * U, ["⑥ update_status(id, \"已通过\") + COMMIT"])
    msg(cv, X["repo"], X["svc"], 8.16 * U, ["OK（rowcount = 1）"], dashed=True,
        color=GREY, size=10.4)
    msg(cv, X["svc"], X["ntf"], 8.76 * U,
        ["⑦ publish(Message)", "学生「审核通过，剩余名额 N」；__admin__ 写 AUDIT"], size=10.6)
    msg(cv, X["ntf"], X["svc"], 9.12 * U, ["{inbox: True, audit: True}"], dashed=True,
        color=GREY, size=10.4)

    # ⑧ 回到管理员
    msg(cv, X["web"], X["adm"], 9.56 * U, ["⑧ flash「已批准，剩余名额 N」+ 302 回审批列表"],
        align="left")
    cv.text(X["web"] + 0.10 * U, 9.80 * U, "{status: \"已通过\", seats_left: N}",
            size=10.2, color=GREY, style="italic")

    note(cv, 0.62 * U, 9.98 * U, 10.66 * U,
         ["审批时二次校验名额：待审核不占名额，可能在审批前被别人占满；批准失败时状态保持「待审核」。",
          "通知在事务提交之后发送，失败只写 NOTIFY_FAILED 审计行，不影响审批结果。"],
         title="注解", size=9.9)
    cv.check()
    return cv.save("seq-approve.png")


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    outs = []
    for fn in (fig_usecase, fig_class, fig_seq_register, fig_seq_approve):
        p = fn()
        outs.append(p)
        print(f"生成 {p}")
    print("\n自检：")
    if PROBLEMS:
        for s in dict.fromkeys(PROBLEMS):
            print(s)
    else:
        print("  未发现线穿框 / 文字溢出。")
    print("\n尺寸：")
    from PIL import Image
    for p in outs:
        with Image.open(p) as im:
            print(f"  {p.name}: {im.size[0]}x{im.size[1]} px  ({im.size[0]/DPI:.2f}x{im.size[1]/DPI:.2f} in @ {DPI}dpi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
