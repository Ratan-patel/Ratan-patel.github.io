import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "parrot-ai"
loader = importlib.machinery.SourceFileLoader("parrot_ai_under_test", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
parrot_ai = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parrot_ai)


class FakeShell:
    def __init__(self):
        self.commands = []

    def run(self, command):
        self.commands.append(command)
        return {"exit_code": 0, "output": f"ran: {command}", "truncated": False}


class ParrotAITests(unittest.TestCase):
    def test_config_is_written_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "config.json"
            parrot_ai.save_config(path, {"provider": "gemini", "api_key": "test-only"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["provider"], "gemini")
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_parse_tool_arguments_object_and_json(self):
        self.assertEqual(parrot_ai._parse_arguments({"command": "id"}), {"command": "id"})
        self.assertEqual(parrot_ai._parse_arguments('{"command":"id"}'), {"command": "id"})
        with self.assertRaises(parrot_ai.AgentError):
            parrot_ai._parse_arguments("not-json")

    def test_interactions_function_tool_has_local_execution_description(self):
        self.assertEqual(parrot_ai.INTERACTIONS_FUNCTION["name"], "parrot_terminal")
        self.assertIn("local Parrot", parrot_ai.INTERACTIONS_FUNCTION["description"])
        self.assertEqual(parrot_ai._openrouter_tool()["function"]["name"], "parrot_terminal")

    def test_interaction_output_text_is_extracted(self):
        self.assertEqual(
            parrot_ai._interaction_text({"output_text": "finished"}),
            "finished",
        )
        self.assertEqual(
            parrot_ai._interaction_text({"steps": [
                {"type": "model_output", "content": [{"type": "text", "text": "fallback"}]}
            ]}),
            "fallback",
        )

    def test_gemini_tool_loop_executes_injected_shell_and_continues(self):
        shell = FakeShell()
        provider = parrot_ai.GeminiInteractions(
            {"provider": "gemini", "api_key": "dummy", "model": "gemini-test"}, shell
        )
        responses = [
            {
                "id": "interaction-1",
                "status": "requires_action",
                "steps": [{
                    "type": "function_call",
                    "id": "call-1",
                    "name": "parrot_terminal",
                    "arguments": {"command": "printf ok"},
                }],
            },
            {"id": "interaction-2", "status": "completed", "output_text": "Done."},
        ]
        with patch.object(parrot_ai, "_http_json", side_effect=responses) as post:
            result = provider.ask("check the shell")
        self.assertEqual(result, "Done.")
        self.assertEqual(shell.commands, ["printf ok"])
        self.assertEqual(post.call_args_list[1].args[1]["previous_interaction_id"], "interaction-1")
        self.assertEqual(provider.previous_id, "interaction-2")

    def test_antigravity_tool_result_is_returned_to_managed_agent(self):
        shell = FakeShell()
        provider = parrot_ai.AntigravityAgent(
            {"provider": "antigravity", "api_key": "dummy", "model": "gemini-test"}, shell
        )
        responses = [
            {
                "id": "agent-interaction-1",
                "environment_id": "env-1",
                "status": "requires_action",
                "steps": [{
                    "type": "function_call",
                    "id": "call-1",
                    "name": "parrot_terminal",
                    "arguments": {"command": "whoami"},
                }],
            },
            {"id": "agent-interaction-2", "status": "completed", "output_text": "Completed."},
        ]
        with patch.object(parrot_ai, "_http_json", side_effect=responses) as post:
            result = provider.ask("who am I?")
        self.assertEqual(result, "Completed.")
        self.assertEqual(shell.commands, ["whoami"])
        initial = post.call_args_list[0].args[1]
        self.assertIn("Parrot 7.4 guest VM", initial["input"])
        self.assertEqual([tool["type"] for tool in initial["tools"]], ["function"])
        followup = post.call_args_list[1].args[1]
        self.assertEqual(followup["environment"], "env-1")
        self.assertEqual(followup["input"][0]["result"]["exit_code"], 0)
        self.assertNotIn("code_execution", [tool.get("type") for tool in followup["tools"]])

    def test_openrouter_tool_loop(self):
        shell = FakeShell()
        provider = parrot_ai.OpenAICompatibleAgent(
            {"provider": "openrouter", "api_key": "dummy", "model": "vendor/tool-model"},
            shell,
            "openrouter",
        )
        responses = [
            {"choices": [{"message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "parrot_terminal", "arguments": '{"command":"id"}'},
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "Command succeeded."}}]},
        ]
        with patch.object(parrot_ai, "_http_json", side_effect=responses):
            result = provider.ask("run id")
        self.assertEqual(result, "Command succeeded.")
        self.assertEqual(shell.commands, ["id"])
        self.assertEqual(provider.messages[-1]["role"], "assistant")


@unittest.skipIf(parrot_ai.pexpect is None, "python3-pexpect is not installed in this test environment")
class LocalShellTests(unittest.TestCase):
    def test_shell_state_persists_between_tool_calls(self):
        shell = parrot_ai.LocalShell()
        try:
            self.assertEqual(shell.run("cd /tmp")["exit_code"], 0)
            result = shell.run("pwd")
            self.assertEqual(result["exit_code"], 0)
            self.assertIn("/tmp", result["output"])
        finally:
            shell.close()

    def test_active_api_secret_is_redacted_and_not_inherited_by_shell(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-secret"}):
            shell = parrot_ai.LocalShell(secrets=["test-only-secret"])
            try:
                result = shell.run("printf '%s' \"${GEMINI_API_KEY-}\"")
                self.assertEqual(result["output"].strip(), "")
                result = shell.run("printf 'test-only-secret'")
                self.assertNotIn("test-only-secret", result["output"])
                self.assertIn("REDACTED API KEY", result["output"])
            finally:
                shell.close()


if __name__ == "__main__":
    unittest.main()
