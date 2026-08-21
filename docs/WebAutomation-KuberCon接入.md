# Web Automation KuberCon 平台接入说明

本文记录 KuberPilot Web Automation 接入 KuberCon Kubernetes 测试平台的实现、
运行方式、安全边界和验证结果。文档不包含平台地址、账号密码、Cookie、内部资源详情
或测试截图。

## 1. 背景与修改前状态

修改前，Web Automation 已具备以下能力：

- 通过 Gateway 和 MCP 工具按需查询外部平台告警；
- 通过 MockOps 和 Legacy NOC 两种页面结构验证 Adapter 泛化；
- 通过周期任务、增量比较和持久化投递队列同步新增与恢复事件；
- 使用 `StandardAlarm` 向 KuberPilot 返回统一告警模型。

上述平台均由仓库内置服务模拟。KuberCon 是独立部署、具有自身登录页、集群路由和
告警接口的测试平台，原有代码无法识别其登录契约、内部接口和字段结构。

## 2. 目标、范围与验收标准

### 2.1 目标

实现 KuberCon Adapter，使 KuberPilot 能通过现有只读 MCP 工具完成以下链路：

```text
自然语言问题
  → KuberPilot AIOps Fast Path
  → web_platform.list_alarms
  → Web Automation Gateway
  → KuberCon Adapter
  → 浏览器登录/登录态复用
  → KuberCon 只读告警接口
  → StandardAlarm
  → 智能助手回答与调用审计
```

### 2.2 范围与非目标

本次包含：

- KuberCon 登录、登录态持久化和失效后重登；
- 自定义告警与内置告警的只读采集；
- 严重级别筛选、数量限制、排序和 `StandardAlarm` 转换；
- KuberCon 自然语言别名、MCP 注册和初始化命令；
- 本地安全配置脚本、脱敏冒烟脚本和自动化测试；
- KuberCon 测试平台只读联调和 KuberPilot 浏览器端到端验证。

本次不包含：

- 创建、删除或重启 Kubernetes 资源；
- 修改告警规则或确认、关闭告警；
- 故障注入、长时间稳定性或高并发验证；
- P1-4 运行监控和 P1-5 证据管理的未合并实现；
- 向 Git 提交平台地址、凭据、Cookie、运行数据库或内部截图。

### 2.3 验收结果

| 编号 | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| 1 | KuberCon Adapter 可被 MCP 注册表发现 | 注册测试 | 通过 |
| 2 | 集群路由和两类告警接口正确 | KuberCon Adapter 单元测试 | 通过 |
| 3 | 平台字段可转换为 `StandardAlarm` | 转换、生命周期与脱敏测试 | 通过 |
| 4 | 登录过期可重登，登录失败返回专用脱敏错误 | 异常和 MCP 错误测试 | 通过 |
| 5 | 本地 `.env` 可解析，进程环境变量优先 | Credential Provider 测试 | 通过 |
| 6 | KuberPilot 可识别 KuberCon 常见写法 | AIOps 聚焦测试 11 项 | 通过 |
| 7 | KuberCon 测试平台可完成只读 MCP 查询 | 脱敏冒烟返回 4 条 critical 告警 | 通过 |
| 8 | 智能助手可展示 KuberCon 告警并留下成功审计 | 浏览器端到端验证及本地截图 | 通过 |
| 9 | 既有 Web Automation 行为未回归 | 全量 97 项测试 | 通过 |
| 10 | 前端集成未被后端改动破坏 | Vue 生产构建，2203 modules | 通过 |

## 3. 方案与关键决策

### 3.1 浏览器负责认证，内部接口负责取数

KuberCon 没有向本项目开放稳定的公开告警 API，但网页登录后会调用内部 JSON 接口。
本实现使用 Playwright 完成登录和 Cookie 管理，再通过同一 `BrowserContext` 的请求能力
调用只读 GET 接口。该方式对应设计文档 §10.3.1 的演进路径：浏览器保留在认证层，
高频数据读取不依赖 DOM 逐行解析。

### 3.2 复用公共浏览器能力

