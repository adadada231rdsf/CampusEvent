# CampusEvent 校园活动报名系统

《软件工程》实验二 · 个人独立完成
学号：242806010116　姓名：宋逸轩

一个用 Flask + SQLite 实现的活动报名系统。核心不是页面，而是把**报名规则**与**通知机制**从业务代码里解耦：
报名方式用**策略模式**（Strategy），通知用**观察者模式**（Observer），两者都有可替换的实现和对应的单元测试。

- 访问地址：http://47.106.192.221:8080　（云服务器部署，见第 6 节；80 端口仍为实验一 StudyTask）
- 源码仓库：https://github.com/adadada231rdsf/CampusEvent

---

## 1. 功能一览

| 需求编号 | 功能 | 实现位置 |
| --- | --- | --- |
| P2-F01 | 活动管理（管理员增 / 改 / 删） | `app/domain/activity_service.py` + `/admin/activity/*` |
| P2-F02 | 活动查看（列表 + 详情，按名称筛选） | `/`、`/activity/<id>` |
| P2-F03 | 报名 / 取消（同一活动禁止重复有效报名） | `RegistrationService.register / cancel` |
| P2-F04 | 报名策略（直接报名 / 需审核） | `app/domain/policy.py` |
| P2-F05 | 审批（批准 / 拒绝，批准时复查名额） | `RegistrationService.approve / reject` |
| P2-F06 | 状态管理（待审核 / 已通过 / 已拒绝 / 已取消） | `app/domain/constants.py` + `registration.status` |
| P2-F07 | 站内通知 | `app/domain/notification.py` + `/messages` |
| P2-F08 | 统计（已通过 / 待审核 / 剩余名额） | `RegistrationService.stats` |

业务规则严格对照指导书附录 B.2 的 7 条，测试逐条覆盖（见第 4 节）。

## 2. 设计要点

- **策略模式**：`RegistrationPolicy` 抽象出 `decide(seats_left)` 与 `requires_approval()`；
  `DirectPolicy` 直接通过、`ApprovalPolicy` 进待审核。`RegistrationService` 只依赖接口，
  新增“抽签 / 班级限定”只需要加一个类并注册，Service 一行不改。
- **名额检查放在哪**：放在策略基类 `RegistrationPolicy.check()` 里，属于**公共规则**（所有策略都必须检查名额），
  而不是各个策略自己重复实现；策略只决定“通过还是待审核”。
- **观察者模式**：`NotificationService.publish()` 是发布者，`INotificationChannel` 是观察者接口，
  站内信（InboxChannel）与审计（AuditChannel）是两个实现。业务侧不知道通知最终落在哪。
- **通知失败不影响报名**：报名与状态变更在同一个事务里提交，通知是提交之后“尽力而为”；
  通道异常被 `publish()` 捕获并在审计表留一条 `NOTIFY_FAILED`，学生仍能在“我的报名”看到记录。
- **避免重复通知**：站内信通道以 `(student_id, activity_id, content)` 幂等去重，审计通道按内容去重，
  重试不会给学生发两条一样的消息。
- **删除策略**：选**软删除**（`activity.deleted_at`）。报名记录是参与凭证，硬删会毁掉历史；
  软删除后学生端自动看不到，已报名学生收到“活动已取消”通知。

详细设计文档（用例说明、UML 类图、时序图、设计模式决策报告）见 `docs/`。

## 3. 快速开始

环境：Python 3.10+（本机用 3.13 验证）。

```bash
cd CampusEvent
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python seed_demo.py               # 可选：生成演示数据（加 --reset 重建）
python run.py                     # http://127.0.0.1:5000
```

演示账号（登录页下拉选择，无需注册）：

- 学生：2024001 张三 / 2024002 李四 / 2024003 王五
- 管理员：admin

## 4. 测试

```bash
python -m pytest -q
```

65 条用例，覆盖验收用例 C1–C10、B.2 的 7 条业务规则、策略/通知的单元行为、
表单校验与权限：

| 文件 | 数量 | 覆盖内容 |
| --- | --- | --- |
| `tests/test_registration.py` | 22 | 报名、审批、取消、统计、事务与通知失败、唯一索引 |
| `tests/test_activity.py` | 16 | 表单校验、增改查、软删除、删除后审批失败 |
| `tests/test_web.py` | 15 | 登录、权限、页面流程、404、通知已读 |
| `tests/test_policy.py` | 10 | 策略接口、名额公共检查、策略无状态 |
| `tests/test_persistence.py` | 2 | 重启（新连接 / 新应用实例）后数据一致（C10） |

测试采用每条用例一个独立 SQLite 文件（`tests/conftest.py`），不依赖执行顺序。

## 5. 数据库 Schema

