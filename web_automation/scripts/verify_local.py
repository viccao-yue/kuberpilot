"""Start all local fixtures, verify REST/MCP paths, then stop exact child processes."""

import json
import os
import subprocess
import sys
import time
import argparse
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def start_process(arguments: list[str], name: str) -> subprocess.Popen:
    stdout = (LOG_DIR / f"{name}.log").open("w", encoding="utf-8")
    stderr = (LOG_DIR / f"{name}.err.log").open("w", encoding="utf-8")
    return subprocess.Popen(
        [sys.executable, *arguments],
        cwd=ROOT,
        stdout=stdout,
        stderr=stderr,
    )


def wait_until_ready(url: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1, trust_env=False).status_code < 500:
                return
        except httpx.HTTPError:
            time.sleep(0.25)
    raise RuntimeError(f"Service did not become ready: {url}")


def main(capture_browser: bool = False) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    runtime_browser_path = ROOT / ".runtime" / "playwright-browsers"
    runtime_tmp_path = ROOT / ".runtime" / "tmp"
    runtime_tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(runtime_browser_path))
    os.environ.setdefault("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")
    os.environ.setdefault("TEMP", str(runtime_tmp_path))
    os.environ.setdefault("TMP", str(runtime_tmp_path))
    os.environ.setdefault("WEB_AUTOMATION_ALLOW_MOCK_DEFAULT_CREDENTIALS", "1")
    os.environ.setdefault("MOCK_PLATFORM_USERNAME", "aiops_robot")
    os.environ.setdefault("MOCK_PLATFORM_PASSWORD", "MockOnly@123456")
    os.environ.setdefault("LEGACY_OPS_USERNAME", "legacy_reader")
    os.environ.setdefault("LEGACY_OPS_PASSWORD", "LegacyOnly@123456")
    subprocess.run([sys.executable, "scripts/generate_test_ca.py"], cwd=ROOT, check=True)
    processes: list[subprocess.Popen] = []
    try:
        processes.append(
            start_process(
                [
                    "-m",
                    "uvicorn",
                    "legacy_ops_platform.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8012",
                ],
                "verify-legacy-ops",
            )
        )
        processes.append(
            start_process(
                [
                    "-m",
                    "uvicorn",
                    "mock_platform.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8011",
                ],
                "verify-http",
            )
        )
        processes.append(
            start_process(
                [
                    "-m",
                    "uvicorn",
                    "mock_platform.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8443",
                    "--ssl-certfile",
                    ".runtime/certs/mock-private-ca-server.crt",
                    "--ssl-keyfile",
                    ".runtime/certs/mock-private-ca-server.key",
                ],
                "verify-https",
            )
        )
        processes.append(
            start_process(
                [
                    "-m",
                    "uvicorn",
                    "gateway.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8010",
                ],
                "verify-gateway",
            )
        )
        wait_until_ready("http://127.0.0.1:8010/healthz")

        with httpx.Client(base_url="http://127.0.0.1:8010", trust_env=False) as client:
            health = client.get("/healthz").json()
            plain = client.post(
                "/api/v1/platforms/mock_platform/connectivity-check"
            ).json()
            private_ca = client.post(
                "/api/v1/platforms/mock_private_ca/connectivity-check"
            ).json()
            tool_list = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "verify-list",
                    "method": "tools/list",
                    "params": {},
                },
            ).json()
            tool_call = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "verify-call",
                    "method": "tools/call",
                    "params": {
                        "name": "web_platform.health",
                        "arguments": {"platform": "mock_platform"},
                    },
                },
            ).json()
            alarm_call = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "verify-alarms",
                    "method": "tools/call",
                    "params": {
                        "name": "web_platform.list_alarms",
                        "arguments": {
                            "platform": "mock_platform",
                            "severity": "all",
                            "limit": 20,
                        },
                    },
                },
                timeout=30,
            ).json()
            legacy_alarm_call = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "verify-legacy-alarms",
                    "method": "tools/call",
                    "params": {
                        "name": "web_platform.list_alarms",
                        "arguments": {
                            "platform": "legacy_ops_platform",
                            "severity": "all",
                            "limit": 20,
                        },
                    },
                },
                timeout=30,
            ).json()

        summary = {
            "gateway_health": health["status"],
            "http_platform_ok": plain["overall_ok"],
            "http_platform_stages": {
                "dns": plain["dns"]["success"],
                "tcp": plain["tcp"]["success"],
                "tls_skipped": not plain["tls"]["attempted"],
                "http": plain["http"]["success"],
            },
            "private_ca_platform_ok": private_ca["overall_ok"],
            "private_ca_tls_ok": private_ca["tls"]["success"],
            "private_ca_failed_stage": private_ca["failed_stage"],
            "private_ca_error_code": private_ca["error_code"],
            "private_ca_message": private_ca["message"],
            "mcp_tool": tool_list["result"]["tools"][0]["name"],
            "mcp_call_is_error": tool_call["result"]["isError"],
            "alarm_tool_is_error": alarm_call["result"]["isError"],
            "alarm_count": alarm_call["result"]
            .get("structuredContent", {})
            .get("count"),
            "alarm_collection_method": alarm_call["result"]
            .get("structuredContent", {})
            .get("collection_method"),
            "legacy_alarm_tool_is_error": legacy_alarm_call["result"]["isError"],
            "legacy_alarm_count": legacy_alarm_call["result"]
            .get("structuredContent", {})
            .get("count"),
            "legacy_first_alarm": legacy_alarm_call["result"]
            .get("structuredContent", {})
            .get("alarms", [{}])[0]
            .get("alarm_id"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not all(
            [
                plain["overall_ok"],
                private_ca["overall_ok"],
                private_ca["tls"]["success"],
                not tool_call["result"]["isError"],
                not alarm_call["result"]["isError"],
                alarm_call["result"].get("structuredContent", {}).get("count") == 3,
                not legacy_alarm_call["result"]["isError"],
                legacy_alarm_call["result"]
                .get("structuredContent", {})
                .get("count")
                == 3,
            ]
        ):
            return 1
        if capture_browser:
            subprocess.run(
                [sys.executable, "scripts/capture_multi_platform_e2e.py"],
                cwd=ROOT,
                check=True,
            )
        return 0
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capture-browser",
        action="store_true",
        help="Capture KuberPilot browser evidence while local fixtures are running.",
    )
    arguments = parser.parse_args()
    raise SystemExit(main(capture_browser=arguments.capture_browser))
