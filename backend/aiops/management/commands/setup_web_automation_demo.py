"""Configure the local Web Automation MCP demonstration."""

from django.core.management.base import BaseCommand

from aiops.models import (
    AIOpsAgentConfig,
    AIOpsKnowledgeEnvironment,
    AIOpsMCPServer,
)


SERVER_NAME = "Web Automation Gateway"
ENVIRONMENT_NAME = "Web Automation 演示环境"
SUGGESTED_QUESTIONS = [
    "查看mock_platform当前告警",
    "查看legacy_ops_platform当前告警",
]


class Command(BaseCommand):
    help = "Idempotently register the local read-only Web Automation Gateway demo."

    def handle(self, *args, **options):
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
            if str(item).strip() and str(item).strip() not in SUGGESTED_QUESTIONS
        ]
        suggested_questions = SUGGESTED_QUESTIONS + suggested_questions
        config.enabled_mcp_server_ids = selected_server_ids
        config.suggested_questions = suggested_questions[:8]
        config.is_enabled = True
        config.welcome_message = (
            "你好，我可以查询 KuberPilot 数据，也可以通过 Web Automation "
            "安全登录外部平台并读取告警。"
        )
        config.save(
            update_fields=[
                "enabled_mcp_server_ids",
                "suggested_questions",
                "is_enabled",
                "welcome_message",
                "updated_at",
            ]
        )

        AIOpsKnowledgeEnvironment.objects.exclude(name=ENVIRONMENT_NAME).update(
            is_default=False
        )
        environment, _ = AIOpsKnowledgeEnvironment.objects.update_or_create(
            name=ENVIRONMENT_NAME,
            defaults={
                "aliases": [
                    "mock_platform",
                    "mock-platform",
                    "MockOps",
                    "模拟平台",
                    "legacy_ops_platform",
                    "legacy-ops-platform",
                    "Legacy NOC",
                    "旧版运维平台",
                ],
                "description": "用于学习 Web Automation 外部平台告警接入的本地演示环境",
                "is_default": True,
                "is_enabled": True,
                "created_by": "setup_web_automation_demo",
                "updated_by": "setup_web_automation_demo",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Web Automation demo configured: "
                f"MCP #{server.id}, Agent #{config.id}, Environment #{environment.id}."
            )
        )
