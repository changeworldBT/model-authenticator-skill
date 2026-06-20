---
name: model-authenticator
description: Use when verifying, auditing, or identifying the real model behind a relay, proxy, router, or OpenAI/Anthropic/Gemini-compatible API, especially for suspected model substitution, downgrade, spoofed model names, or evidence-backed model attribution.
---

# Model Authenticator

Use this skill to probe a live endpoint and infer the likely underlying model family and tier from behavior, not branding.

Treat endpoint metadata such as the returned `model` field as low-trust evidence. Favor repeated behavioral probes and candidate scoring.

## Quick Start

From `skills/model-authenticator/`, run the bundled script with no flags first:

```bash
python scripts/probe_models.py
```

The script resolves each effective value in this order:
1. Explicit CLI flags
2. `MODEL_AUTH_*` environment variables
3. Provider-specific environment variables such as `OPENAI_*`, `ANTHROPIC_*`, or `GEMINI_*`
4. `.env.local` and `.env` in the current working directory
5. `~/.codex/config.toml` for fallback model, base URL, API key, or protocol hints
6. `~/.config/opencode/opencode.jsonc` for OpenAI-compatible provider, model, and base URL hints

If autodiscovery misses something, rerun with explicit overrides:

```bash
python scripts/probe_models.py --protocol openai --base-url https://example.com/v1 --api-key "$env:OPENAI_API_KEY" --model gpt-5.5
python scripts/probe_models.py --protocol openai --base-url https://open.bigmodel.cn/api/paas/v4 --api-key "$env:ZHIPU_API_KEY" --model glm-5.2
python scripts/probe_models.py --protocol anthropic --base-url https://example.com --api-key "$env:ANTHROPIC_API_KEY" --model claude-sonnet-5
python scripts/probe_models.py --protocol gemini --base-url https://example.com/v1beta --api-key "$env:GEMINI_API_KEY" --model gemini-3.1-pro
```

## Supported Families

The probe recognizes these model families:

| Family | Tiers | Example Models |
|---|---|---|
| **openai** | premium, small | GPT-5.5, GPT-5.4, GPT-5, GPT-4.1, o3; GPT-5-mini, GPT-4o-mini |
| **anthropic** | premium (opus/sonnet), small (haiku) | Opus 4.8, Sonnet 5, Sonnet 4.6; Haiku 4.5 |
| **gemini** | premium (pro), small (flash) | Gemini 3.1 Pro; Gemini 3 Flash |
| **deepseek** | chat, reasoner | DeepSeek V4, V4-Flash; DeepSeek-R1 |
| **qwen** | instruct | Qwen3.6, Qwen3-Max, Qwen3-Plus |
| **llama** | instruct | Llama 4 Maverick |
| **mistral** | instruct | Mistral Large 2, Codestral |
| **kimi** | instruct | Kimi K2.6, Moonshot V1 |
| **minimax** | instruct | MiniMax M2.7, Mimo V3 |
| **glm** | premium | GLM-5.2, GLM-5.1, GLM-5, GLM-4.6 |

## Workflow

1. Resolve runtime configuration before asking the user for credentials. Assume the endpoint is already configured unless discovery proves otherwise.
2. Allow local or self-hosted relays to run without an API key when the endpoint accepts anonymous requests.
3. Run `python scripts/probe_models.py` with the default `full` probe set when the question is high-stakes or the relay already looks suspicious.
4. Run `python scripts/probe_models.py --probe-set fast` only when you need a quick triage first.
5. Read the JSON report and summarize:
   - `status`
   - `declared_model`
   - `runtime.config_sources`
   - `suspected_actual_model` or `candidate_models`
   - `confidence`
   - `risk_level`
   - `evidence`
   - `contradictions`
6. If the report says `mismatch_detected: true`, state clearly whether the relay looks like:
   - same family but downgraded tier
   - different family entirely
   - inconclusive, but suspicious
7. If confidence is below `0.7`, present the top candidate set instead of inventing a single exact model.
8. If `status` is `unreachable`, fix connectivity or credentials first. Do not guess the underlying model from zero successful probes.

## Interpreting Results

Use the script output as the primary evidence source.

- `suspected_actual_model`: only trust this when `confidence` is strong and the support gap is meaningful.
- `candidate_models`: use this when the endpoint behaves like a family or tier but not a uniquely identifiable SKU.
- `risk_level`:
  - `high`: strong evidence of substitution or cross-family mismatch
  - `medium`: inconsistent or incomplete evidence
  - `low`: declared model and observed behavior are broadly aligned
- `reported_models`: low-trust metadata echoed by the endpoint. Helpful for contradictions, not for proof.

When the report conflicts with the endpoint's claimed model, explicitly say that the behavioral evidence outweighs the self-reported label.

## References

- Read [references/fingerprint-rubric.md](references/fingerprint-rubric.md) when you need the scoring rationale, expected failure modes, or mismatch semantics.
- Read [references/protocol-notes.md](references/protocol-notes.md) when an endpoint partially implements OpenAI, Anthropic, or Gemini semantics and you need to choose overrides or explain adapter-specific quirks.

## Validation

Use these commands when maintaining this skill:

```bash
python scripts/test_probe_models.py
```

Forward-test by using the skill on a real relay question phrased the way a user would ask it. Do not trust a passing result until the script output and the natural-language summary agree.
