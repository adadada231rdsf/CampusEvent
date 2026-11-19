# AI_DEV_LOG —— CampusEvent 关键协作记录

- 项目：CampusEvent 校园活动报名系统（《软件工程》实验二）
- 学生：242806010116 宋逸轩
- 说明：按指导书附录 D.2 记录 5–10 条**有代表性**的协作，重点不是“AI 写了什么”，
  而是“我给了什么指令、AI 产出有什么问题、我如何判断与验证”。
- 提交对应：baseline-v1 之前的记录都属于同一版本；`commit` 列填标签或提交主题，精确 hash 见 `git log --oneline`。

| # | 时间 / commit | 任务与给 AI 的关键指令 | AI 产出与问题 | 学生判断 / 验证 |
| --- | --- | --- | --- | --- |
| 1 | 2026-11-18 / `baseline-v1`（设计阶段） | “先按指导书 3.4-A/B/C 出设计材料：用例图、UML 类图、报名与审批两张时序图；说明名额检查属于公共规则还是策略责任，不要写实现代码。” | 给出 6 个类的职责表 + 策略/观察者两种方案；初稿把名额检查写进了 `DirectPolicy` 与 `ApprovalPolicy` 各一份 | **否决**：名额是活动约束，与报名方式无关，写两份会在新增策略时漏写。要求移到基类 `check()`，并让审批复查复用同一方法。修改后与 B.2-3/C8 一致 |
| 2 | 2026-11-18 / 设计评审前 | “把用例说明写成可验收的：每个用例要有前置条件、主流程、异常分支和错误码，C1–C10 要能对应到用例。” | 产出了 8 个用例，但 C8（批准时满员失败）只写了“提示失败”，没有说明状态保持待审核 | 补充为：`approve` 复查 `seats_left<=0` 抛 `CAPACITY_FULL`，**状态不变**；并把它写进时序图的 alt 分支。后续 `test_approve_when_capacity_full_fails` 就按这句断言 |
| 3 | 2026-11-18 / 设计评审前 | “类图要能看出依赖方向：Service 依赖策略抽象而不是具体策略；通知通道是接口。” | 第一版类图把 `RegistrationService` 直接连到 `DirectPolicy`、`ApprovalPolicy`，还漏了 `repository` | 按依赖倒置改为 `Service ..> RegistrationPolicy`，具体策略只与抽象类有继承关系；补 `<<module>> repository` 与 `constants`。评审同学据此确认“新增策略不改 Service” |
| 4 | 2026-11-19 / 实现阶段 | “按类图实现域层，`register()` 里不允许出现 `if policy_type`；通知在事务提交后发送，失败要留痕但不能影响报名。” | 实现基本符合；但 `publish()` 把异常只记在内存 `self.failures`，数据库无痕迹 | **要求返工**：增加 `NOTIFY_FAILED` 审计行（含通道名、异常、原文），并用 try/except 包住二次写入。补测试 `test_notification_failure_does_not_lose_registration` |
| 5 | 2026-11-19 / 实现阶段 | “把所有业务规则列成清单，逐条指出代码位置与测试名，找不到就标红。” | 清单里 B.2-5 的“活动开始后不允许新增报名”标红——代码只检查了名额 | **确认缺陷 D-01**：在 `register()` 加 `start_at <= now → ACTIVITY_STARTED`；同时明确取消不受限，补两条测试。这是“让 AI 自查清单”最有效的一次 |
| 6 | 2026-11-19 / 测试阶段 | “测试要能脱离 HTTP：直接构造 `RegistrationService(conn, notifier)`；每条用例独立 SQLite 文件；时间用固定 FUTURE/PAST，不要依赖当前时间。” | 生成了 65 条用例；最初用 `tempfile.mkdtemp()` 建库，在本机报 `sqlite3.OperationalError: unable to open database file` | 定位为临时目录不可写，改为在 `tests/_tmpdb/` 下用 uuid 命名并 teardown 清理。另抽查 5 条用例，确认断言的是状态与数据，而不只是返回码 |
| 7 | 2026-11-19 / 测试阶段 | “补三类边界：待审核不占名额、满员时批准不超上限、绕过服务层直接插两行看索引是否拦住。” | 前两类有；第三类 AI 认为“索引只是优化”，没写 | **坚持要写**：部分唯一索引 `ux_reg_active` 是规则 4 的最后一道防线，必须有测试证明它有效。结果 `test_database_index_blocks_two_active_rows` 通过，也让报告可以写“三层兜底” |
| 8 | 2026-11-19 / 验收取证 | “用真实浏览器把 C1–C10 走一遍并截图，图里不能有工具自己的浮层，失败分支（满员/重复报名）也要有证据。” | 截图里出现“DeepSeek · 页面标题”浮层遮挡 flash；AI 先猜是页面伪元素，改 CSS 无效 | 用 DOM 探针定位到浏览器注入的 `#ego-agent-cursor-overlay`，改为截图前 `display:none` + CDP 整页截图。19 张图重截，逐张检查无浮层 |
| 9 | 2026-11-19 / 验收取证 | “满员和重复报名时按钮是隐藏的，怎么取证？” | AI 建议直接改数据造状态，风险是绕过真实入口 | **否决**：改用 `fetch(url, {method:'POST', redirect:'manual'})` 直接打真实路由，再读 flash。这样既验证了后端拒绝，又不伪造数据 |
| 10 | 2026-11-19 / 文档阶段 | “把测试结果、缺陷记录、可维护性基线整理成报告素材；文案要以当前操作者视角复读一遍。” | 发现批准失败提示“请先联系管理员扩大名额”，而操作者就是管理员 | **缺陷 D-03**：改为“请先扩大名额或拒绝该申请”，重截 `12-approve-fail-full.png`。同时要求报告里的每个结论都能指到代码、测试或截图 |
| 11 | 2026-11-19 / 部署阶段 | “服务器是阿里云轻量应用服务器，80 端口跑着实验一，把 CampusEvent 部署到 8080 并 systemd 常驻，别动实验一。” | 第一版 `tools/deploy.sh` 在 Windows 上写盘是 CRLF，服务器执行报 `set: pipefail\n: invalid option name`；另外本机没有 sshpass/paramiko，密码登录只能靠 `SSH_ASKPASS` + 一个打印密码的小 exe | 先用 `sed -i 's/\r$//'` 在服务器修好脚本，回头在仓库加 `.gitattributes`（`*.sh eol=lf`）根治；部署后核对 `systemctl is-enabled/is-active`、`curl 127.0.0.1:8080/login`=200、admin 登录 302，确认实验一 `studytask.service` 仍在 80 端口正常 |

## 统计

- 协作轮次：11 轮（设计 3、实现 2、测试 2、验收 2、文档 1、部署 1）。
- 被否决/返工的 AI 产出：6 处（#1 名额归属、#4 通知留痕、#5 开始时间校验、#7 索引测试、#9 伪造数据、#11 CRLF 部署脚本）。
- 通过 AI 发现并修复的缺陷：D-01、D-02（自查清单）、D-03（文案复读）。
- 结论：AI 在“生成骨架与穷举清单”上效率最高；在“业务规则边界、事务语义、面向谁写文案”上必须人工复核。
