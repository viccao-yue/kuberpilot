# AIOps Web Automation 定时采集与任务中心实现说明

本文说明 KuberPilot Web Automation 从 P0“按需查询”向 P1“周期采集”演进的
第一阶段实现。当前版本在 Gateway 内增加配置驱动的告警调度、持久化采集任务记录、
任务查询 API 和同平台重叠保护，并继续复用 P0 的网络预检、Credential Provider、
Playwright Adapter 与统一告警模型。

当前证据等级为本地单元测试、多组件集成测试和 30 分钟连续运行验证。两个目标平台
仍是仓库内的 MockOps 与 Legacy NOC 演示平台，尚未进行真实运维平台或生产环境验证。

## 1. 背景与修改前状态

P0 已经跑通以下按需查询链路：

```text
KuberPilot 用户提问
  → MCP web_platform.list_alarms
  → Gateway 网络预检与凭据解析
  → Playwright Adapter 登录目标平台
  → StandardAlarm 标准化
  → KuberPilot 返回告警并记录审计
```

这条链路需要用户主动提问才会执行。修改前没有周期调度器，没有独立的采集任务编号，
也不能查询某次采集何时开始、是否成功、执行了多久。若同一平台被重复触发，还缺少
明确的任务级重叠保护。

本次实现对应 `AIOPS_WebAutomation_Design.md` 的以下内容：

- §16“定时采集与生产调度”中的配置驱动周期采集；
- §16.2 中的 APScheduler、`coalesce` 和 `max_instances=1`；
- §17.4 中任务持久化与任务标识的基础部分；
- §17.5 中按平台限制并发的基础部分；
- §19.1 P1“稳定周期采集”的第一阶段。

## 2. 目标、范围与验收标准

### 2.1 目标

在不破坏 P0 手动 MCP 查询的前提下，使 Gateway 能按平台配置自动采集告警，并让
每次采集都形成可查询、可追踪的任务记录。

### 2.2 本次范围

- 在平台 YAML 中配置告警采集间隔；
- Gateway 启动时加载两个演示平台的周期任务；
- 任务状态按 `queued → running → succeeded/failed` 流转；
- 任务记录保存到项目目录内的 SQLite 文件；
- 提供创建任务、查询任务列表和查询任务详情的 REST API；
- 同一平台存在活动任务时返回 HTTP 409，避免任务重叠；
- Gateway 重启后保留历史任务，并把中断任务标记为失败后释放平台锁；
- 保留现有 `web_platform.health` 和 `web_platform.list_alarms` MCP 工具行为。

### 2.3 非目标

以下能力不属于 P1-1 本身；其中告警增量闭环已由同一交付中的 P1-2 完成，
其余项目仍属于后续生产化范围：

- Redis/RQ/Celery 分布式任务队列和多副本调度锁；
- 指数退避重试、死信队列和人工重投；
- 告警增量对比、去重、恢复事件与回调 KuberPilot（已在 P1-2 完成）；
- Prometheus 指标、Grafana 看板与生产告警规则；
- 常驻浏览器 Context 与登录态长期复用；
- 真实运维平台、30 天或 7×24 生产稳定性验证。

### 2.4 验收标准

| 编号 | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| 1 | 两个平台能按 YAML 周期自动创建采集任务 | 30 分钟各成功 30 次、失败 0 次 | 通过 |
| 2 | 成功任务包含平台、状态、时间、耗时和标准化结果 | 任务详情 API、集成测试 | 通过 |
| 3 | 失败任务保存脱敏错误码和错误消息 | `test_collection_task_manager.py` | 通过 |
| 4 | 同一平台活动任务不重叠 | Store 单元测试、API 409 测试 | 通过 |
| 5 | Gateway 重启后历史保留，中断任务不永久阻塞 | SQLite 重开与中断恢复测试 | 通过 |
| 6 | 手动任务支持创建、列表和详情查询 | API 集成测试 | 通过 |
| 7 | P0 网络预检、Adapter 与 MCP 查询没有回归 | Web Automation 全量测试 | 44 项通过 |
| 8 | KuberPilot Web Automation 专项和前端构建没有回归 | Django 专项测试、Vue 构建 | 9 项通过，构建通过 |

