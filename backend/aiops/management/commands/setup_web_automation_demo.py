"""Configure the local Web Automation MCP and alarm-callback demonstration."""

import os

from django.core.management.base import BaseCommand

from aiops.models import (
    AIOpsAgentConfig,
    AIOpsKnowledgeEnvironment,
    AIOpsMCPServer,
)
from ops.models import AlertIntegration


SERVER_NAME = "Web Automation Gateway"
ENVIRONMENT_NAME = "Web Automation 演示环境"
ALERT_INTEGRATION_NAME = "Web Automation Gateway"
DEFAULT_ENVIRONMENT_DESCRIPTION = "用于学习 Web Automation 外部平台告警接入的本地演示环境"
WEB_AUTOMATION_ENVIRONMENT_DESCRIPTION = (
    "用于 Web Automation 外部平台告警接入的演示与经授权只读联调环境"
)
DEFAULT_WELCOME_MESSAGE = "你好，我可以帮你结合平台上下文查询资源、根因分析、生成待执行任务等。"
WEB_AUTOMATION_WELCOME_MESSAGE = (
    "你好，我可以查询 KuberPilot 数据，也可以通过 Web Automation "
    "安全登录外部平台并读取告警。"
)
SUGGESTED_QUESTIONS = [
    "查看mock_platform当前告警",
    "查看legacy_ops_platform当前告警",
    "查看KuberCon当前告警",
]
ENVIRONMENT_ALIASES = [
    "mock_platform",
    "mock-platform",
    "MockOps",
    "模拟平台",
    "legacy_ops_platform",
    "legacy-ops-platform",
    "Legacy NOC",
    "旧版运维平台",
    "kubercon",
    "kuber-con",
    "KuberCon",
]


class Command(BaseCommand):
    help = "Idempotently register the local read-only Web Automation Gateway demo."

    def handle(self, *args, **options):
        callback_token = os.environ.get("WEB_AUTOMATION_CALLBACK_TOKEN", "").strip()
        integration_defaults = {
            "provider": "generic",
            "is_enabled": True,
            "default_labels": {
                "integration": "web_automation",
                "environment": "local-demo",
            },
            "description": "接收 Web Automation 周期采集产生的新增与恢复告警",
        }
        if callback_token:
            integration_defaults["token"] = callback_token
        integration, _ = AlertIntegration.objects.update_or_create(
            name=ALERT_INTEGRATION_NAME,
            defaults=integration_defaults,
        )

        server, _ = AIOpsMCPServer.objects.update_or_create(
            name=SERVER_NAME,
            defaults={
                "server_type": AIOpsMCPServer.SERVER_HTTP,
                "endpoint_or_command": "http://127.0.0.1:8010/mcp",
                "description": "只读 Web 平台浏览器自动化 Gateway（本地研究环境）",
                "auth_config": {
                    "timeout_seconds": 30,
                    "allow_write": False,
                },
                "tool_whitelist": [
                    "web_platform.health",
                    "web_platform.list_alarms",
                ],
                "is_builtin": False,
                "is_enabled": True,
            },
        )

        config, _ = AIOpsAgentConfig.objects.get_or_create(name="default")
        selected_server_ids = [
            int(item)
            for item in (config.enabled_mcp_server_ids or [])
            if str(item).isdigit()
        ]
        if server.id not in selected_server_ids:
            selected_server_ids.append(server.id)
        suggested_questions = [
            str(item).strip()
            for item in (config.suggested_questions or [])
            if str(item).strip()
        ]
        LIMIT = 8
        for question in SUGGESTED_QUESTIONS:
            if len(suggested_questions) >= LIMIT:
                break
            if question not in suggested_questions:
                suggested_questions.append(question)
        config.enabled_mcp_server_ids = selected_server_ids
        config.suggested_questions = suggested_questions
        config.is_enabled = True
        current_welcome = (config.welcome_message or "").strip()
        if not current_welcome or current_welcome == DEFAULT_WELCOME_MESSAGE:
            config.welcome_message = WEB_AUTOMATION_WELCOME_MESSAGE
        elif "Web Automation" not in current_welcome:
            config.welcome_message = (
                f"{current_welcome.rstrip()} {WEB_AUTOMATION_WELCOME_MESSAGE}"
            )[:255]
        config.save(
            update_fields=[
                "enabled_mcp_server_ids",
                "suggested_questions",
                "is_enabled",
                "welcome_message",
                "updated_at",
            ]
        )

        AIOpsKnowledgeEnvironment.objects.exclude(name=ENVIRONMENT_NAME).filter(
            is_default=True
        ).update(is_default=False)
        environment, created = AIOpsKnowledgeEnvironment.objects.get_or_create(
            name=ENVIRONMENT_NAME,
            defaults={
                "aliases": ENVIRONMENT_ALIASES,
                "description": WEB_AUTOMATION_ENVIRONMENT_DESCRIPTION,
                "is_default": True,
                "is_enabled": True,
                "created_by": "setup_web_automation_demo",
                "updated_by": "setup_web_automation_demo",
            },
        )
        if not created:
            aliases = [
                str(item).strip()
                for item in (environment.aliases or [])
                if str(item).strip()
            ]
            for alias in ENVIRONMENT_ALIASES:
                if alias not in aliases:
                    aliases.append(alias)
            environment.aliases = aliases
            if not environment.description or (
                environment.description == DEFAULT_ENVIRONMENT_DESCRIPTION
            ):
                environment.description = WEB_AUTOMATION_ENVIRONMENT_DESCRIPTION
            environment.is_default = True
            environment.is_enabled = True
            environment.updated_by = "setup_web_automation_demo"
            environment.save(
                update_fields=[
                    "aliases",
                    "description",
                    "is_default",
                    "is_enabled",
                    "updated_by",
                    "updated_at",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Web Automation demo configured: "
                f"MCP #{server.id}, Agent #{config.id}, Environment #{environment.id}, "
                f"AlertIntegration #{integration.id}."
            )
        )