原有两个 Adapter 分别实现了浏览器启动参数、平台 origin 和登录态文件路径。本次将
这些逻辑提取到 `adapters/browser.py`，并由 MockOps、Legacy NOC 和 KuberCon 共用。
登录失败异常也移动到 `adapters/base.py`，避免 Adapter 之间反向依赖。

### 3.3 管理员配置与模型输入隔离

KuberCon 的 URL、集群、凭据引用和允许网段由平台注册 YAML 管理。模型只能传入
`platform`、`severity` 和 `limit`，不能提供 URL、用户名、密码或 Cookie。

`adapter_options` 用于保存平台专属但非敏感的配置，例如 KuberCon 集群标识和是否采集
内置告警。集群标识只接受小写字母、数字、点和连字符，防止路径注入。

### 3.4 标准告警与生命周期标识

KuberCon 的 labels、annotations、状态和触发时间被映射为 `StandardAlarm`。告警 ID
由集群、告警集合、规则、资源和 `activeAt` 共同生成：重复采集同一活动告警时 ID
保持稳定；告警恢复后再次触发时，新的触发时间会生成新的生命周期 ID。

`raw_data` 只保留规则和指标等必要字段，不复制完整 labels、内部地址或平台响应正文。

## 4. 实施过程与文件变更

| 文件或目录 | 修改内容 | 修改原因 |
|---|---|---|
| `web_automation/adapters/kubercon.py` | 登录、会话恢复、双接口采集、转换和脱敏 | 实现 KuberCon 平台契约 |
| `web_automation/adapters/browser.py` | 公共浏览器启动、origin 和状态路径 helper | 消除三个 Adapter 的重复逻辑 |
| `web_automation/adapters/base.py` | 增加通用 `PlatformLoginError` | 统一登录失败语义 |
| `web_automation/adapters/mock_platform.py` | 复用公共浏览器 helper | 验证重构不改变既有行为 |
| `web_automation/adapters/legacy_ops_platform.py` | 复用公共浏览器 helper | 验证重构不改变既有行为 |
| `web_automation/platforms/models.py` | 增加受控 `adapter_options` | 支持平台专属非敏感配置 |
| `web_automation/credentials/environment.py` | 支持项目本地 `.env`，环境变量优先 | 兼容本地运行与部署注入 |
| `web_automation/gateway/mcp/alarm_tool.py` | 注册 KuberCon 并细分登录失败错误 | 接入现有 MCP 工具和脱敏错误边界 |
| `backend/aiops/services.py` | 增加 KuberCon 常见别名 | 支持自然语言 Fast Path |
| `backend/aiops/management/commands/setup_web_automation_demo.py` | 增加建议问题和环境别名 | 让初始化后的智能助手可直接查询 |
| `web_automation/scripts/configure-kubercon-local.ps1` | 交互式生成忽略配置 | 避免凭据出现在命令行和 Git |
| `web_automation/scripts/verify_kubercon.py` | 输出脱敏 MCP 冒烟摘要 | 提供可复现联调入口 |
| `web_automation/tests/`、`backend/aiops/tests/` | 增加成功、异常、权限和幂等测试 | 防止接入与既有能力回归 |
| `.gitattributes` | 统一文本换行并声明 PowerShell 编码策略 | 降低 Windows PowerShell 5.1 乱码风险 |

初始化命令对既有环境采用增量追加：保留用户自定义 aliases、description 和 created_by，
只补充缺失的 KuberCon 别名和必要启用状态，重复执行结果稳定。

## 5. 运行方法

前置条件：执行节点能够访问经授权的 KuberCon 测试平台，且已安装 Web Automation
依赖和 Playwright 浏览器。

在 `web_automation` 目录执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\configure-kubercon-local.ps1 `
  -BaseUrl "http://<authorized-internal-platform>:<port>" `
  -Cluster "<authorized-cluster>" `
  -Username "<authorized-account>"
```

脚本通过 `Read-Host -AsSecureString` 读取密码，并生成被 Git 忽略的 `.env` 与
`.runtime/platforms/kubercon.yaml`。密码不会进入命令行或终端输出。

执行只读冒烟：

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_kubercon.py `
  --severity critical `
  --limit 10
