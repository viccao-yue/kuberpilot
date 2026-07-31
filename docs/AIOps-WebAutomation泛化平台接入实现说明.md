# AIOps Web Automation 泛化平台接入实现说明

本文记录 KuberPilot AIOps Web Automation 的当前实现方式、组件边界、运行链路、
泛化验证结果与工程限制。当前实现通过 MCP 和 Playwright 为智能体提供外部运维
平台告警查询能力，证据等级达到本地多组件集成测试和 KuberPilot 浏览器端到端
验证；经授权的真实运维平台联调与生产环境验证尚未完成。

相关文档：

- `docs/AIOps智能体实现说明.md`：说明 KuberPilot 智能体、MCP、Skill 与审计链路。
- `docs/AIOps-MCP-Skill-双阶段应答设计.md`：说明 MCP 工具调用和双阶段应答。
- `docs/AIOps-WebAutomation网络预检实现说明.md`：说明网络预检实现。
- `docs/AIOps-WebAutomation告警闭环实现说明.md`：说明首个平台的端到端告警闭环。
- `docs/AIOps-WebAutomation多平台泛化验证说明.md`：说明第二个平台 Adapter 和泛化验证。

## 1. 背景与研究问题

KuberPilot 已有 AIOps 智能体、MCP 工具调用、权限控制和调用审计等基础能力。
设计文档 `AIOPS_WebAutomation_Design.md` 进一步提出了一个实际问题：

> 当 vCenter、HCI、私有云等运维平台没有开放 API，或者 API 暂时无法申请时，
> AIOps 如何安全地登录它们的 Web 管理页面并取得告警数据？

本阶段选择 Playwright 作为浏览器自动化执行方式，并增加独立的 Web Automation
Gateway。KuberPilot 不直接控制网页，而是通过 MCP 调用 Gateway 提供的受控工具；
Gateway 再根据管理员登记的平台配置选择对应 Adapter，登录平台、读取告警并转换
为统一格式。

这里的 MCP 可以理解为“智能体调用外部工具的统一接口约定”。模型或路由逻辑只
提供平台标识等受限参数，真正访问网络、登录网页和解析数据的仍是后端 Python
代码。这样可以把 AI 的理解能力和系统的执行权限分开。

## 2. 既有能力与扩展范围

开始研究前，KuberPilot 已具备以下相关基础：

- Vue 前端中的 AIOps 智能助手和智能体审计页面；
- Django 后端的 Action Router、MCP 客户端和工具调用审计；
- Agent 可以通过外部 HTTP MCP Server 调用 Python 工具；
- 写入或执行类动作可使用 Pending Action 和人工确认控制风险。

但当时没有独立的 Web Automation Gateway，也没有以下能力：

- 登录前分阶段检查目标平台网络；
- 隔离保存外部平台凭据；
- 使用 Playwright 登录没有开放接口的 Web 管理台；
- 把不同平台的告警转换为同一种数据结构；
- 在 KuberPilot 前端查询这些告警并留下 MCP 审计；
- 用两个结构不同的平台验证 Adapter 设计是否能够复用。

## 3. 阶段目标与完成情况

### 3.1 总目标

验证下面这条智能体工具链能否真实运行：

```text
用户自然语言提问
  → KuberPilot 识别平台和告警意图
  → 调用 MCP 工具 web_platform.list_alarms
  → Web Automation Gateway 校验平台与网络
  → Credential Provider 在服务内部解析凭据
  → Playwright Adapter 登录目标网页并采集数据
  → 转换为 StandardAlarm
  → KuberPilot 前端显示中文结果
  → 智能体审计记录工具调用
```

### 3.2 验收总表