## 3. 方案与关键决策

### 3.1 执行链路

```text
平台 YAML 的采集间隔
  → APScheduler 周期触发
  → CollectionTaskManager 创建 task_id
  → SQLite 原子检查同平台是否已有活动任务
  → 复用 call_alarm_tool
  → 网络预检 → 凭据解析 → Adapter 采集与标准化
  → 记录 succeeded 或 failed、耗时和结果
  → 任务中心 REST API 查询
```

手动 API 与定时调度只在“触发来源”上不同，后续都进入同一个
`CollectionTaskManager`。这样不会出现定时采集和 MCP 查询分别维护两套登录、解析
或错误处理逻辑。

### 3.2 为什么使用 APScheduler

设计文档明确建议 Gateway 内置 APScheduler。当前平台数量少、任务频率低，内置
调度器比立即引入 Celery 更容易验证核心链路。每个任务配置：

- `coalesce=True`：服务短暂停顿后，错过多次只补一次；
- `max_instances=1`：同一个调度 Job 不并行执行；
- `misfire_grace_time`：限定延迟任务可被补执行的时间。

### 3.3 为什么第一阶段使用 SQLite

P1-1 需要验证任务状态和重启后历史保留，但还不需要多 Gateway 副本。SQLite 无需
新增外部服务，数据文件固定在 `web_automation/.runtime`，适合本地和单实例原型。
任务创建使用 `BEGIN IMMEDIATE` 原子检查同平台活动任务，避免两个请求同时通过。

SQLite 不是最终的多副本队列。进入分布式部署前，应按设计文档迁移到 Redis +
RQ/Celery，并增加分布式锁、重试和死信队列。

## 4. 实施过程与文件变更

| 文件或目录 | 修改内容 | 修改原因 |
|---|---|---|
| `web_automation/gateway/tasks/models.py` | 定义任务状态、触发来源和 API 模型 | 固定任务中心的数据合同 |
| `web_automation/gateway/tasks/store.py` | SQLite 建表、状态更新、筛选和原子防重叠 | 持久化任务历史并控制单平台并发 |
| `web_automation/gateway/tasks/manager.py` | 创建任务、后台执行、成功/失败落库 | 统一手动与定时采集执行路径 |
| `web_automation/gateway/tasks/scheduler.py` | 从平台配置注册 APScheduler Job | 实现配置驱动周期采集 |
| `web_automation/gateway/routes/tasks.py` | 创建、列表、详情 REST API | 提供任务中心查询入口 |
| `web_automation/gateway/app.py` | 管理调度器生命周期并注册 API | 随 Gateway 启停调度器 |
| `web_automation/platforms/models.py` | 增加采集间隔配置字段 | 对 YAML 配置做范围校验 |
| `web_automation/platforms/*definitions/*.yaml` | 两个平台配置 60 秒告警采集 | 提供可复现的演示调度 |
| `web_automation/requirements.txt` | 增加 APScheduler | 引入设计文档指定调度器 |
| `web_automation/scripts/*.ps1` | 启动前检查 APScheduler 依赖 | 保证旧虚拟环境可自动补依赖 |
| `web_automation/scripts/verify_scheduled_collection.py` | 有界连续运行验证 | 统计验证期间两平台成功与失败任务 |
| `web_automation/tests/` | 增加 Store、Manager、Scheduler 和 API 测试 | 覆盖状态、错误、恢复和重叠边界 |

## 5. 运行方法

### 5.1 启动完整本地演示

在 Windows PowerShell 中执行：

```powershell
Set-Location "<仓库根目录>\web_automation"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-local-demo.ps1
```

启动后地址：

- Gateway：`http://127.0.0.1:8010`
- API 文档：`http://127.0.0.1:8010/docs`
- MockOps：`http://127.0.0.1:8011/login`
- Legacy NOC：`http://127.0.0.1:8012/auth/signin`

### 5.2 手动创建并查询采集任务

```powershell
$task = Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"platform":"mock_platform","severity":"all","limit":20}' `
  -Uri "http://127.0.0.1:8010/api/v1/collection-tasks"