```

初始化 KuberPilot MCP 配置并启动服务后，可在智能助手输入：

```text
查看 KuberCon 当前告警
```

## 6. 验证过程与结果

### 6.1 聚焦测试

```powershell
python -m pytest `
  tests/unit/test_kubercon_adapter.py `
  tests/unit/test_alarm_tool.py `
  tests/unit/test_credentials.py `
  tests/unit/test_platform_loader.py `
  tests/unit/test_legacy_ops_adapter.py -q
```

结果：`26 passed`。

### 6.2 Web Automation 全量回归

```powershell
python -m pytest -q
```

结果：`97 passed`。存在一条 FastAPI TestClient 对旧 httpx 接口的弃用 warning，
与本次实现无关。

### 6.3 AIOps 测试

```powershell
python manage.py test aiops.tests.test_web_automation -v 2
```

结果：`11 tests passed`，覆盖自然语言别名、后端 MCP 权限允许/拒绝路径和初始化幂等性。

另执行 AIOps 全量 247 项测试，结果为 3 failures、3 errors，均位于未修改的
`aiops/tests/test_core.py`。错误包括既有测试函数签名、缺失断言参数和 SLO/知识图谱
断言，不涉及本次 KuberCon 文件；本次直接相关 11 项全部通过。

### 6.4 前端构建

```powershell
npm run build
```

结果：构建成功，处理 `2203 modules`。

### 6.5 KuberCon 测试平台只读联调

使用当前 PR 工作区代码执行 `verify_kubercon.py --severity critical --limit 10`，脱敏摘要为：

```json
{
  "is_error": false,
  "ok": true,
  "platform": "kubercon",
  "count": 4,
  "severity_counts": {
    "critical": 4,
    "warning": 0,
    "info": 0
  },
  "collection_method": "playwright_authenticated_session",
  "read_only": true,
  "error_code": null
}
```

告警数量是平台动态状态，不是 Adapter 内置固定数据。

### 6.6 浏览器端到端验证

启动当前 PR 工作区的 KuberPilot 前后端和 Gateway 后，在智能助手输入
“查看 KuberCon 当前告警”，页面成功展示 20 条告警及严重级别统计。调用审计中存在
状态为 `success` 的 `web_platform.list_alarms` 记录，展开后可见：

- `request_payload.platform` 为 `kubercon`；
- `response_summary.is_error` 为 `false`；
- 工具来自 `Web Automation Gateway`。

本地生成了查询结果和调用审计两张截图。截图含测试平台内部资源名称，因此保存在被
Git 忽略的 `web_automation/.runtime/e2e-kubercon`，不嵌入公开文档、不进入提交。

## 7. 安全、配置与兼容性

- Adapter 仅调用 KuberCon GET 告警接口，不提供写操作工具；
- 平台地址和凭据由管理员配置，不进入模型上下文；
- 进程环境变量优先于项目 `.env`，便于部署环境使用 Secret 注入；
- API 异常只返回状态码或异常类型，不返回平台响应正文；
- Cookie、浏览器状态、SQLite、日志和截图均位于 Git 忽略目录；
- `credential_id` 是凭据引用名，不代表账号本身一定只读；本次安全边界由 GET-only
  Adapter、无写工具和只读验证过程共同保证；
- `configure-kubercon-local.ps1` 使用 ASCII 文案并保存为 UTF-8 with BOM，可由
  Windows PowerShell 5.1 正确读取。

## 8. 已知限制与未验证项

- 未在 KuberCon 集群中主动触发和恢复一条新告警；
- 未执行 30 分钟以上周期采集或高并发测试；
- 未验证验证码、MFA、账号过期和密码轮换；
- KuberCon 内部接口不是公开稳定 API，平台升级后可能需要调整路径或字段；
- 本次只证明 KuberCon 测试平台接入，不等同于生产发布验收。

## 9. 总结

本次在已合并的 Web Automation 主线能力之上新增 KuberCon Adapter，完成浏览器认证、
登录态复用、内部只读告警接口采集、标准化转换、自然语言路由和调用审计闭环。代码通过
聚焦测试、97 项 Web Automation 回归、11 项 AIOps 聚焦测试、前端构建、KuberCon
测试平台只读冒烟和浏览器端到端验证，且未将平台地址、凭据或内部截图纳入提交。
