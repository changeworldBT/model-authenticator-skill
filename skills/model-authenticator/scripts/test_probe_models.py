#!/usr/bin/env python3
"""Tests for the model-authenticator probe script."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from mock_model_server import MockRelayServer

SCRIPT_PATH = Path(__file__).with_name("probe_models.py")


class ProbeModelsIntegrationTests(unittest.TestCase):
    maxDiff = None

    def run_probe(self, env_overrides: dict[str, str]) -> tuple[int, dict]:
        env = os.environ.copy()
        env.update(env_overrides)
        env.pop("OPENAI_API_KEY", None)
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("GEMINI_API_KEY", None)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
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


if __name__ == "__main__":
    unittest.main()
