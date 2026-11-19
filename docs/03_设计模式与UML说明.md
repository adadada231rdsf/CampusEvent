# CampusEvent 设计说明与设计模式决策报告（baseline-v1）

- 课程：《软件工程》实验二
- 学生：242806010116 宋逸轩
- 对应指导书：3.4 设计任务 A/B/C/D、3.7 可维护性要求
- 配套图：`docs/diagrams/class-diagram-v1.png`、`seq-register.png`、`seq-approve.png`、`usecase.png`

> 过程说明：按指导书 3.4-D 的要求，**先由 AI 产出设计材料（本文档 + 4 张 UML 图），经同学评审后才进入编码**。
> AI 协作过程与人工修正记录见项目根目录 `AI_DEV_LOG.md`；评审签名见 `docs/04_设计评审表.md`。

---

## 1. 设计目标

1. 报名规则会变（直接报名 / 需审核，未来可能出现抽签、班级限定、候补）。变更时**不改业务核心**。
2. 通知渠道会变（站内信、邮件、短信），且**通知失败不能让合法的报名消失**。
3. 名额与重复报名是所有报名方式共有的规则，不能在每个策略里各写一遍。
4. 业务规则要能脱离 HTTP 测试，便于回归（65 条 pytest 全部在服务层或 Flask test client 上运行）。

## 2. 职责分配

| 类 / 模块 | 职责 | 不负责 |
| --- | --- | --- |
| `web.create_app` + 路由 | HTTP、会话、表单解析、flash、模板渲染 | 业务规则、SQL |
| `RegistrationService` | 报名/取消/审批的事务编排、状态迁移、组装通知消息 | 具体报名规则（交给策略）、具体投递（交给通道） |
| `RegistrationPolicy`（抽象） | 公共名额规则 `check()`、声明 `decide()` 与 `requires_approval()` | 数据访问、通知 |
| `DirectPolicy` / `ApprovalPolicy` | 只回答“这条报名该是什么状态” | 名额检查（由基类统一） |
| `NotificationService` | 发布消息、逐通道投递、捕获异常、失败留痕 | 决定“何时通知”（由 Service 决定） |
| `INotificationChannel` 及实现 | 单一投递方式（站内信 / 审计） | 重试策略、业务判断 |
| `ActivityService` | 活动增改删、表单校验、软删除与连带通知 | 报名规则 |
| `repository` | SQL 与 Schema、参数化查询、事务外的读写工具 | 业务判断 |
| `entities` / `constants` | 数据结构、状态与错误码 | 行为 |

## 3. 策略模式：报名方式

### 3.1 问题

报名方式不同会导致“提交后状态不同、是否需要审批不同”。若写成 `if policy_type == 'DIRECT': ... else: ...`，
每增加一种方式就要改 `register()`，并且审批、统计、页面按钮都要跟着加分支，违反开闭原则。

### 3.2 方案

```
RegistrationPolicy (ABC)
├─ check(*, seats_left, capacity) -> None      # 公共规则：满员抛 SealError(CAPACITY_FULL)
├─ decide(seats_left) -> str        (abstract) # 该策略下报名后的状态
└─ requires_approval() -> bool      (abstract)
   ├─ DirectPolicy   : decide → 已通过,   requires_approval → False
   └─ ApprovalPolicy : decide → 待审核,   requires_approval → True
get_policy(code) -> RegistrationPolicy           # 模块级工厂，实例无状态可共享
```

`RegistrationService.register()` 里只有三步与策略相关：

```python
policy = get_policy(act["policy_type"])
left = capacity - repo.count_approved(conn, activity_id)
policy.check(seats_left=left, capacity=capacity)   # 公共规则
status = policy.decide(left)                        # 策略决定状态
```

### 3.3 名额检查属于公共规则，不属于策略

指导书 3.4-B 明确要求说明这一点。本项目的结论是：**名额检查放基类的模板方法 `check()`，不放各策略**。

理由：

1. 名额是活动的物理约束，与“报名方式”无关；任何策略都不允许超卖，写进策略会产生重复代码，
   且新增策略时容易漏写，导致超卖这一最严重的缺陷。
2. 策略的差异只在“通过还是待审核”，这是**状态判定**；名额是**前置条件**，两者变化原因不同（SRP）。
3. 批准时的复查（`approve`）也复用同一个 `check()`，保证“报名时”和“审批时”的口径完全一致——
   这正是 C8 能通过的结构性原因。
4. 新增策略（例如“抽签”）只需要实现“如何决定状态”，名额与重复报名自动继承。

### 3.4 备选方案与取舍

| 方案 | 优点 | 为什么没选 |
| --- | --- | --- |
| if/elif 分支 | 代码最少 | 新增方式要改核心方法，审批/统计/UI 都要跟着改，回归面大 |
| 表驱动配置（字典） | 无类膨胀 | 行为只能表达“状态字符串”，无法表达“是否需要审批 + 额外校验”，扩展时仍要写分支 |
| 策略模式（选中） | 新增方式只加类；公共规则集中在基类；可单测 | 类数量增加；需要在工厂注册（可接受） |

## 4. 观察者模式：通知

### 4.1 问题

报名/审批成功后要通知学生；通知方式可能增加（站内信、邮件、短信），而且通知系统故障不应影响报名。
若在 `register()` 里直接 `INSERT INTO message`，通知与业务耦合，新增渠道要改业务代码。

### 4.2 方案

