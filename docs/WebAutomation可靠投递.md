# Web Automation 可靠投递实现说明

## 1. 背景与修改前状态

P1-1 已实现配置驱动的周期采集和 SQLite 任务历史，P1-2 已实现告警增量对比、
新增与恢复回调，以及进程内 10、30、90 秒重试。修改前的回调重试依赖当前 Python
进程：Gateway 退出后，尚未执行的重试不会被恢复；达到尝试上限后也没有可查询、
可人工重投的死信记录。

本阶段对应《AIOPS_WebAutomation_Design.md》的以下部分：

- §16.4：失败重试、达到上限进入死信队列，以及人工重投；
- §17.4：任务持久化、幂等、至少一次投递、DLQ 和回调去重；
- §17.6：Gateway 重启后恢复被中断的投递。

## 2. 目标、范围与验收标准

### 2.1 目标

将 KuberPilot 告警回调从进程内临时重试改为可恢复的持久化投递，使 Gateway
重启、KuberPilot 暂时不可用或 HTTP 回调失败时，告警事件仍可继续投递。

### 2.2 范围

- 在项目内 SQLite 增加持久化投递任务；
- 使用幂等键去重相同告警事件；
- 按配置执行延迟重试，达到上限进入死信；
- Gateway 启动时恢复中断任务；
- 提供投递任务列表、详情和死信人工重投 API；
- 保证同一平台、同一告警的活动与恢复事件按生成顺序投递；
- 验证 KuberPilot 对重复 HTTP 回调不会重复创建告警。

### 2.3 非目标

- Redis、RQ 或 Celery 分布式队列；
- 多 Gateway 副本的分布式锁和水平扩展；
- 投递任务前端管理页面；
- Prometheus 指标、Grafana 看板和自动告警；
- 真实第三方运维平台的生产联调。

### 2.4 验收标准

| 编号 | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| 1 | 回调失败后任务和请求数据仍保存在 SQLite | Delivery Store 单元测试、故障注入数据库 | 通过 |
| 2 | Gateway 重启后恢复 `delivering` 任务 | Worker 启动恢复测试、故障注入重建 Store/Worker | 通过 |
| 3 | 按配置重试并在达到上限后进入 `dead_letter` | Worker 与 Store 单元测试 | 通过 |
| 4 | 死信可以通过 API 人工重投 | API 202、409、503 和 404 路径测试 | 通过 |
| 5 | 相同事件不会生成第二条投递任务 | 幂等键单元测试 | 通过 |
| 6 | 同一告警的后续事件不会越过前序死信 | 告警事件顺序测试 | 通过 |
| 7 | KuberPilot 容忍至少一次投递 | Django 重复回调测试只保留一条告警 | 通过 |
| 8 | 30 分钟反复故障注入后无积压和死信残留 | 1800 秒、182 条成功、无残留 | 通过 |
| 9 | 同一告警恢复后再次触发会创建新任务 | 完整生命周期回归测试产生 `new/recovered/new` 三次回调 | 通过 |
| 10 | Worker 遇到未预期异常后继续运行且健康状态可见 | 领取、回调、状态写回、关闭和健康接口测试 | 通过 |

## 3. 总体方案

### 3.1 持久化 Outbox

本实现采用 Outbox（待投递箱）模式。采集器识别告警变化后，不直接把内存中的
数据交给 HTTP 重试循环，而是先写入 `delivery_jobs` 表。告警快照与投递任务在
同一个 SQLite 事务中更新：

```text
周期采集
  -> 计算 new / recovered
  -> 同一事务写 delivery_jobs 并推进 alarm_snapshots
  -> DeliveryWorker 领取到期任务
  -> HTTP 回调 KuberPilot
```

只有数据库事务提交成功后才允许开始 HTTP 投递。进程在提交后、回调前退出时，
事件仍可从数据库恢复。快照可以在持久化后安全推进，后续周期采集不会反复生成
相同变化。

### 3.2 状态机

```text
pending -> delivering -> succeeded
                 |
                 +-> retry_wait -> delivering
                 |
                 +-> dead_letter -> pending（人工重投）
```

| 状态 | 含义 |
|---|---|
| `pending` | 已持久化，等待首次投递 |
| `delivering` | Worker 已领取，正在执行 HTTP 请求 |
| `retry_wait` | 本次失败，等待下一次到期 |
| `succeeded` | KuberPilot 已返回成功状态 |
| `dead_letter` | 达到最大尝试次数，等待人工处理 |

默认总共尝试 4 次：首次尝试加 3 次重试，重试间隔为 10、30、90 秒。

