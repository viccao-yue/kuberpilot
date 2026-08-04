# KuberPilot Web Automation Gateway

本目录实现目标平台网络预检，按 URL 策略、DNS、TCP、TLS、HTTP 五层定位故障，
并通过 REST 与 MCP 工具 `web_platform.health` 对外提供只读检查。

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
