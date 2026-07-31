# AIOps Web Automation 网络预检实现说明

> 文档版本：v1.0
> 实现目录：`web_automation/`
> 实现范围：URL 安全策略、DNS、TCP、TLS、HTTP、REST、MCP、模拟平台与本地验收
> 非本期范围：管理员登录、凭据管理、Playwright 页面操作、资源/告警采集

---

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 设计原则](#2-设计原则)
- [3. 总体架构](#3-总体架构)
- [4. 文件与模块设计](#4-文件与模块设计)
- [5. 分层检查流程](#5-分层检查流程)
- [6. 平台配置与安全边界](#6-平台配置与安全边界)
- [7. REST 与 MCP 接口](#7-rest-与-mcp-接口)
- [8. 本地模拟环境](#8-本地模拟环境)
- [9. 本地运行与验证](#9-本地运行与验证)
- [10. Docker Compose 部署](#10-docker-compose-部署)
- [11. 测试与验收结果](#11-测试与验收结果)
- [12. 错误码与排障](#12-错误码与排障)
- [13. 安全设计](#13-安全设计)
- [14. 已知边界](#14-已知边界)

---

## 1. 背景与目标

Web Automation 在登录 vCenter、HCI、OpenStack 等管理台前，需要先确认执行节点
是否真正具备网络访问条件。若直接启动 Playwright，DNS、端口、证书、代理、登录
页面等问题会统一表现为“登录失败”或“超时”，无法快速定位根因。

当前实现新增独立的 Web Automation Gateway 网络预检能力：

```text
管理员登记平台
        ↓
URL 安全策略
        ↓
DNS → TCP → TLS → HTTP
        ↓
ConnectivityReport
        ↓
REST / MCP(web_platform.health)
        ↓
KuberPilot Agent 与运维人员
```

本期目标：

1. 在登录前定位网络故障层次；
2. 支持普通 HTTP 与私有 CA HTTPS 测试；
3. 使用稳定、可审计的结构化报告；
4. 与 KuberPilot 现有 HTTP MCP 客户端协议兼容；
5. 防止模型把网络检查器变成任意 URL 访问器；
6. 保持缓存、证书、日志和运行文件位于项目目录。

---

## 2. 设计原则

| 原则 | 实现 |
|---|---|
| 配置归管理员 | 目标 URL 只从 YAML 注册表读取 |
| AI 最小输入 | MCP 只接收 `platform` |
| 分层定位 | URL、DNS、TCP、TLS、HTTP 分开报告 |
| 失败短路 | DNS 失败后不继续 TCP；TLS 失败后不请求 HTTP |
| 不绕过 TLS | 不使用 `verify=False` |
| 不采集页面 | HTTP 预检不保存响应正文 |
| 只读 | 不登录、不提交表单、不修改平台 |
| 项目内落盘 | `.venv/.cache/.runtime/logs` 都在副本内 |
| 独立服务 | 不向巨型 `backend/aiops/services.py` 塞平台网络代码 |

---

## 3. 总体架构

```text
┌──────────────────────────────────────────────────────────┐
│ KuberPilot AIOps                                        │
│ HTTP MCP Client → initialize → tools/list → tools/call  │
└───────────────────────┬──────────────────────────────────┘
                        │ POST /mcp
┌───────────────────────▼──────────────────────────────────┐
│ Web Automation Gateway (FastAPI)                        │
│ REST API │ MCP Router │ PlatformRegistry                │
└───────────────────────┬──────────────────────────────────┘
                        │ platform id
┌───────────────────────▼──────────────────────────────────┐
│ ConnectivityChecker                                    │
│ URL Policy → DNS → TCP → TLS → HTTP                    │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTPS/HTTP
┌───────────────────────▼──────────────────────────────────┐
│ vCenter / HCI / 私有云 / 本地模拟管理台                  │
└──────────────────────────────────────────────────────────┘
```

Gateway 是 KuberPilot 与目标平台之间的工具层。网络预检只回答“是否可达、失败在哪一
层”，不负责用户名密码和页面数据提取。

---

## 4. 文件与模块设计

### 4.1 核心目录

```text
web_automation/
├── gateway/
│   ├── app.py                    # FastAPI 入口
│   ├── config.py                 # 项目相对配置
│   ├── dependencies.py           # Registry/Checker 依赖构造
│   ├── routes/health.py          # REST 健康与预检接口
│   └── mcp/
│       ├── router.py             # MCP JSON-RPC
│       └── health_tool.py        # web_platform.health
├── network/
│   ├── checker.py                # 五层编排和失败短路
│   ├── models.py                 # 结构化报告
│   ├── errors.py                 # 稳定错误码
│   ├── url_policy.py             # SSRF/网段限制
│   ├── dns_checker.py
│   ├── tcp_checker.py
│   ├── tls_checker.py
│   └── http_checker.py
├── platforms/
│   ├── loader.py                 # YAML 注册表
│   ├── models.py                 # 配置校验
│   ├── definitions/              # 本地进程配置
│   └── docker-definitions/       # Docker DNS 配置
├── mock_platform/app.py          # 模拟管理台
├── scripts/
│   ├── start-local-demo.ps1
│   ├── start-gateway.ps1
│   ├── run-tests.ps1
│   ├── verify_local.py
│   └── generate_test_ca.py
├── tests/
├── Dockerfile
└── requirements.txt
```

### 4.2 为什么使用独立目录

网络预检未来会被登录、Adapter、定时采集共同复用。如果直接写进 KuberPilot
`services.py`：

- 每新增平台都可能修改 Agent 主引擎；
- 无法独立部署到可访问目标管理网的节点；
- Playwright 和证书依赖会污染 Django 环境；
- 故障边界不清晰。

因此本实现保持独立进程，通过 MCP 与 KuberPilot 集成。

---

## 5. 分层检查流程

### 5.1 URL 策略

入口只接受注册平台标识。`url_policy.py`检查：

- 仅允许 HTTP/HTTPS；
- URL 内禁止用户名密码；
- 禁止云元数据地址；
- DNS 结果必须位于该平台配置的允许网段；
- 拒绝未指定、多播、链路本地地址。

### 5.2 DNS

`dns_checker.py`调用系统解析器，返回全部 IPv4/IPv6 地址和耗时。所有解析结果都
必须通过地址策略，避免域名在检查后解析到另一个敏感地址。

### 5.3 TCP

`tcp_checker.py`只连接平台配置中的一个端口，不扫描其他端口。结果区分：

- 连接成功；
- 拒绝连接；
- 超时；
- 其他网络错误。

### 5.4 TLS

HTTPS 平台使用系统 CA 或平台专属私有 CA 完成真实握手，验证：

- 证书信任链；
- 证书有效期；
- 主机名/IP；
- TLS 协议；
- 证书主题和签发者。

HTTP 平台返回明确的“TLS 未执行”，而不是缺失字段。

### 5.5 HTTP

HTTP 层只发送 GET，不保存正文，不自动跟随重定向。状态解释：

| 状态 | 网络判断 |
|---|---|
| 200 | 页面可访问 |
| 301/302 | 服务可达，返回跳转；预检不继续跟随 |
| 401 | 网络可达，需要认证 |
| 403 | 网络可达，被访问策略拒绝 |
| 5xx | 目标平台或代理异常 |

不自动跟随重定向可避免目标平台把预检器引向未登记地址。

### 5.6 失败短路

```text
DNS 失败 ──→ 返回，不执行 TCP/TLS/HTTP
TCP 失败 ──→ 返回，不执行 TLS/HTTP
TLS 失败 ──→ 返回，不执行 HTTP
HTTP 失败 ─→ 返回完整前置成功信息
```

---

## 6. 平台配置与安全边界

本地示例：

```yaml
platform: mock_platform
display_name: Mock operations platform
base_url: http://127.0.0.1:8011/login
enabled: true
timeout_seconds: 5
expected_login_path: /login
allowed_resolved_cidrs:
  - 127.0.0.0/8
```

私有 CA 示例：

```yaml
platform: private_cloud
display_name: Private cloud
base_url: https://private-cloud.example/login
ca_cert_path: certs/private-cloud-ca.pem
allowed_resolved_cidrs:
  - 10.20.0.0/16
```

`ca_cert_path`解析后必须仍在`web_automation`项目目录内，禁止`../`逃逸。

模型调用中不允许出现：

```json
{"url": "http://169.254.169.254/"}
```

唯一允许的业务参数是：

```json
{"platform": "mock_platform"}
```

---

## 7. REST 与 MCP 接口

### 7.1 Gateway 存活

```http
GET /healthz
```

### 7.2 运维人员直接检查

```http
POST /api/v1/platforms/{platform}/connectivity-check
```

### 7.3 MCP

```http
POST /mcp
```

实现 KuberPilot 当前客户端使用的：

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`
- `DELETE /mcp`

工具名称：

```text
web_platform.health
```

工具返回 MCP `content`文本和`structuredContent`结构化报告。检查失败时
`isError=true`，但仍返回可诊断的安全报告。

---

## 8. 本地模拟环境

模拟平台提供：

| 路径 | 用途 |
|---|---|
| `/health` | 服务存活 |
| `/login` | 正常登录页 |
| `/redirect-to-login` | 302 场景 |
| `/status/{code}` | 401/403/503 等 |
| `/slow` | 超时测试 |

`generate_test_ca.py`在`.runtime/certs`生成仅用于本地测试的：

- 测试 CA；
- HTTPS 服务端证书；
- 对应私钥。

服务器证书包含 SAN、SKI、AKI、Key Usage 和 Server Authentication EKU，可以
通过 Python 3.14 的严格证书校验。`.runtime`被 Git 忽略。

---

## 9. 本地运行与验证

### 9.1 一键启动

```powershell
Set-Location ".\web_automation"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start-local-demo.ps1
```

端口：

| 服务 | 地址 |
|---|---|
| Gateway | `http://127.0.0.1:8010` |
| HTTP Mock | `http://127.0.0.1:8011` |
| HTTPS Mock | `https://127.0.0.1:8443` |

### 9.2 REST 验证

```powershell
Invoke-RestMethod http://127.0.0.1:8010/healthz

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8010/api/v1/platforms/mock_platform/connectivity-check"
```

### 9.3 自动端到端验证

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_local.py
```

该脚本启动三个精确子进程，验证HTTP、私有CA HTTPS、MCP列表和MCP调用，最后只
终止自己启动的进程。

---

## 10. Docker Compose 部署

Compose文件：

```text
compose.web-automation.yml
```

服务：

```text
certificate-generator
mock-platform
mock-private-ca
web-automation-gateway
```

启动：

```powershell
docker compose -f compose.web-automation.yml up --build
```

停止：

```powershell
docker compose -f compose.web-automation.yml down
```

Compose使用绑定目录保存测试证书，不创建证据数据卷；容器日志限制为每文件10MB、
最多3个文件。

### 10.1 验证范围

Compose 配置已通过语法验证：

```powershell
docker compose -f compose.web-automation.yml config --quiet
```

当前验证不包含基础镜像拉取、镜像构建和容器运行，因此 Compose 结论仅限于配置
语法与服务依赖关系。

---

## 11. 测试与验收结果

执行：

```powershell
.\scripts\run-tests.ps1
```

结果：

```text
25 passed
```

覆盖：

- URL协议、嵌入凭据和元数据地址拦截；
- DNS成功与失败；
- TCP成功、拒绝和Windows超时差异；
- TLS跳过与CA错误；
- HTTP 200/401/503；
- YAML加载、未知平台和路径逃逸；
- 完整成功流程与DNS失败短路；
- REST存活接口；
- MCP初始化、工具列表、工具调用参数限制。

真实本地端到端结果：

```text
Gateway health            OK
HTTP platform             DNS/TCP/HTTP OK
HTTPS private CA platform DNS/TCP/TLS/HTTP OK
MCP tools/list            web_platform.health
MCP tools/call            OK
```

---

## 12. 错误码与排障

| 错误码 | 含义 | 优先检查 |
|---|---|---|
| `PLATFORM_NOT_FOUND` | 未登记平台 | YAML与platform拼写 |
| `PLATFORM_DISABLED` | 管理员禁用 | `enabled` |
| `INVALID_TARGET` | URL格式/协议错误 | `base_url` |
| `TARGET_NOT_ALLOWED` | 地址不在白名单 | DNS结果、CIDR |
| `DNS_RESOLUTION_FAILED` | 域名无法解析 | 企业DNS/hosts |
| `TCP_CONNECTION_REFUSED` | 端口拒绝 | 服务和端口 |
| `TCP_TIMEOUT` | 连接超时 | 路由/防火墙 |
| `TLS_PRIVATE_CA_UNTRUSTED` | CA不可信 | 私有CA路径 |
| `TLS_CERTIFICATE_EXPIRED` | 证书过期 | 更新证书 |
| `TLS_HOSTNAME_MISMATCH` | 域名不匹配 | URL/SAN |
| `TLS_HANDSHAKE_FAILED` | TLS协商失败 | 协议、证书文件 |
| `PROXY_CONNECTION_FAILED` | 代理失败 | 代理地址/网络 |
| `HTTP_REQUEST_FAILED` | HTTP超时或5xx | 平台服务状态 |

---

## 13. 安全设计

1. **SSRF防护**：模型无权提供URL，且DNS结果受CIDR限制。
2. **云元数据保护**：拒绝`169.254.169.254`与已知元数据主机。
3. **无明文凭据**：网络预检完全不处理平台密码。
4. **不读取正文**：不把管理页面内容送入日志或模型。
5. **不跟随重定向**：避免跳向未登记目标。
6. **真实TLS校验**：私有CA必须明确配置。
7. **路径限制**：CA路径不能离开项目根目录。
8. **日志限制**：Compose日志轮转；本地日志位于项目`logs`。
9. **只读行为**：只执行DNS、连接、握手和GET。

---

## 14. 已知边界

本期不包含：

- 账号密码和TOTP；
- Cookie、Token和`storage_state`；
- Playwright浏览器登录；
- Adapter资源/告警转换；
- 企业堡垒机与真实代理验证；
- K8s NetworkPolicy；
- 对生产管理网做真实放行。

账号凭据解析、浏览器登录和登录态管理不属于网络预检模块；这些能力由
Credential Provider 与平台 Adapter 负责，并复用 `ConnectivityChecker` 作为
访问目标平台前的安全检查。
