"""A legacy-style operations platform whose alarms exist only in an HTML table."""

import html
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse


app = FastAPI(title="Legacy Operations Console")
SESSION_COOKIE = "legacy_ops_sid"
SESSIONS: dict[str, str] = {}

EVENTS = [
    {
        "event_no": "EVT-9001",
        "priority": "P1",
        "asset": "db-master-01",
        "asset_kind": "DATABASE",
        "summary": "数据库连接数接近上限",
        "detail": "当前连接数 475，上限 500。",
        "raised_time": "2026/07/31 09:18:32",
        "state": "OPEN",
    },
    {
        "event_no": "EVT-9002",
        "priority": "P2",
        "asset": "payment-api",
        "asset_kind": "SERVICE",
        "summary": "支付接口响应变慢",
        "detail": "",
        "raised_time": "2026/07/31 09:23:07",
        "state": "ACK",
    },
    {
        "event_no": "EVT-9003",
        "priority": "P3",
        "asset": "backup-job-07",
        "asset_kind": "",
        "summary": "备份任务完成时间晚于预期",
        "detail": "任务已完成，建议观察下一周期。",
        "raised_time": "2026/07/31 09:31:45",
        "state": "OPEN",
    },
]


def _credentials() -> tuple[str, str]:
    return (
        os.environ.get("LEGACY_OPS_USERNAME", "legacy_reader"),
        os.environ.get("LEGACY_OPS_PASSWORD", "LegacyOnly@123456"),
    )


def _current_user(request: Request) -> str | None:
    return SESSIONS.get(request.cookies.get(SESSION_COOKIE, ""))


def _login_page(error: str = "") -> HTMLResponse:
    error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
    return HTMLResponse(
        f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>旧版运维台登录</title>
<style>
body{{margin:0;background:#16202a;color:#d9e2ec;font:14px Arial,"Microsoft YaHei";}}
.shell{{width:520px;margin:90px auto;border:1px solid #536575;background:#243442;}}
.title{{padding:14px 18px;background:#0f1720;font-size:20px}}form{{padding:24px}}
.row{{display:grid;grid-template-columns:110px 1fr;margin:14px 0;align-items:center}}
input{{padding:9px;background:#111d27;border:1px solid #657786;color:white}}
button{{margin-left:110px;padding:9px 28px;background:#d97706;color:white;border:0}}
.error{{margin:0 24px;color:#fecaca}}
</style></head><body><main class="shell"><div class="title">Legacy NOC Console 3.2</div>
{error_html}<form method="post" action="/auth/signin">
<div class="row"><label for="operator">操作员工号</label><input id="operator" name="operator"></div>
<div class="row"><label for="access_key">访问口令</label><input id="access_key" name="access_key" type="password"></div>
<button type="submit">进入控制台</button></form></main></body></html>"""
    )


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/auth/signin", response_class=HTMLResponse)
async def login_page(request: Request):
    if _current_user(request):
        return RedirectResponse("/console", status_code=302)
    return _login_page()


@app.post("/auth/signin")
async def login(request: Request):
    values = parse_qs((await request.body()).decode("utf-8", errors="strict"))
    username = (values.get("operator") or [""])[0]
    password = (values.get("access_key") or [""])[0]
    expected_username, expected_password = _credentials()
    if not secrets.compare_digest(username, expected_username) or not secrets.compare_digest(
        password, expected_password
    ):
        return _login_page("认证失败：请检查操作员工号和访问口令。")
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = username
    response = RedirectResponse("/console", status_code=303)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", max_age=900)
    return response


@app.get("/console", response_class=HTMLResponse)
async def console(request: Request):
    if not _current_user(request):
        return RedirectResponse("/auth/signin", status_code=302)
    return HTMLResponse(
        """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>Legacy NOC Console</title></head><body>
<h1>Legacy NOC Console</h1><p>只读事件查询</p>
<a href="/active-events">进入活动事件列表</a></body></html>"""
    )


@app.get("/active-events", response_class=HTMLResponse)
async def active_events(request: Request):
    if not _current_user(request):
        return RedirectResponse("/auth/signin", status_code=302)
    rows = "".join(
        f"""<tr data-event-no="{html.escape(item['event_no'])}">
<td class="priority">{html.escape(item['priority'])}</td>
<td class="asset">{html.escape(item['asset'])}</td>
<td class="asset-kind">{html.escape(item['asset_kind'])}</td>
<td class="summary">{html.escape(item['summary'])}</td>
<td class="detail">{html.escape(item['detail'])}</td>
<td class="raised-time">{html.escape(item['raised_time'])}</td>
<td class="state">{html.escape(item['state'])}</td></tr>"""
        for item in EVENTS
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>活动事件</title><style>
body{{font:13px Arial,"Microsoft YaHei";padding:18px;background:#e7e9eb}}
table{{width:100%;border-collapse:collapse;background:white}}
th,td{{border:1px solid #9aa3aa;padding:8px;text-align:left}}th{{background:#324553;color:white}}
</style></head><body><h1>活动事件列表</h1>
<table id="event-grid"><thead><tr><th>优先级</th><th>对象</th><th>对象类别</th>
<th>摘要</th><th>补充信息</th><th>发生时间</th><th>状态</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
    )


@app.post("/test/expire-session")
async def expire_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    SESSIONS.pop(token, None)
    return {"expired": True}
