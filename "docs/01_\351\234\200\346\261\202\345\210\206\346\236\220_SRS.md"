# CampusEvent 校园活动报名系统 —— 初始需求分析（SRS）

- 课程：《软件工程》实验二
- 学生：242806010116 宋逸轩（个人独立完成）
- 版本：baseline-v1
- 对应指导书：3.1 任务概述、P2-F01 ~ P2-F08、附录 B.2 业务规则

---

## 1. 项目目标与范围

CampusEvent 面向校园内“活动发布 → 学生报名 → 管理员审批 → 结果通知”的完整链路，支持两种报名方式：
**直接报名（DIRECT）** 提交即通过，**需审核（APPROVAL）** 先进入待审核、由管理员批准或拒绝。

本期范围（baseline-v1）：

| 在范围内 | 说明 |
| --- | --- |
| 活动管理 | 管理员新建、编辑、删除活动；删除采用软删除 |
| 活动查看 | 学生查看列表与详情，按名称筛选 |
| 报名与取消 | 两种报名策略；同一活动禁止重复有效报名 |
| 审批 | 管理员批准 / 拒绝；批准时复查剩余名额 |
| 状态管理 | 待审核 / 已通过 / 已拒绝 / 已取消 |
| 站内通知 | 报名结果、审批结果、活动取消写入站内消息 |
| 统计 | 每个活动的已通过数、待审核数、剩余名额 |
| 持久化 | 活动与报名重启后不丢失（SQLite） |

明确不在本期范围：真实身份认证（用演示账号下拉登录代替）、邮件/短信通知、候补队列、签到与学分、
多租户与权限模型、活动分类的独立维护。指导书 3.6 规定变更单（CR）发布前不得提前实现变更内容，
因此上述“明显可扩展但未要求”的能力只在设计中预留扩展点，不在 baseline-v1 落地。

## 2. 角色

| 角色 | 权限 | 入口 |
| --- | --- | --- |
| 学生 | 浏览/筛选活动、查看详情、报名、取消自己的报名、查看我的报名、查看站内通知 | `/`、`/activity/<id>`、`/my`、`/messages` |
| 管理员 | 学生的全部查看能力之外：活动增改删、查看待审核列表、批准/拒绝、查看统计 | `/admin/*` |
| 系统 | 按策略决定报名状态、检查名额、生成通知、记录审计 | 服务层与通知通道 |

演示账号：学生 2024001 张三、2024002 李四、2024003 王五；管理员 admin。登录不做密码校验，
这是实验范围内的有意取舍（见 README 第 8 节），因为本期考察的是报名业务规则与设计，而不是认证。

## 3. 功能需求与验收标准

### P2-F01 活动管理

- 管理员可新建活动，字段：名称（必填，≤60 字）、类别、开始时间、地点（必填）、人数上限（正整数）、报名方式（直接报名 / 需审核）。
- 管理员可编辑、删除活动；删除时给仍在“待审核/已通过”的报名人发送“活动已被管理员取消”通知。
- 删除策略选**软删除**（`activity.deleted_at`）：报名记录是参与凭证，硬删除会毁掉历史；
  软删除后学生端列表与详情不可见，但历史报名仍可追溯。
- 实现：`app/domain/activity_service.py`（`parse_activity_form`、`ActivityService.create/update/delete`）、路由 `/admin/activity/*`。

### P2-F02 活动查看

- 学生首页展示活动卡片：名称、类别、时间、地点、上限、已通过、待审核、剩余名额、我的报名状态。
- 支持按名称模糊筛选（`?q=`），列表与筛选结果共用同一视图。
- 详情页展示活动全部字段、四个统计卡、报名记录表（含已取消/已拒绝的历史记录）。
- 实现：`/`、`/activity/<id>`，模板 `activities.html`、`activity_detail.html`。

### P2-F03 报名 / 取消

- 学生对同一活动不得同时存在两条“待审核/已通过”的报名；已取消/已拒绝保留历史，可重新申请。
- 取消仅限本人、且状态必须是“待审核/已通过”；取消后名额立即回补。
- 活动开始后不允许新增报名（业务规则 5），取消不受此限。
- 实现：`RegistrationService.register/cancel`；数据库另有部分唯一索引 `ux_reg_active` 兜底。

### P2-F04 报名策略

- DIRECT：名额充足时提交即“已通过”。
- APPROVAL：提交后进入“待审核”，不占用名额。
- 策略通过策略模式实现，新增策略只需新增类并注册，`RegistrationService` 不修改。

### P2-F05 审批

- 管理员在 `/admin/approvals` 看到全部待审核申请（学生、学号、活动、活动容量、提交时间、备注）。
- 批准：状态必须为“待审核”，且**再次检查剩余名额**；名额已满时批准失败，状态保持“待审核”。
- 拒绝：可填拒绝理由，写入 `registration.note` 并随通知发给学生。
- 实现：`RegistrationService.approve/reject`，均在同一事务内完成状态变更。

### P2-F06 状态管理

状态集合与合法迁移：

```
（新建）──DIRECT──▶ 已通过 ──取消──▶ 已取消
（新建）──APPROVAL──▶ 待审核 ──批准──▶ 已通过 ──取消──▶ 已取消
                       └──拒绝──▶ 已拒绝 ──重新申请──▶ 待审核/已通过
```

“已取消/已拒绝”是终态的历史记录，不参与名额统计，也不阻止再次申请。

### P2-F07 站内通知