| 编号 | 验收目标 | 主要证据 | 结论 |
|---|---|---|---|
| 1 | 能定位 URL、DNS、TCP、TLS、HTTP 哪一层不通 | 网络预检测试、`verify_local.py` | 通过 |
| 2 | 私有 CA HTTPS 不通过关闭证书校验来绕过 | 本地私有 CA 握手结果 | 通过 |
| 3 | AI 不能提供任意 URL，目标必须由管理员登记 | YAML 注册表、URL/CIDR 安全测试 | 通过 |
| 4 | Gateway 能用 Playwright 登录受保护平台并取得告警 | MockOps 本地集成测试 | 通过 |
| 5 | KuberPilot 前端能显示外部平台的 3 条告警 | 告警闭环截图 | 通过 |
| 6 | MCP 调用可审计，参数中不出现用户名和密码 | 智能体审计截图 | 通过 |
| 7 | 同一个 MCP 工具能接入 JSON API 和 HTML 表格两类平台 | 两个平台各返回 3 条告警 | 通过 |
| 8 | 平台差异被限制在 YAML、凭据和 Adapter 中 | 文件结构、单元测试、浏览器回归 | 通过 |
| 9 | KuberPilot 前端和统一告警模型无需为第二平台重写 | 多平台同会话截图 | 通过 |
| 10 | 能接入经授权的真实平台并稳定运行 | 尚未取得授权测试平台 | 未验证 |

## 4. 功能组成与实现结果

### 4.1 阶段一：网络互通预检

首先实现独立的 FastAPI Gateway，并在尝试登录前依次检查：

```text
平台配置 → URL 安全策略 → DNS → TCP → TLS → HTTP
```

这一阶段的价值不是简单返回“能通”或“不能通”，而是帮助使用者判断问题到底是
域名解析、端口、防火墙、证书还是网页服务造成的。实现还包括：

- 目标 URL 只能来自管理员维护的 YAML，不能由 AI 任意传入；
- DNS 解析结果必须落在平台允许的 CIDR 网段；
- 拒绝云元数据地址、URL 内嵌凭据和路径逃逸；
- HTTPS 使用系统 CA 或明确配置的私有 CA，不使用 `verify=False`；
- 提供 REST 接口和 MCP 工具 `web_platform.health`；
- 缓存、虚拟环境、证书和运行文件保存在仓库目录内；
- 提供本地运行脚本和 Docker Compose 基线配置。

阶段文档：

- [网络预检实现说明](AIOps-WebAutomation网络预检实现说明.md)

### 4.2 阶段二：单平台告警查询闭环

网络连通之后，实现了第一个可从 KuberPilot 前端操作的完整功能：

1. 仓库中的 `mock_platform` 启动一个真实可访问的本地 FastAPI 测试平台；
2. 平台提供登录页、会话 Cookie、告警页面和受保护的告警 JSON 接口；
3. Gateway 根据 `credential_id` 在内部解析凭据；
4. Playwright 启动系统 Edge，登录平台并读取受保护告警；
5. Adapter 把平台数据转换成 `StandardAlarm`；
6. Gateway 通过 `web_platform.list_alarms` 返回标准化结果；
7. KuberPilot 根据用户问题调用该工具，显示中文告警并写入工具调用审计。

在这一链路中，用户名、密码和 Cookie 不进入模型输入、MCP 参数或聊天内容。
当前功能只读，因此不产生外部写操作；如果未来增加确认、关闭或派单，必须接入
KuberPilot 的 Pending Action 和人工确认机制。

阶段文档：

- [告警闭环实现说明](AIOps-WebAutomation告警闭环实现说明.md)

关键页面证据：

![KuberPilot 显示外部平台告警](screenshots/web-automation-alarm-integration/03-alarm-answer.png)

![KuberPilot 记录 MCP 工具调用](screenshots/web-automation-alarm-integration/04-mcp-audit.png)

### 4.3 阶段三：第二平台 Adapter 与泛化验证

只接通一个平台无法说明设计具有泛化能力，因此又实现了
`legacy_ops_platform`。它不是复制第一平台，而是故意采用不同结构：

| 差异 | `mock_platform` | `legacy_ops_platform` |
|---|---|---|
| 登录字段 | 用户名、密码 | 操作员工号、访问口令 |
| 登录成功页 | `/dashboard` | `/console` |
| 告警来源 | 受保护 JSON API | 登录后 HTML 表格 |
| 告警级别 | critical/warning/info | P1/P2/P3 |
| 时间格式 | ISO 8601 | `YYYY/MM/DD HH:mm:ss` |
| 数据完整性 | 字段较完整 | 存在空说明和空资源类型 |
| 平台状态 | firing | OPEN/ACK |

新增的 `LegacyOpsPlatformAdapter` 负责处理这些差异，最终仍输出
`StandardAlarm`。KuberPilot 前端、MCP 工具名和中文展示逻辑没有为第二平台重写。