- `NotificationService` 是**发布者**（Subject），持有 `channels: List[INotificationChannel]`。
- `INotificationChannel.deliver(conn, message) -> bool` 是**观察者接口**。
- 两个实现：
  - `InboxChannel`：写 `message` 表，按 `(student_id, activity_id, content)` 幂等去重；
  - `AuditChannel`：以 `student_id='__audit__'`、`kind='AUDIT'` 写审计行，同样按内容去重。
- `publish()` 逐通道 `try/except`，单个通道异常不影响其他通道，异常写入 `self.failures`，
  并**再尝试**写一条 `kind='NOTIFY_FAILED'` 的审计消息，保证“通知失败有痕迹”。

### 4.3 通知失败是否影响报名事务

**不影响。** 事务边界是：

```
BEGIN IMMEDIATE
  校验 → 插入/更新 registration
COMMIT                     ← 报名在此刻已经成立
publish(message)           ← 提交之后“尽力而为”，失败只留痕
```

理由：报名是学生的核心诉求，通知是派生结果。若把通知放进事务，一次 SMTP 超时就会回滚一条合法报名，
既不符合业务规则 6，也会让用户看到“明明点了报名却什么都没发生”。代价是极端情况下“报名成功但没有站内信”，
因此用 `NOTIFY_FAILED` 审计行 + “我的报名”页面兜底，学生仍能看到自己的记录。

### 4.4 如何避免重复通知

1. 站内信按 `(student_id, activity_id, content)` 唯一维度去重，重复 `publish` 同一条消息返回 `False`，不新增行。
2. 审计通道按 `content` 去重，审批重试不会产生多条“批准报名 #N”。
3. 通知的内容包含状态与剩余名额，天然区分不同事件（报名成功 / 审核通过 / 拒绝 / 取消）。

## 5. 设计原则对照

| 原则 | 体现 |
| --- | --- |
| SRP 单一职责 | 策略只决定状态；通道只投递；Service 只编排事务；repository 只管 SQL |
| OCP 开闭 | 新增报名方式 = 新增 Policy 子类 + 注册；新增渠道 = 新增 Channel + `register()` |
| LSP 里氏替换 | `DirectPolicy` / `ApprovalPolicy` 可互换，Service 只依赖 `RegistrationPolicy` 接口 |
| DIP 依赖倒置 | Service 依赖 `INotificationChannel` 抽象，不依赖具体通道；测试可注入故障通道 |
| ISP 接口隔离 | `INotificationChannel` 只有一个 `deliver`；`RegistrationPolicy` 只有 3 个方法 |
| 低耦合高内聚 | 域层不 import Flask；路由不写 SQL；模板只读 `stats` 与实体字段 |
| 防御式设计 | 服务层校验 + 数据库 CHECK 约束 + 部分唯一索引三层兜底 |

## 6. UML 类图说明（`class-diagram-v1.png`）

读图要点：

- 左侧实体列：`Activity`、`Student`、`Registration`、`Message` 都是不可变或纯数据对象（dataclass），
  不含业务方法，因此可以被序列化、比较、在测试里直接构造。
- 中间服务列：`RegistrationService` 组合 `NotificationService`（实心菱形），依赖 `RegistrationPolicy`
  与 `repository`（虚线箭头）。依赖只指向抽象/模块接口。
- 右侧策略列：`RegistrationPolicy` 是抽象类，`check()` 为具体方法（模板方法），`decide()` /
  `requires_approval()` 为抽象方法；`DirectPolicy`、`ApprovalPolicy` 继承它。
- 右下通知列：`NotificationService` 组合 1..* 个 `INotificationChannel`，`InboxChannel` / `AuditChannel` 实现接口。
- 底部两个 `<<module>>`：`repository`（SQL 与 Schema）与 `constants`（状态、策略编码、`SealError`）。
- 关联：`Registration --> Activity`、`Registration --> Student`，多重性为 0..* 对 1。

## 7. 时序图说明

### 7.1 报名（`seq-register.png`）

关键顺序：**校验 → 策略判定 → 插入 → COMMIT → 通知**。图中用 alt 片段给出四种分支：
已有有效报名、活动已开始、名额已满、成功（DIRECT / APPROVAL 两种状态）。
图右侧注解强调“通知在事务提交之后发送，通知失败不回滚报名”。

### 7.2 审批（`seq-approve.png`）

关键顺序：**取记录 → 校验状态为待审核 → 复查剩余名额 → 更新状态 + COMMIT → 通知（学生 + 审计）**。
alt 片段给出“名额已满 → 批准失败、状态保持待审核”与“批准成功”两条路径。
`approve()` 与 `register()` 共用 `check()`，因此两条路径的名额口径一致。

## 8. 为变更预留的扩展点（不含实现）

指导书 3.6 规定变更单发布前不得提前实现，因此下面只记录**设计上已经预留**的位置，baseline-v1 不落地：

| 可能的变更 | 预留点 | 预期影响 |
| --- | --- | --- |
| 新增报名方式（抽签/候补/班级限定） | `RegistrationPolicy` 子类 + `_POLICIES` 注册 + `POLICY_LABELS` | 只新增类；`register()` 不改；需补该策略的测试 |
| 新增通知渠道（邮件/短信） | 实现 `INotificationChannel.deliver` 并 `notifier.register(...)` | 域层不改；需补通道测试与失败留痕测试 |
| 名额扩容 / 候补转正 | `activity.capacity` 更新 + `approve` 复检逻辑复用 | 触及 `RegistrationService.approve`，需回归 C4/C8/C9 |
| 报名截止时间独立于活动开始时间 | 新增活动字段 + `register()` 前置校验 | 触及实体、表单、Schema、规则；回归面较大 |

这些判断也是将来 CR 到达时“变更影响分析”的起点。
