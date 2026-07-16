#!/usr/bin/env python3
"""Tests for the model-authenticator probe script."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mock_model_server import MockRelayServer
import probe_models

SCRIPT_PATH = Path(__file__).with_name("probe_models.py")


class ProbeModelsIntegrationTests(unittest.TestCase):
    maxDiff = None

    def run_probe(self, env_overrides: dict[str, str], cwd: Path | None = None) -> tuple[int, dict]:
        env = os.environ.copy()
        for key in (
            "MODEL_AUTH_PROTOCOL",
            "MODEL_AUTH_BASE_URL",
            "MODEL_AUTH_API_KEY",
            "MODEL_AUTH_MODEL",
            "OPENAI_BASE_URL",
            "OPENAI_API_BASE",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENROUTER_BASE_URL",
            "OPENROUTER_API_KEY",
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_MODEL",
            "GEMINI_BASE_URL",
            "GEMINI_API_KEY",
            "GEMINI_MODEL",
            "BASE_URL",
            "API_KEY",
            "MODEL_NAME",
        ):
            env.pop(key, None)
        env.update(env_overrides)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd,
            timeout=20,
            check=False,
        )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                "Probe script did not emit JSON. "
                f"stdout={completed.stdout!r} stderr={completed.stderr!r} exc={exc}"
            )
        return completed.returncode, payload

    def test_openai_env_autodiscovery_detects_premium_profile(self) -> None:
        server = MockRelayServer("openai-premium").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "gpt-4o",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["declared_model"], "gpt-4o")
        self.assertEqual(report["runtime"]["declared_model"], "gpt-4o")
        self.assertIn("env:MODEL_AUTH_MODEL", report["runtime"]["config_sources"])
        self.assertIn("env:MODEL_AUTH_BASE_URL", report["runtime"]["config_sources"])
        self.assertEqual(report["candidate_models"][0]["id"], "openai-premium")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)
        self.assertIsNotNone(report["suspected_actual_model"])

    def test_openai_env_autodiscovery_flags_qwen_substitution(self) -> None:
        server = MockRelayServer("qwen-substitute").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "gpt-4o",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "qwen")
        self.assertTrue(report["mismatch_detected"])
        self.assertEqual(report["risk_level"], "high")
        self.assertTrue(
            any("Declared family looks like openai" in item for item in report["contradictions"])
        )

    def test_anthropic_adapter_smoke(self) -> None:
        server = MockRelayServer("anthropic-sonnet").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "anthropic",
                    "MODEL_AUTH_BASE_URL": server.anthropic_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "claude-3-7-sonnet",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "anthropic")
        self.assertFalse(report["mismatch_detected"])

    def test_gemini_adapter_smoke(self) -> None:
        server = MockRelayServer("gemini-flash").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "gemini",
                    "MODEL_AUTH_BASE_URL": server.gemini_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "gemini-2.0-flash",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "gemini")
        self.assertFalse(report["mismatch_detected"])

    def test_invalid_json_response_emits_json_error(self) -> None:
        server = MockRelayServer("invalid-json").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "gpt-4o",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "unreachable")
        self.assertTrue(any("Invalid JSON" in item for item in report["contradictions"]))

    def test_invalid_json_response_redacts_gemini_api_key(self) -> None:
        secret = "SECRET_KEY_REPRO_123"
        server = MockRelayServer("invalid-json").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "gemini",
                    "MODEL_AUTH_BASE_URL": server.gemini_base_url,
                    "MODEL_AUTH_API_KEY": secret,
                    "MODEL_AUTH_MODEL": "gemini-2.0-flash",
                }
            )
        finally:
            server.stop()

        serialized = json.dumps(report)
        self.assertEqual(code, 1)
        self.assertNotIn(secret, serialized)
        self.assertNotIn("?key=", serialized)

    def test_process_env_wins_over_env_file_across_key_order(self) -> None:
        server = MockRelayServer("openai-premium").start()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                (temp_path / ".env").write_text("MODEL_AUTH_API_KEY=file-key\n", encoding="utf-8")
                code, report = self.run_probe(
                    {
                        "MODEL_AUTH_PROTOCOL": "openai",
                        "MODEL_AUTH_BASE_URL": server.openai_base_url,
                        "OPENAI_API_KEY": "env-key",
                        "MODEL_AUTH_MODEL": "gpt-4o",
                    },
                    cwd=temp_path,
                )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertIn("env:OPENAI_API_KEY", report["runtime"]["config_sources"])
        self.assertFalse(
            any(source.startswith("env-file:") and source.endswith(":MODEL_AUTH_API_KEY")
                for source in report["runtime"]["config_sources"])
        )

    def test_codex_protocol_hint_is_used_for_non_inferable_model(self) -> None:
        server = MockRelayServer("anthropic-sonnet").start()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                codex_dir = temp_path / ".codex"
                codex_dir.mkdir()
                (codex_dir / "config.toml").write_text(
                    "\n".join(
                        [
                            'model = "private-relay-model"',
                            'protocol = "anthropic"',
                            f'base_url = "{server.anthropic_base_url}"',
                        ]
                    ),
                    encoding="utf-8",
                )
                code, report = self.run_probe(
                    {
                        "USERPROFILE": str(temp_path),
                        "HOME": str(temp_path),
                    },
                    cwd=temp_path,
                )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["runtime"]["protocol"], "anthropic")
        self.assertIn("codex:config.toml:protocol", report["runtime"]["config_sources"])

    def test_mistral_profile_detected(self) -> None:
        server = MockRelayServer("mistral").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "mistral-large",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "mistral")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)

    def test_kimi_profile_detected(self) -> None:
        server = MockRelayServer("kimi").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "kimi-k2.6",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "kimi")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)

    def test_minimax_profile_detected(self) -> None:
        server = MockRelayServer("minimax").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "minimax-m2.7",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "minimax")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)

    def test_deepseek_reasoner_profile_detected(self) -> None:
        server = MockRelayServer("deepseek-reasoner").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "deepseek-v4",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "deepseek")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)

    def test_glm_premium_profile_detected(self) -> None:
        server = MockRelayServer("glm-premium").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "openai",
                    "MODEL_AUTH_BASE_URL": server.openai_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "glm-5.2",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "glm")
        self.assertFalse(report["mismatch_detected"])
        self.assertGreaterEqual(report["confidence"], 0.7)
        self.assertEqual(report["declared_identity"]["family"], "glm")
        self.assertEqual(report["declared_identity"]["tier"], "premium")

    def test_anthropic_haiku_profile_detected(self) -> None:
        server = MockRelayServer("anthropic-haiku").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "anthropic",
                    "MODEL_AUTH_BASE_URL": server.anthropic_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "claude-haiku-4.5",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "anthropic")
        self.assertFalse(report["mismatch_detected"])

    def test_gemini_pro_profile_detected(self) -> None:
        server = MockRelayServer("gemini-pro").start()
        try:
            code, report = self.run_probe(
                {
                    "MODEL_AUTH_PROTOCOL": "gemini",
                    "MODEL_AUTH_BASE_URL": server.gemini_base_url,
                    "MODEL_AUTH_API_KEY": "test-key",
                    "MODEL_AUTH_MODEL": "gemini-3.1-pro",
                }
            )
        finally:
            server.stop()

        self.assertEqual(code, 0)
        self.assertEqual(report["candidate_models"][0]["family"], "gemini")
        self.assertFalse(report["mismatch_detected"])


class RiskAssessmentTests(unittest.TestCase):
    def test_low_confidence_cross_family_result_is_inconclusive(self) -> None:
        risk, mismatch_detected = probe_models.assess_risk(
            {"family": "openai", "tier": "premium"},
            {"family": "qwen", "tier": "small"},
            confidence=0.45,
        )

        self.assertEqual(risk, "medium")
        self.assertFalse(mismatch_detected)


if __name__ == "__main__":
    unittest.main()
