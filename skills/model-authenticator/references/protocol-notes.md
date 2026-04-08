# Protocol Notes

## OpenAI-Compatible

- Default path in the script is `chat/completions`.
- This is the most common relay shape and the best first choice unless the endpoint is clearly Anthropic- or Gemini-native.
- Many relays echo the requested `model` field back unchanged. Treat that as low-trust metadata.

## Anthropic-Compatible

- The script uses `POST /v1/messages` with `x-api-key` and `anthropic-version`.
- Tool results arrive as structured `tool_use` blocks, which the script normalizes into a common tool-call shape.
- Some relays emulate Anthropic poorly and may reject tools or system instructions; incomplete support should lower confidence, not force a wrong attribution.

## Gemini-Style

- The script uses `models/{model}:generateContent`.
- The adapter normalizes `functionCall` parts into the same tool-call representation used by the other protocols.
- Gemini-style endpoints vary the most in relay land. Be careful with low-confidence conclusions.

## Configuration Discovery

The script resolves configuration from:

1. CLI flags
2. `MODEL_AUTH_PROTOCOL`, `MODEL_AUTH_BASE_URL`, `MODEL_AUTH_API_KEY`, `MODEL_AUTH_MODEL`
3. Provider-specific variables such as:
   - `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`
   - `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
   - `GEMINI_BASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`
4. `.env.local` and `.env`
5. `~/.codex/config.toml` for a fallback model name
6. `~/.config/opencode/opencode.jsonc` for OpenAI-compatible provider and base URL hints

If the user says the endpoint is already configured, try zero-argument execution first before asking for overrides.

For local gateways, an API key may be optional. The script omits auth headers when no key can be resolved.
