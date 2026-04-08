#!/usr/bin/env python3
"""Local mock server for validating model-authenticator probes."""

from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

EXPECTED_TOOL_NAME = "record_probe_result"
EXPECTED_TOOL_ARGS = {"color": "blue", "count": 7}


@dataclass(frozen=True)
class ProbeReply:
    text: str = ""
    tool_call: dict[str, Any] | None = None


PROFILES: dict[str, dict[str, ProbeReply]] = {
    "openai-premium": {
        "json_strict": ProbeReply(text='{"alpha":4,"beta":11,"gamma":"red"}'),
        "minimal_math": ProbeReply(text="1073"),
        "system_priority": ProbeReply(text="SYS-PRIORITY-41"),
        "context_anchor": ProbeReply(text="teal-17-omega"),
        "tool_only": ProbeReply(tool_call={"name": EXPECTED_TOOL_NAME, "arguments": EXPECTED_TOOL_ARGS}),
        "identity_hint": ProbeReply(text="openai"),
    },
    "openai-mini": {
        "json_strict": ProbeReply(text='{"alpha":4,"beta":11,"gamma":"red"}'),
        "minimal_math": ProbeReply(text="1073"),
        "system_priority": ProbeReply(text="SYS-PRIORITY-41"),
        "context_anchor": ProbeReply(text="teal-17-gamma"),
        "tool_only": ProbeReply(tool_call={"name": EXPECTED_TOOL_NAME, "arguments": EXPECTED_TOOL_ARGS}),
        "identity_hint": ProbeReply(text="openai"),
    },
    "anthropic-sonnet": {
        "json_strict": ProbeReply(text='{"alpha":4,"beta":11,"gamma":"red"}'),
        "minimal_math": ProbeReply(text="1073"),
        "system_priority": ProbeReply(text="SYS-PRIORITY-41"),
        "context_anchor": ProbeReply(text="teal-17-omega"),
        "tool_only": ProbeReply(tool_call={"name": EXPECTED_TOOL_NAME, "arguments": EXPECTED_TOOL_ARGS}),
        "identity_hint": ProbeReply(text="anthropic"),
    },
    "gemini-flash": {
        "json_strict": ProbeReply(text="```json\n{\"alpha\":4,\"beta\":11,\"gamma\":\"red\"}\n```"),
        "minimal_math": ProbeReply(text="1073"),
        "system_priority": ProbeReply(text="SYS-PRIORITY-41"),
        "context_anchor": ProbeReply(text="teal-17-omega"),
        "tool_only": ProbeReply(
            text="Using the function.",
            tool_call={"name": EXPECTED_TOOL_NAME, "arguments": EXPECTED_TOOL_ARGS},
        ),
        "identity_hint": ProbeReply(text="gemini"),
    },
    "qwen-substitute": {
        "json_strict": ProbeReply(text="```json\n{\"alpha\":4,\"beta\":11,\"gamma\":\"red\"}\n```"),
        "minimal_math": ProbeReply(text="The answer is 1073."),
        "system_priority": ProbeReply(text="USER-OVERRIDE"),
        "context_anchor": ProbeReply(text="teal-17-omega"),
        "tool_only": ProbeReply(
            text="I will call the tool now.",
            tool_call={"name": EXPECTED_TOOL_NAME, "arguments": EXPECTED_TOOL_ARGS},
        ),
        "identity_hint": ProbeReply(text="qwen"),
    },
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _extract_probe_name(payload: dict[str, Any], protocol: str) -> tuple[str, str]:
    if protocol == "openai":
        messages = payload.get("messages", [])
        combined = "\n".join(str(message.get("content", "")) for message in messages)
        model = str(payload.get("model", "unknown-model"))
    elif protocol == "anthropic":
        content_parts = []
        for message in payload.get("messages", []):
            content = message.get("content", "")
            if isinstance(content, list):
                content_parts.extend(str(part.get("text", "")) for part in content if isinstance(part, dict))
            else:
                content_parts.append(str(content))
        combined = "\n".join(content_parts)
        model = str(payload.get("model", "unknown-model"))
    else:
        contents = payload.get("contents", [])
        parts = []
        for item in contents:
            for part in item.get("parts", []):
                if "text" in part:
                    parts.append(str(part["text"]))
        combined = "\n".join(parts)
        model = str(payload.get("model", "unknown-model"))

    for line in combined.splitlines():
        if line.startswith("PROBE_ID:"):
            return line.split(":", 1)[1].strip(), model
    return "unknown_probe", model


def _openai_response(model: str, reply: ProbeReply) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": reply.text or ""}
    finish_reason = "stop"
    if reply.tool_call is not None:
        finish_reason = "tool_calls"
        message["tool_calls"] = [
            {
                "id": "call_mock_1",
                "type": "function",
                "function": {
                    "name": reply.tool_call["name"],
                    "arguments": json.dumps(reply.tool_call["arguments"], separators=(",", ":")),
                },
            }
        ]
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 24, "total_tokens": 144},
    }


def _anthropic_response(model: str, reply: ProbeReply) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    stop_reason = "end_turn"
    if reply.text:
        content.append({"type": "text", "text": reply.text})
    if reply.tool_call is not None:
        stop_reason = "tool_use"
        content.append(
            {
                "type": "tool_use",
                "id": "toolu_mock_1",
                "name": reply.tool_call["name"],
                "input": reply.tool_call["arguments"],
            }
        )
    return {
        "id": "msg_mock",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 120, "output_tokens": 24},
    }


def _gemini_response(model: str, reply: ProbeReply) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    if reply.text:
        parts.append({"text": reply.text})
    if reply.tool_call is not None:
        parts.append(
            {
                "functionCall": {
                    "name": reply.tool_call["name"],
                    "args": reply.tool_call["arguments"],
                }
            }
        )
    return {
        "candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}],
        "modelVersion": model,
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 24, "totalTokenCount": 144},
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "MockModelServer/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(raw_body or "{}")
        parsed = urlparse(self.path)

        if parsed.path.endswith("/chat/completions"):
            protocol = "openai"
        elif parsed.path.endswith("/v1/messages"):
            protocol = "anthropic"
        elif parsed.path.endswith(":generateContent"):
            protocol = "gemini"
        else:
            self._send_json(404, {"error": {"message": f"Unknown path: {self.path}"}})
            return

        probe_name, model = _extract_probe_name(payload, protocol)
        profile = getattr(self.server, "profile", "openai-premium")
        reply = PROFILES.get(profile, {}).get(probe_name, ProbeReply(text="unknown"))

        if protocol == "openai":
            body = _openai_response(model, reply)
        elif protocol == "anthropic":
            body = _anthropic_response(model, reply)
        else:
            body = _gemini_response(model, reply)

        self._send_json(200, body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockRelayServer:
    def __init__(self, profile: str) -> None:
        self.profile = profile
        self.port = _find_free_port()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), _Handler)
        self.httpd.profile = profile  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> "MockRelayServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

    @property
    def openai_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    @property
    def anthropic_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def gemini_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1beta"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the local mock relay server.")
    parser.add_argument("--profile", default="openai-premium", choices=sorted(PROFILES))
    args = parser.parse_args()

    server = MockRelayServer(args.profile).start()
    try:
        print(f"Mock relay server running on port {server.port} with profile {args.profile}")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
