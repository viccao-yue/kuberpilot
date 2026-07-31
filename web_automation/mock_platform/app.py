"""A small but real login-protected operations platform used by the AIOps demo."""

import asyncio
import html
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


app = FastAPI(title="Mock Operations Platform")
SESSION_COOKIE = "mock_ops_session"
SESSIONS: dict[str, str] = {}

ALARMS = [
    {
        "id": "alarm-001",
        "level": "critical",
        "resource_id": "vm-001",
        "resource_type": "vm",
        "resource_name": "test-vm-01",
        "title": "CPU使用率过高",
        "message": "CPU使用率达到95%，已持续8分钟。",
        "occurred_at": "2026-07-30T14:32:00+08:00",
        "status": "firing",
    },
    {
        "id": "alarm-002",
        "level": "warning",
        "resource_id": "node-002",
        "resource_type": "host",
        "resource_name": "node-02",
        "title": "主机可用内存不足",
        "message": "可用内存低于10%，建议检查高占用进程。",
        "occurred_at": "2026-07-30T14:36:00+08:00",
        "status": "firing",
    },
    {
        "id": "alarm-003",
        "level": "warning",
        "resource_id": "storage-001",
        "resource_type": "storage",
        "resource_name": "storage-01",
        "title": "存储池剩余容量不足",
        "message": "存储池剩余容量低于10%。",
        "occurred_at": "2026-07-30T14:40:00+08:00",
        "status": "firing",
    },
]


def _credentials() -> tuple[str, str]:
    return (
        os.environ.get("MOCK_PLATFORM_USERNAME", "aiops_robot"),
        os.environ.get("MOCK_PLATFORM_PASSWORD", "MockOnly@123456"),
    )


def _current_user(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    return SESSIONS.get(token)


def _login_page(error: str = "") -> HTMLResponse:
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return HTMLResponse(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MockOps 登录</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center;
      font-family:"Microsoft YaHei",sans-serif; background:#f4f7fb; color:#1f2937; }}
    .card {{ width:360px; padding:32px; background:white; border-radius:16px;
      box-shadow:0 18px 50px rgba(31,41,55,.12); }}
    h1 {{ margin:0 0 8px; font-size:26px; }} .hint {{ color:#64748b; margin-bottom:24px; }}
    label {{ display:block; margin:14px 0 6px; font-weight:600; }}
    input {{ box-sizing:border-box; width:100%; padding:11px 12px; border:1px solid #cbd5e1;
      border-radius:8px; }}
    button {{ width:100%; margin-top:20px; padding:12px; border:0; border-radius:8px;
      background:#2563eb; color:white; font-weight:700; cursor:pointer; }}
    .error {{ color:#dc2626; background:#fef2f2; padding:9px; border-radius:8px; }}
  </style>
</head>
<body><main class="card">
  <h1>MockOps 管理平台</h1>
  <p class="hint">AIOps Web Automation 授权测试环境</p>
  {error_html}
  <form method="post" action="/login">
    <label for="username">只读服务账号</label>
    <input id="username" name="username" autocomplete="username" required>
    <label for="password">密码</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">登录</button>
  </form>
</main></body></html>"""
    )


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return _login_page()


@app.post("/login")
async def login(request: Request):
    body = (await request.body()).decode("utf-8", errors="strict")
    values = parse_qs(body)
    username = (values.get("username") or [""])[0]
    password = (values.get("password") or [""])[0]
    expected_username, expected_password = _credentials()
    if not secrets.compare_digest(username, expected_username) or not secrets.compare_digest(
        password, expected_password
    ):
        return _login_page("账号或密码错误。")
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = username
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=1800,
    )
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = _current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return HTMLResponse(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>MockOps 控制台</title><style>
body{{font-family:"Microsoft YaHei",sans-serif;margin:0;background:#f6f8fb;color:#1f2937}}
header{{background:#111827;color:white;padding:18px 32px}} main{{padding:28px 32px}}
.card{{background:white;padding:22px;border-radius:12px;max-width:760px;box-shadow:0 8px 24px #0001}}
a{{color:#2563eb}} .badge{{background:#dcfce7;color:#166534;padding:4px 9px;border-radius:999px}}
</style></head><body><header><strong>MockOps</strong> · 只读控制台</header>
<main><section class="card"><span class="badge">登录成功</span>
<h1>欢迎，{html.escape(user)}</h1><p>当前有 <strong>{len(ALARMS)}</strong> 条活动告警。</p>
<p><a href="/alarms">查看告警列表</a></p></section></main></body></html>"""
    )


@app.get("/alarms", response_class=HTMLResponse)
async def alarms_page(request: Request):
    if not _current_user(request):
        return RedirectResponse("/login", status_code=302)
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(item['level'])}</td>"
        f"<td>{html.escape(item['resource_name'])}</td>"
        f"<td>{html.escape(item['title'])}</td>"
        f"<td>{html.escape(item['message'])}</td>"
        "</tr>"
        for item in ALARMS
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>活动告警</title>
<style>body{{font-family:"Microsoft YaHei";padding:30px;background:#f6f8fb}}
table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:12px;border-bottom:1px solid #e5e7eb;text-align:left}}
th{{background:#f8fafc}}</style></head><body><h1>活动告警</h1>
<table><thead><tr><th>级别</th><th>资源</th><th>标题</th><th>说明</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
    )


@app.get("/api/internal/alarms")
async def alarms_api(request: Request):
    if not _current_user(request):
        return JSONResponse({"detail": "authentication required"}, status_code=401)
    severity = request.query_params.get("severity", "all").lower()
    limit = min(max(int(request.query_params.get("limit", "20")), 1), 100)
    items = [
        item for item in ALARMS if severity == "all" or item["level"].lower() == severity
    ][:limit]
    return {"platform": "mock_platform", "count": len(items), "alarms": items}


@app.get("/redirect-to-login")
async def redirect_to_login():
    return RedirectResponse("/login", status_code=302)


@app.get("/status/{status_code}")
async def status(status_code: int):
    return JSONResponse({"simulated": status_code}, status_code=status_code)


@app.get("/slow")
async def slow():
    await asyncio.sleep(10)
    return {"status": "late"}