这证明当前方案具备的不是“所有平台零开发接入”，而是更实际的能力：

> 接入新平台时，主要新增平台 YAML、凭据引用和一个 Adapter；智能体、MCP 工具
> 合同和前端展示可以继续复用。

阶段文档：

- [多平台泛化验证说明](AIOps-WebAutomation多平台泛化验证说明.md)

关键页面证据：

![第二平台的 HTML 告警表](screenshots/web-automation-multi-platform/01-legacy-html-alarm-table.png)

![同一会话查询两个平台](screenshots/web-automation-multi-platform/03-two-platforms-one-chat.png)

![两个平台的 MCP 调用审计](screenshots/web-automation-multi-platform/04-multi-platform-mcp-audit.png)

## 5. 当前实现结构

```text
kuberpilot/
├── backend/aiops/
│   ├── services.py
│   │   └── 识别平台告警问题并调用统一 MCP 工具
│   ├── test_web_automation.py
│   └── management/commands/setup_web_automation_demo.py
├── frontend/
│   └── 复用原有智能助手和智能体审计页面
├── web_automation/
│   ├── gateway/
│   │   ├── FastAPI REST 接口
│   │   └── MCP health/list_alarms 工具
│   ├── network/
│   │   └── URL、DNS、TCP、TLS、HTTP 分层预检
│   ├── credentials/
│   │   └── 根据 credential_id 解析凭据
│   ├── adapters/
│   │   ├── mock_platform.py
│   │   └── legacy_ops_platform.py
│   ├── models/
│   │   └── StandardAlarm 标准模型
│   ├── platforms/definitions/
│   │   └── 管理员维护的平台白名单与 Adapter 配置
│   ├── mock_platform/
│   ├── legacy_ops_platform/
│   ├── tests/
│   └── scripts/
└── docs/
    ├── 三份 Web Automation 技术说明
    └── 两组浏览器验收截图
```

核心边界是：

- KuberPilot 负责理解用户问题、选择工具、展示结果和审计；
- MCP 规定 KuberPilot 与 Gateway 之间如何发现和调用工具；
- Gateway 负责网络、安全策略、凭据解析和 Adapter 分派；
- Adapter 负责某个平台具体的登录、页面导航和数据提取；
- `StandardAlarm` 隔离各个平台的数据差异；
- 管理员控制平台 URL、允许网段、Adapter 和 `credential_id`；
- AI 只传已登记的平台标识、筛选条件和数量限制。

## 6. 运行与演示方法

### 6.1 前置条件

- Windows PowerShell 5.1 或 PowerShell 7；
- Python、Node.js 和 Microsoft Edge；
- 项目依赖已按仓库脚本安装；
- 两个终端均从本仓库根目录开始操作。

### 6.2 启动 Web Automation

在终端一执行：

```powershell
Set-Location ".\web_automation"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-local-demo.ps1
```

本地服务：

| 服务 | 地址 |
|---|---|
| Gateway | `http://127.0.0.1:8010` |
| MockOps | `http://127.0.0.1:8011` |
| Legacy NOC | `http://127.0.0.1:8012` |
| 私有 CA 测试平台 | `https://127.0.0.1:8443` |

### 6.3 初始化并启动 KuberPilot

在终端二执行：

```powershell
Set-Location ".\backend"
python manage.py setup_web_automation_demo
Set-Location ".."
Set-ExecutionPolicy -Scope Process Bypass
.\tools\dev\start-dev.ps1
```

打开 `http://127.0.0.1:3000`，使用本地演示账号登录，进入
“AIOps → 智能助手”，依次输入：

```text
查看legacy_ops_platform当前告警
查看mock_platform当前告警
```

然后进入“AIOps → 智能体审计”，查看
`mcp::Web Automation Gateway::web_platform.list_alarms` 调用。

### 6.4 自动验证

```powershell
Set-Location ".\web_automation"
.\scripts\run-tests.ps1
.\.venv\Scripts\python.exe .\scripts\verify_local.py
```

KuberPilot 后端专项测试：

