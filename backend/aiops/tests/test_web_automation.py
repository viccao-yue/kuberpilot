from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from aiops.models import (
    AIOpsAgentConfig,
    AIOpsKnowledgeEnvironment,
    AIOpsMCPServer,
)
from aiops.services import (
    _extract_web_platform,
    _format_web_platform_alarm_result,
    _is_web_platform_alarm_question,
    _run_web_platform_alarm_fastpath,
)


class WebPlatformAlarmRoutingTests(TestCase):
    def test_matcher_requires_platform_and_alarm(self):
        self.assertTrue(_is_web_platform_alarm_question("查看mock_platform当前告警"))
        self.assertTrue(_is_web_platform_alarm_question("查询模拟平台 alerts"))
        self.assertTrue(_is_web_platform_alarm_question("查看旧版运维平台当前告警"))
        self.assertFalse(_is_web_platform_alarm_question("查看当前告警"))
        self.assertFalse(_is_web_platform_alarm_question("打开 mock_platform"))

    def test_platform_extractor_supports_two_distinct_platforms(self):
        self.assertEqual(
            _extract_web_platform("查看mock_platform当前告警"),
            "mock_platform",
        )
        self.assertEqual(
            _extract_web_platform("查看 Legacy NOC 当前告警"),
            "legacy_ops_platform",
        )
        self.assertEqual(_extract_web_platform("查看 MockOps 告警"), "mock_platform")
        self.assertEqual(_extract_web_platform("查看 mock ops 告警"), "mock_platform")
        self.assertIsNone(_extract_web_platform("查看当前告警"))

    def test_formatter_renders_standard_alarm_in_chinese(self):
        content = _format_web_platform_alarm_result(
            {
                "platform": "mock_platform",
                "count": 1,
                "severity_counts": {"critical": 1},
                "alarms": [
                    {
                        "alarm_id": "MOCK-001",
                        "severity": "critical",
                        "resource_name": "test-vm-01",
                        "resource_type": "host",
                        "title": "CPU使用率过高",
                        "description": "CPU 使用率连续 5 分钟超过 90%。",
                        "occurred_at": "2026-07-30T09:15:00+08:00",
                    }
                ],
            }
        )
        self.assertIn("mock_platform 当前活动告警", content)
        self.assertIn("test-vm-01", content)
        self.assertIn("CPU使用率过高", content)
        self.assertIn("只读 MCP", content)

    def test_formatter_tolerates_non_numeric_severity_counts(self):
        content = _format_web_platform_alarm_result(
            {
                "platform": "mock_platform",
                "severity_counts": {
                    "critical": "N/A",
                    "warning": "--",
                    "info": "∞",
                },
                "alarms": [],
            }
        )

        self.assertIn("严重 0 条，警告 0 条，提示 0 条", content)

    @mock.patch("aiops.services._build_runtime_tool_registry")
    @mock.patch("aiops.services.user_has_permissions", return_value=False)
    def test_fastpath_rejects_user_without_mcp_permission(
        self,
        mocked_has_permissions,
        mocked_build_registry,
    ):
        result = _run_web_platform_alarm_fastpath(
            session=None,
            user_message=SimpleNamespace(content="查看 MockOps 告警"),
            user=SimpleNamespace(username="viewer"),
            active_mcp_servers=[],
            knowledge_environment=None,
            analysis_scope={},
            emit=mock.Mock(),
        )

        mocked_has_permissions.assert_called_once_with(
            mock.ANY,
            ["aiops.mcp.invoke"],
        )
        mocked_build_registry.assert_not_called()
        self.assertEqual(
            result["metadata"]["error_code"],
            "web_platform_alarm_mcp_permission_denied",
        )

    @mock.patch("aiops.services._run_tool_call")
    @mock.patch("aiops.services._build_runtime_tool_registry")
    @mock.patch("aiops.services.user_has_permissions", return_value=True)
    def test_fastpath_allows_user_with_mcp_permission(
        self,
        mocked_has_permissions,
        mocked_build_registry,
        mocked_run_tool_call,
    ):
        managed_client = mock.Mock()
        registry_entry = {
            "kind": "external",
            "raw_tool_name": "web_platform.list_alarms",
        }
        mocked_build_registry.return_value = (
            [],
            {"web_automation__list_alarms": registry_entry},
            [managed_client],
            [],
        )
        mocked_run_tool_call.return_value = {
            "tool_output": {
                "structuredContent": {
                    "ok": True,
                    "platform": "mock_platform",
                    "count": 1,
                    "severity_counts": {
                        "critical": 1,
                        "warning": 0,
                        "info": 0,
                    },
                    "alarms": [],
                    "collection_method": "playwright_authenticated_session",
                    "read_only": True,
                }
            },
            "citations": [],
        }
        user = SimpleNamespace(username="operator")
        user_message = SimpleNamespace(content="查看 MockOps 告警")

        result = _run_web_platform_alarm_fastpath(
            session=None,
            user_message=user_message,
            user=user,
            active_mcp_servers=[SimpleNamespace(name="Web Automation Gateway")],
            knowledge_environment={"name": "Web Automation 演示环境"},
            analysis_scope={},
            emit=mock.Mock(),
        )

        mocked_has_permissions.assert_called_once_with(
            user,
            ["aiops.mcp.invoke"],
        )
        mocked_build_registry.assert_called_once_with(mock.ANY, user)
        mocked_run_tool_call.assert_called_once_with(
            None,
            user_message,
            user,
            "web_automation__list_alarms",
            {"platform": "mock_platform", "limit": 20},
            registry_entry=registry_entry,
        )
        self.assertEqual(result["metadata"]["alarm_count"], 1)
        self.assertEqual(result["metadata"]["external_platform"], "mock_platform")
        self.assertTrue(result["metadata"]["read_only"])
        managed_client.close.assert_called_once_with()