- 触发点：报名成功、申请待审核、批准、拒绝、取消、活动被删除。
- 通知写入 `message` 表，`/messages` 展示，进入页面后标记为已读（页面标注“本次新读”）。
- 通知通道可插拔（观察者模式）；通道失败留审计痕迹，不影响已经提交的报名。

### P2-F08 统计

- `stats(activity_id)` 返回 `capacity / approved / pending / rejected / cancelled / seats_left`。
- 剩余名额 = 上限 − 已通过数；“待审核”不占名额（业务规则 3）。

## 4. 业务规则（附录 B.2）与实现映射

| 规则 | 要求 | 实现位置 | 测试 |
| --- | --- | --- | --- |
| B.2-1 | 直接报名且名额充足 → 已通过 + 站内通知 | `policy.DirectPolicy.decide` + `RegistrationService._notify` | `test_direct_policy_auto_approves` |
| B.2-2 | 审核型 → 待审核；批准/拒绝；批准时复查名额 | `ApprovalPolicy`、`approve/reject` | `test_approve_pending_and_notify`、`test_reject_pending_and_notify` |
| B.2-3 | 名额只按已通过计，待审核不占名额，满员不得再批准 | `count_approved`、`approve` 中的复查 | `test_pending_does_not_consume_seat`、`test_approve_when_capacity_full_fails` |
| B.2-4 | 同一学生同一活动不得两条有效报名；取消/拒绝后保留历史可再申请 | `active_registration` + 部分唯一索引 | `test_duplicate_active_registration_rejected`、`test_cancel_then_reapply_allowed` |
| B.2-5 | 可取消自己的待审核/已通过；活动开始后不允许新增报名 | `cancel`、`register` 中的开始时间检查 | `test_cancel_own_registration_and_stats`、`test_registration_after_activity_start_blocked` |
| B.2-6 | 通知失败要留痕，但不得让合法报名无声消失 | `NotificationService.publish` 捕获异常并写 `NOTIFY_FAILED` | `test_notification_failure_does_not_lose_registration` |
| B.2-7 | 活动与报名必须持久化；删除有报名的活动可拒绝或软删除并说明 | SQLite 落盘 + 软删除 | `test_persistence.py`、`test_soft_delete_hides_activity_but_keeps_history` |

## 5. 非功能需求

| 维度 | 要求 | 落地方式 |
| --- | --- | --- |
| 持久化 | 重启服务后数据一致 | SQLite 文件 `instance/campusevent.sqlite`，WAL 外键开启 |
| 一致性 | 名额不超卖、状态迁移合法 | 单事务 `BEGIN IMMEDIATE … COMMIT`；状态校验前置 |
| 可维护性 | 新增报名方式/通知通道不改业务核心 | 策略模式 + 观察者模式 + 依赖倒置 |
| 可测试性 | 业务规则可脱离 HTTP 测试 | 服务层接受 `conn` 与 `notifier` 注入；65 条 pytest |
| 安全性（本期） | 学生不能访问管理页；不能取消他人报名 | 会话角色校验、403 页面、归属校验 `NOT_OWNER` |
| 可用性 | 关键操作有明确反馈 | flash 提示 + 状态徽标 + 名额实时显示 |

## 6. 数据模型

```sql
student(student_id PK, name)
activity(activity_id PK AUTOINCREMENT, title, category, start_at, location,
         capacity CHECK(capacity > 0), policy_type CHECK(policy_type IN ('DIRECT','APPROVAL')),
         deleted_at)
registration(registration_id PK, activity_id FK, student_id FK,
             status CHECK(status IN ('待审核','已通过','已拒绝','已取消')),
             note, created_at, updated_at)
CREATE UNIQUE INDEX ux_reg_active ON registration(activity_id, student_id)
  WHERE status IN ('待审核','已通过');        -- 业务规则 4 的数据库兜底
message(message_id PK, student_id, activity_id, kind, content, created_at, is_read)
```

时间统一以 `YYYY-MM-DD HH:MM` 文本存储，便于 SQLite 比较与前端 `datetime-local` 回填。

## 7. 约束与假设

1. 单机单库部署（2 vCPU / 2 GiB 云服务器），并发量小；写入用 SQLite 的 `BEGIN IMMEDIATE` 串行化。
2. 登录为演示身份选择，不作为安全边界；管理页仍校验 `role == admin`。
3. 变更单（CR）由教师在初版验收后统一发布；baseline-v1 不包含任何猜测性变更实现，
   但类图与接口已为“新增策略 / 新增通知通道 / 新增统计维度”预留扩展点。

## 8. 交付物对照（3.8 与附录 D）

| 要求 | 文件 |
| --- | --- |
| 初始 SRS 分析 | `docs/01_需求分析_SRS.md` |
| 用例说明 | `docs/02_用例说明.md` |
| 初版 UML 类图 / 时序图 / 用例图 | `docs/diagrams/*.png`（说明见 `docs/03_设计模式与UML说明.md`） |
| 设计模式决策报告 | `docs/03_设计模式与UML说明.md` 第 3~5 节 |
| 设计评审签名表 | `docs/04_设计评审表.md` |
| 回归测试表 | `docs/05_测试用例与回归表.md` |
| 变更影响分析 | `docs/06_变更影响分析模板.md`（CR 发布后填写） |
| AI 协作记录 | `AI_DEV_LOG.md` |
| 项目总结 | `docs/07_项目总结.md` |
| 实验报告 | `docs/实验二_实验报告_宋逸轩.docx` |
| 云部署与访问地址 | `README.md` 第 6 节 |