### 3.3 重启恢复

Gateway 启动时，Worker 将上次进程遗留的 `delivering` 任务改为立即到期的
`retry_wait`。随后按正常领取流程继续投递。已成功任务不会重新领取。

### 3.4 幂等与顺序

幂等键计算内容为：

```text
SHA-256(platform + alert_callback + event_id)
```

`event_id` 包含变化类型、告警指纹、告警发生时间，以及根据持久化投递历史计算的生命周期
序号。第一次生命周期保持原有事件 ID 计算方式；恢复后再次触发时序号递增，生成新的事件
和投递任务。同一次状态转换的重复采集仍复用已有任务。

系统采用至少一次投递语义：如果 HTTP 已成功但进程在写入成功状态前退出，任务
可能再次回调。KuberPilot 仍按告警 `fingerprint` 更新同一条记录，因此重复请求
不会创建第二条告警。

同一平台、同一告警指纹按 SQLite 写入顺序串行领取。前序任务处于重试或死信时，
后续恢复事件仍可入队，但不会提前发送，从而避免“先恢复、后活动”造成最终状态
错误。

### 3.5 Worker 异常隔离与健康状态

Worker 主循环为任务领取异常提供顶层保护和最长 30 秒的有限退避。单个回调或状态写回
异常只影响当前任务，当前批次的其他任务仍继续处理。已领取但未完成的任务会回到
`retry_wait`，达到最大尝试次数后进入 `dead_letter`；后台任务已经异常结束时，Gateway
关闭流程会记录故障但不会再次抛出该异常。

`GET /healthz` 的 `delivery_worker` 字段提供：

- `enabled`、`is_running`：是否启用和是否仍在运行；
- `backlog`、`dead_letter`：待处理和死信数量；
- `last_error`：最近异常阶段、异常类型和发生时间，不返回异常原文或敏感请求数据；
- `queue_error_type`：健康检查本身无法读取队列时的异常类型。

## 4. API

### 4.1 查询投递任务

```http
GET /api/v1/delivery-jobs?platform=mock_platform&status=retry_wait&limit=50
GET /api/v1/delivery-jobs/{job_id}
```

`status` 可选值为 `pending`、`delivering`、`retry_wait`、`succeeded` 和
`dead_letter`。

### 4.2 人工重投死信

```http
POST /api/v1/delivery-jobs/{job_id}/retry
```

- 目标不存在时返回 404；
- 目标不是死信时返回 409；
- 回调 Worker 未运行时返回 503，并保持原死信状态；
- 接受重投时返回 202，将尝试次数清零并重新进入 `pending`。

## 5. 配置

| 环境变量 | 默认值 | 说明 |
|---|---:|---|
| `WEB_AUTOMATION_CALLBACK_RETRY_DELAYS_SECONDS` | `10,30,90` | 每次失败后的等待秒数 |
| `WEB_AUTOMATION_DELIVERY_POLL_INTERVAL_SECONDS` | `1` | Worker 空闲轮询间隔，范围大于 0 且不超过 60 秒 |
| `WEB_AUTOMATION_DELIVERY_BATCH_SIZE` | `20` | 每次最多领取数量，范围 1～200 |
| `WEB_AUTOMATION_TASK_DATABASE_PATH` | `.runtime/collection-tasks.sqlite3` | 采集与投递共用的项目内数据库 |

回调令牌仍由 `web_automation/.env` 或部署环境注入，不写入任务数据、接口错误或
日志。数据库路径继续强制限制在 `web_automation` 目录内。

## 6. 文件变更

| 文件或目录 | 修改内容 |
|---|---|
| `web_automation/gateway/delivery/models.py` | 投递状态、任务和人工重投响应模型 |
| `web_automation/gateway/delivery/store.py` | SQLite Outbox、幂等、领取、重试、死信和恢复 |
| `web_automation/gateway/delivery/worker.py` | 后台轮询、单次 HTTP 投递和重试调度 |
| `web_automation/gateway/routes/deliveries.py` | 列表、详情和死信重投 API |
| `web_automation/gateway/alerts/callback.py` | HTTP 客户端改为单次请求，重试由 Worker 管理 |
| `web_automation/gateway/alerts/processor.py` | 告警变化先持久化，再触发投递 |
| `web_automation/gateway/dependencies.py` | 装配 Store、Callback Client 和 Worker |
| `web_automation/gateway/app.py` | 启停投递 Worker，注册 API 路由 |
| `web_automation/gateway/config.py` | 投递轮询与批量配置 |
| `web_automation/scripts/verify_reliable_delivery.py` | 可重复执行的故障注入验证 |
| `web_automation/tests/` | 持久化、恢复、死信、顺序、API 和后台 Worker 测试 |
| `backend/ops/tests.py` | KuberPilot 重复回调去重测试 |