class WebAutomationSetupCommandTests(TestCase):
    def test_command_is_idempotent_and_registers_read_only_mcp(self):
        output = StringIO()
        call_command("setup_web_automation_demo", stdout=output)
        call_command("setup_web_automation_demo", stdout=output)

        server = AIOpsMCPServer.objects.get(name="Web Automation Gateway")
        config = AIOpsAgentConfig.objects.get(name="default")
        environment = AIOpsKnowledgeEnvironment.objects.get(
            name="Web Automation 演示环境"
        )

        self.assertEqual(AIOpsMCPServer.objects.count(), 1)
        self.assertEqual(server.endpoint_or_command, "http://127.0.0.1:8010/mcp")
        self.assertFalse(server.auth_config["allow_write"])
        self.assertIn("web_platform.list_alarms", server.tool_whitelist)
        self.assertIn(server.id, config.enabled_mcp_server_ids)
        self.assertEqual(config.suggested_questions[0], "查看mock_platform当前告警")
        self.assertEqual(
            config.suggested_questions[1],
            "查看legacy_ops_platform当前告警",
        )
        self.assertTrue(environment.is_default)
        self.assertIn("mock_platform", environment.aliases)
        self.assertIn("legacy_ops_platform", environment.aliases)

    def test_command_preserves_full_question_list_and_custom_welcome(self):
        original_questions = [f"用户问题 {index}" for index in range(1, 9)]
        custom_welcome = "欢迎使用公司运维助手。"
        config = AIOpsAgentConfig.objects.create(
            name="default",
            suggested_questions=original_questions,
            welcome_message=custom_welcome,
        )

        call_command("setup_web_automation_demo", stdout=StringIO())
        config.refresh_from_db()

        self.assertEqual(config.suggested_questions, original_questions)
        self.assertTrue(config.welcome_message.startswith(custom_welcome))
        self.assertIn("Web Automation", config.welcome_message)
        self.assertLessEqual(len(config.welcome_message), 255)

        first_welcome = config.welcome_message
        call_command("setup_web_automation_demo", stdout=StringIO())
        config.refresh_from_db()
        self.assertEqual(config.suggested_questions, original_questions)
        self.assertEqual(config.welcome_message, first_welcome)

    def test_command_only_demotes_existing_default_environment(self):
        default_environment = AIOpsKnowledgeEnvironment.objects.create(
            name="生产环境图谱",
            is_default=True,
        )
        non_default_environment = AIOpsKnowledgeEnvironment.objects.create(
            name="测试环境图谱",
            is_default=False,
        )

        call_command("setup_web_automation_demo", stdout=StringIO())
        default_environment.refresh_from_db()
        non_default_environment.refresh_from_db()

        self.assertFalse(default_environment.is_default)
        self.assertFalse(non_default_environment.is_default)