```sql
student(student_id PK, name)
activity(activity_id PK, title, category, start_at, location,
         capacity CHECK(capacity > 0), policy_type, deleted_at)
registration(registration_id PK, activity_id FK, student_id FK, status, note,
             created_at, updated_at)
-- 同一学生同一活动最多一条“待审核/已通过”
CREATE UNIQUE INDEX ux_reg_active ON registration(activity_id, student_id)
  WHERE status IN ('待审核', '已通过');
message(message_id PK, student_id, activity_id, kind, content, created_at, is_read)
```

状态取值：待审核 / 已通过 / 已拒绝 / 已取消；报名方式取值：DIRECT / APPROVAL。

## 6. 部署（Ubuntu 24.04）

服务器上 80 端口已被实验一的 StudyTask 占用，CampusEvent 用 **8080** 端口共存。
已在 `47.106.192.221` 上线：`campusevent.service`（systemd，`Restart=always`）托管 gunicorn，
防火墙放行 TCP 8080，公网访问 <http://47.106.192.221:8080>。

从零部署的命令（仓库已含 `tools/deploy.sh`，服务器上执行即可）：

```bash
# 本地：导出当前提交并上传（仓库为私有，scp 比 git clone 省事）
git archive --format=tar HEAD -o _tmp/campusevent.tar
scp _tmp/campusevent.tar root@47.106.192.221:/root/
ssh root@47.106.192.221 'mkdir -p /root/CampusEvent && tar -xf /root/campusevent.tar -C /root/CampusEvent'

# 服务器
cd /root/CampusEvent
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple bash tools/deploy.sh 8080
```

`tools/deploy.sh` 会建 venv、装依赖、写 `/etc/systemd/system/campusevent.service`
（含随机 `CAMPUSEVENT_SECRET`、`Restart=always`）、灌演示数据并 `systemctl enable --now`。
注意脚本必须保持 LF 换行（`.gitattributes` 已强制），否则 bash 报 `set: pipefail: invalid option name`。

持久化文件：`instance/campusevent.sqlite`（重启不丢数据）。
验证：`curl -I http://127.0.0.1:8080/login` 返回 200；外网访问 `http://47.106.192.221:8080`。

## 7. 文档索引

| 文件 | 内容 |
| --- | --- |
| `docs/01_需求分析_SRS.md` | 初始需求分析、B.2 规则到代码/测试的映射 |
| `docs/02_用例说明.md` | UC-01 ~ UC-08、C1–C10 对照 |
| `docs/03_设计模式与UML说明.md` | 设计模式决策报告、读图指引 |
| `docs/04_设计评审表.md` | 送审材料清单与评审签名表 |
| `docs/05_测试用例与回归表.md` | 65 条用例明细、手工验收表、缺陷记录 |
| `docs/06_变更影响分析模板.md` | CR 到达后填写的影响分析 |
| `docs/07_项目总结.md` | 项目总结（含 4 个真实问题） |
| `docs/08_验收记录.md` | C1–C10 操作步骤与截图编号 |
| `docs/diagrams/` | 用例图、类图、报名/审批时序图 |
| `docs/screenshots/` | 20 张真实浏览器验收截图（含云端实例） |
| `docs/实验二_实验报告_宋逸轩.docx` | 实验报告（按附录 D.1 结构） |
| `docs/实验二_演示_宋逸轩.pptx` | 演示文稿（15 页，策略/观察者/时序/测试/部署） |
| `AI_DEV_LOG.md` | 11 轮 AI 协作记录 |
| `你要做的步骤.md` | 需要学生本人完成的步骤清单 |

## 8. 目录结构

```
CampusEvent/
├── app/
│   ├── __init__.py            # 暴露 create_app
│   ├── web/__init__.py        # Flask 装配层：路由、会话、错误页
│   ├── domain/
│   │   ├── constants.py       # 状态、策略编码、SealError
│   │   ├── entities.py        # Student / Activity / Registration / Message
│   │   ├── policy.py          # 策略模式：报名方式
│   │   ├── notification.py    # 观察者模式：通知通道
│   │   ├── repository.py      # SQLite 访问 + Schema
│   │   ├── registration_service.py  # 报名核心业务
│   │   └── activity_service.py      # 活动管理 + 表单校验
│   ├── templates/             # Jinja2 页面（9 个）
│   └── static/style.css
├── tests/                     # pytest：65 条
├── docs/                      # 设计文档、UML、验收记录、截图
├── run.py                     # 开发服务器
├── seed_demo.py               # 演示数据
├── requirements.txt
└── AI_DEV_LOG.md              # 与 AI 的关键协作记录
```

## 9. 已知取舍

- 登录是“演示账号下拉选择”，没有密码与注册流程——实验关注报名业务规则，不关注认证。
- 名额并发用 `BEGIN IMMEDIATE` 串行化写入，单机 SQLite 足够；多实例部署需换成独立数据库。
- 通知只有站内信与审计两个通道，邮件/短信通道留了 `register()` 扩展点但未实现。
