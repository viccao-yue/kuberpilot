# KuberPilot Web Automation Gateway

本目录实现目标平台网络预检、只读告警采集、周期采集任务中心和告警增量回调。
Gateway 通过 REST 与 MCP 工具提供按需查询，通过 APScheduler 按平台配置定时
采集告警，并通过持久化投递队列将新增与恢复事件推送到 KuberPilot 告警中心。

实现边界、任务 API、验证结果和未完成的生产化能力见
[`docs/WebAutomation定时采集.md`](../docs/WebAutomation定时采集.md)和
[`docs/WebAutomation告警增量闭环.md`](../docs/WebAutomation告警增量闭环.md)，
可靠投递、重启恢复和死信重投见
[`docs/WebAutomation可靠投递.md`](../docs/WebAutomation可靠投递.md)。

## 启用 KuberPilot 告警回调

先启动或配置好 KuberPilot 后端，再在仓库根目录执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\dev\configure-web-automation-callback.ps1
```

脚本会生成仅保存在本地 `web_automation/.env` 的随机回调令牌，并为 KuberPilot
创建或更新对应的告警集成。令牌不会写入 Git，也不会输出到终端。随后启动
KuberPilot 和本地演示平台：

```powershell
.\tools\dev\start-dev.ps1
Set-Location ".\web_automation"
.\scripts\start-local-demo.ps1
```

在 `http://127.0.0.1:8011/alarms` 或 `http://127.0.0.1:8012/events`
登录后，可使用页面上的演示按钮新增或恢复告警。等待下一次周期采集后，在
KuberPilot `http://127.0.0.1:3000/alerts` 中可看到同一告警从“活动”变为“已恢复”。
演示控制只在 `WEB_AUTOMATION_ENABLE_DEMO_CONTROLS=1` 时启用。

## 本地一键演示

在 Windows PowerShell 5.1 或 PowerShell 7 中执行：

```powershell
Set-Location ".\web_automation"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-local-demo.ps1
```

脚本会在项目内创建 `.venv`、`.cache`、`.runtime`，并启动：

- Gateway：`http://127.0.0.1:8010`
- HTTP 模拟平台：`http://127.0.0.1:8011`
- 旧版 HTML 运维平台：`http://127.0.0.1:8012`
- 私有 CA HTTPS 模拟平台：`https://127.0.0.1:8443`

按 `Ctrl+C` 后，脚本会关闭它启动的三个模拟平台进程。

另开终端验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8010/healthz

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8010/api/v1/platforms/mock_platform/connectivity-check"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8010/api/v1/platforms/mock_private_ca/connectivity-check"

# 手动提交一次告警采集任务
$task = Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"platform":"mock_platform","severity":"all","limit":20}' `
  -Uri "http://127.0.0.1:8010/api/v1/collection-tasks"

# 查看任务详情和最近任务
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/collection-tasks/$($task.task.task_id)"
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/collection-tasks?limit=20"

# 查看待重试或死信投递任务
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/delivery-jobs?status=retry_wait"
Invoke-RestMethod "http://127.0.0.1:8010/api/v1/delivery-jobs?status=dead_letter"

# 修复回调故障后，人工重投一条死信任务
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8010/api/v1/delivery-jobs/<job_id>/retry"
```

两个演示平台的 YAML 均配置为每 60 秒采集一次告警。任务会经历
`queued -> running -> succeeded/failed`，结果持久化到项目内部的
`.runtime/collection-tasks.sqlite3`。同一平台已有活动任务时，新任务返回 HTTP 409，
防止浏览器任务重叠。

告警回调会先持久化到同一个项目内 SQLite 文件，再由后台投递器发送。状态依次为
`pending -> delivering -> retry_wait -> succeeded`；达到最大尝试次数后进入
`dead_letter`。Gateway 重启会恢复停留在 `delivering` 的任务，重复事件由幂等键复用
原任务，不会生成第二条投递记录。

如需关闭定时调度但保留手动任务 API，可在本地 `.env` 设置：

```text
WEB_AUTOMATION_SCHEDULER_ENABLED=0
```

## 自动验证

```powershell
.\scripts\run-tests.ps1
.\.venv\Scripts\python.exe .\scripts\verify_local.py
```

自动验证同时覆盖 `mock_platform` 的受保护 JSON API 和
`legacy_ops_platform` 的 HTML 表格解析。后者没有告警 API，用于证明同一个 MCP
工具可以通过不同 Adapter 接入页面结构不同的平台。

## Docker Compose

在仓库根目录执行：

```powershell
Set-Location "<KuberPilot 仓库根目录>"
docker compose -f compose.web-automation.yml up --build
```

停止服务：

```powershell
docker compose -f compose.web-automation.yml down
```

不要随意追加 `-v`，它会删除数据卷。Compose 配置提供 Gateway、两个 HTTP 测试
平台和私有 CA HTTPS 测试服务，用于本地复现与验证。

## 添加真实平台

在 `platforms/definitions` 中新增 YAML。AI 只能传 `platform` 标识，不能传任意
URL；目标 URL、允许网段、CA 和代理均由管理员配置。

真实私有 CA 放入项目内 `certs` 或管理员指定的受控路径，但不得提交 Git。禁止用
`verify=False` 代替正确的 CA 配置。