本阶段没有 Django 模型或迁移变更。`delivery_jobs` 由 Gateway 在现有项目内
SQLite 中幂等建表。

## 7. 运行与验证

### 7.1 启动

先按现有流程配置 KuberPilot 回调并启动服务：

```powershell
Set-Location "<仓库根目录>"
.\tools\dev\configure-web-automation-callback.ps1
.\tools\dev\start-dev.ps1

Set-Location ".\web_automation"
.\scripts\start-local-demo.ps1
```

### 7.2 查询与重投

```powershell
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/delivery-jobs?limit=20"

$deadLetters = Invoke-RestMethod `
  "http://127.0.0.1:8010/api/v1/delivery-jobs?status=dead_letter"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8010/api/v1/delivery-jobs/$($deadLetters[0].job_id)/retry"
```

人工重投前应先修复 KuberPilot 地址、网络、令牌或服务状态；否则任务仍会再次失败。

### 7.3 自动测试

```powershell
Set-Location "<仓库根目录>\web_automation"
$env:TEMP = (New-Item -ItemType Directory -Force -Path ".runtime\tmp").FullName
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pytest -q
```

结果：77 项 Web Automation 测试通过。测试覆盖成功路径、HTTP 失败、重启恢复、
重试耗尽、人工重投、Worker 停用、跨生命周期幂等、同告警顺序、Worker 未预期异常
自恢复、健康状态以及 API 错误路径。

Django 定向测试：

```powershell
Set-Location "<仓库根目录>\backend"
python manage.py test `
  ops.tests.AlertWebhookIngestTests `
  aiops.tests.test_web_automation -v 2
```

结果：19 项通过，包括专用令牌校验和重复回调不重复创建告警。

前端兼容性构建：

```powershell
Set-Location "<仓库根目录>\frontend"
$env:npm_config_cache = (New-Item -ItemType Directory -Force -Path ".npm-cache").FullName
npm run build
```

结果：2203 个模块完成构建。

### 7.4 30 分钟故障注入

```powershell
Set-Location "<仓库根目录>\web_automation"
$env:TEMP = (New-Item -ItemType Directory -Force -Path ".runtime\tmp").FullName
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe .\scripts\verify_reliable_delivery.py `
  --duration-seconds 1800 `
  --progress-seconds 60 `
  --event-interval-seconds 10 `
  --database .runtime\verification\reliable-delivery-30m.sqlite3
```

验证使用真实本机 HTTP 请求和 SQLite 持久化，但回调接收端是本地测试服务，不是
生产 KuberPilot。脚本先验证固定故障阶段，再在 30 分钟内持续生成事件，并对部分
事件的第一次请求注入 HTTP 503。

实际结果：

- 请求持续时间：1800.0 秒；
- 最终投递状态：`succeeded=182`，无 `pending`、`retry_wait` 或 `dead_letter`；
- HTTP 请求：220 次，其中 182 次成功，其余为脚本主动注入的失败；
- 固定阶段：失败持久化、Store 重开恢复、`delivering` 重启恢复、进入死信、人工
  重投和幂等复用全部通过。

## 8. 安全、兼容性与边界

- 任务只保存标准化告警回调，不保存平台密码、Cookie 或回调令牌；
- HTTP 错误只记录异常类型和固定公开消息，不写响应体或敏感请求头；
- SQLite 和验证数据位于已忽略的 `web_automation/.runtime`；
- 投递查询 API 与现有 Gateway 任务 API 一样，依赖部署网络边界保护；尚未增加
  Gateway 自身的用户登录与 RBAC；
- SQLite 方案面向当前单 Gateway 原型。多副本部署时应将 `DeliveryJobStore`
  替换为 Redis/RQ 或 Celery，并增加分布式领取和锁；
- 本阶段没有投递任务前端页面，因此验收证据采用自动测试、API 和数据库状态，
  不使用缺乏额外证明价值的浏览器截图。

## 9. 总结

P1-3 将告警回调从“进程还在才能继续重试”升级为“事件先落盘、重启后继续投递”。
系统具备持久化重试、幂等去重、同告警顺序保护、死信查询和人工重投能力，并保持
KuberPilot 对重复回调的兼容。当前结论基于本地组件、HTTP 集成和故障注入验证，
不等同于多副本或真实生产环境验证。