```powershell
Set-Location ".\backend"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPYCACHEPREFIX = (Resolve-Path ".\.pycache").Path
$env:TEMP = (Resolve-Path ".\.tmp").Path
$env:TMP = $env:TEMP
python manage.py test aiops.test_web_automation
```

前端生产构建：

```powershell
Set-Location ".\frontend"
npm run build
```

### 6.5 验证结果

| 检查项 | 验证结果 | 结论 |
|---|---|---|
| Web Automation 单元与集成测试 | `32 passed` | 通过 |
| KuberPilot Web Automation 专项测试 | `4 tests`，`OK` | 通过 |
| Gateway 本地多组件集成 | Gateway、HTTP、私有 CA HTTPS 和 MCP health 均成功 | 通过 |
| 两个平台真实 Adapter 调用 | 两个平台各返回 3 条告警，采集方式为 Playwright 登录会话 | 通过 |
| Vue 生产构建 | `2191 modules transformed`，构建成功 | 通过 |
| 技术文档静态检查 | 文档结构、图片路径和 UTF-8 编码检查通过 | 通过 |

页面截图来自对应功能版本的浏览器端到端验收，自动截图脚本保留在仓库中，可按
各技术说明中的验证命令重新生成。

## 7. 安全与工程约束

- 当前只提供网络检查和告警查询等只读能力；
- AI 不能传任意 URL，目标平台必须先由管理员登记；
- 平台 URL 的 DNS 结果受允许网段限制；
- HTTPS 必须正确验证 CA，不通过关闭 TLS 校验绕过；
- 用户名和密码由 Credential Provider 解析，不进入 MCP 参数；
- 两个平台使用不同 `credential_id`；
- 浏览器会话、证书、缓存和日志等运行数据位于 Git 忽略目录；
- 仓库不提交真实 Token、生产账号、Cookie、客户数据或私有 CA 私钥；
- PowerShell 5.1 脚本按项目规则使用 UTF-8 with BOM；
- 写操作不属于当前实现；扩展此类能力必须增加 RBAC、Preflight、Pending Action
  和人工确认。

## 8. 已知限制与结论边界

1. `mock_platform` 和 `legacy_ops_platform` 都是仓库内真实运行的测试服务，但数据是
   本地演示数据，不是真实业务环境的生产告警。
2. 当前结果证明两种差异较大的本地平台可通过统一 Adapter 合同接入，不能据此
   宣称所有真实平台无需开发即可接入。
3. 尚未验证验证码、MFA、SSO、iframe、动态虚拟表格和复杂分页。
4. 真实页面改版会影响选择器；契约检测、失败截图和自动恢复机制尚未实现。
5. 当前环境变量凭据提供器适合实验；生产应接 Vault、Kubernetes Secret 或企业
   已有密钥管理系统。
6. 尚未验证多实例调度、连续采集、高可用、限流和生产容量。
7. Docker Compose 配置是可选复现基线；当前验证不包含镜像构建和容器运行。

## 9. 实现价值

当前实现验证了设计方案中的几项关键假设：

- **网络互通**：在登录前可以精确识别网络和证书问题；
- **管理员账号与密码**：凭据可以由 Gateway 内部管理，不交给 AI；
- **MCP 工具化**：KuberPilot 能用统一方式调用外部浏览器自动化能力；
- **平台泛化**：JSON API 平台和纯 HTML 表格平台可以通过不同 Adapter 输出同一
  告警模型；
- **前端闭环**：结果不是停留在 Python 测试，而是能在智能助手中显示并在审计页
  留痕；
- **安全边界**：平台、URL、凭据和写操作权限仍由后端与管理员控制。

因此，当前实现形成了可供技术评审和演示的本地技术原型，为真实平台联调提供
网络预检、凭据隔离、Adapter 扩展、统一告警模型、MCP 调用和审计等可复用骨架。

## 10. 总结

当前实现从 KuberPilot 原有 MCP 和智能体能力出发，完成了网络预检、凭据隔离、
Playwright 登录、告警采集、标准化、MCP 暴露、前端中文展示和审计闭环，并使用
两个登录方式、数据来源和字段格式不同的本地平台验证了 Adapter 泛化思路。

当前实现达到“可运行、可测试、可演示、可审查”的本地技术原型水平。结论限定于
两个差异化本地测试平台；经授权的真实平台联调和生产环境验证尚未完成。