$taskId = $task.task.task_id
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/collection-tasks/$taskId"
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/collection-tasks?limit=20"
```

### 5.3 运行测试和连续采集验证

```powershell
.\scripts\run-tests.ps1

.\.venv\Scripts\python.exe .\scripts\verify_scheduled_collection.py `
  --duration-seconds 1800 `
  --poll-seconds 10
```

连续验证脚本只统计脚本启动后新产生的 `scheduled` 任务。两个平台至少各成功一次、
没有失败任务，并且实际运行达到指定时长时才返回退出码 0。

## 6. 验证过程与结果

### 6.1 自动测试

```text
web_automation 全量：44 passed
Django Web Automation 专项：9 tests，OK
Vue 生产构建：2203 modules transformed，built successfully
```

还执行了 `python manage.py test aiops -v 2`。主分支基线的 245 项测试中有 239 项
通过，3 项失败、3 项错误。失败位于既有 `aiops.tests.test_core`，包括测试函数参数
错误及知识图谱/SLO 断言；本次 diff 没有修改 `backend/`。因此不能把 Django AIOps
全量回归写成通过，但与 Web Automation 直接相关的 9 项专项测试全部通过。

手动 API 联调同时验证了两条路径：

- 平台空闲时创建任务返回 HTTP 202，任务随后变为 `succeeded`，critical 筛选返回
  1 条告警，耗时 1186 ms；
- 定时任务占用同一平台时，手动创建返回 HTTP 409 和活动 `task_id`，证明重叠保护
  在真实 Gateway 进程中生效。

连续验证结束后停止并重新启动 Gateway（关闭调度，避免产生新任务），任务 API 仍
查询到 67 条历史记录，活动任务为 0，说明项目内 SQLite 历史在进程重启后保留，
且没有遗留 `queued/running` 状态永久占用平台。

### 6.2 30 分钟连续周期采集

```json
{
  "gateway_health": "ok",
  "requested_duration_seconds": 1800,
  "elapsed_seconds": 1800.0,
  "scheduled_success_counts": {
    "mock_platform": 30,
    "legacy_ops_platform": 30
  },
  "failed_task_ids": [],
  "ok": true
}
```

这项验证属于本地演示平台的多组件集成测试，不等于真实平台联调，也不能替代
设计文档要求的 7×24 生产稳定性验证。

## 7. 安全、配置与兼容性

- 调度配置由管理员维护的 YAML 提供，AI 和普通 API 调用者不能提交任意 URL；
- 定时任务继续使用 `credential_id`，数据库不保存用户名、密码、Cookie 或 Token；
- 任务失败只保存受控错误码和异常类型，不保存原始凭据或浏览器会话；
- SQLite、日志、缓存和浏览器运行文件位于 `.runtime`/`.cache`，均不提交 Git；
- JSON 响应显式声明 UTF-8；PowerShell 5.1 脚本保持 UTF-8 BOM；
- 当前任务 API 沿用 Gateway 的受信网络边界，尚未增加独立用户认证。生产部署应通过
  内网、反向代理或服务认证限制访问。

## 8. 已知限制与未验证项

- 调度 Job 在启动时从 YAML 重建，尚未使用 Redis 保存调度器状态；
- SQLite 只适合单 Gateway 实例，不支持跨主机分布式锁；
- 当前失败会留下任务记录，但不会自动重试或进入死信队列；
- 当前每次采集仍会走 Playwright 登录流程，尚未实现常驻登录态；
- P1-1 只保存全量标准化告警；新增、恢复和指纹比较由 P1-2 补充；
- P1-1 不回调 KuberPilot；P1-2 已将新增和恢复事件接入现有告警中心；
- 未连接真实运维平台，未验证 7×24 与成功率 ≥95% 的生产指标。

## 9. 总结

P1-1 把 P0 的按需告警查询扩展为可配置的周期采集，并增加了持久化任务记录、
状态查询、失败记录、重启恢复和同平台重叠保护。它证明了“两个 Adapter 可以被同一
调度与任务框架持续调用”，但仍是单实例、本地演示平台上的生产化基础原型；完整
P1-2 已在此基础上补充增量去重与告警回调；后续仍需要可靠队列、持久化重试/DLQ、
监控和真实平台稳定性验证。
