---
name: model-authenticator
description: Detect the likely actual model behind relay, proxy, or model-routing endpoints instead of trusting the advertised model name. Use when Codex needs to verify whether a provider swapped a premium model for a cheaper one, audit suspicious behavior from an OpenAI-compatible, Anthropic-compatible, or Gemini-style API, identify the real family or tier behind already-configured base_url and API key credentials, or produce an evidence-backed candidate list with confidence and mismatch risk.
---

# Model Authenticator

Use this skill to probe a live endpoint and infer the likely underlying model family and tier from behavior, not branding.

Treat endpoint metadata such as the returned `model` field as low-trust evidence. Favor repeated behavioral probes and candidate scoring.

## Quick Start

Run the bundled script with no flags first:

```bash
python scripts/probe_models.py
```

The script resolves configuration in this order:
1. Explicit CLI flags
2. `MODEL_AUTH_*` environment variables
3. Provider-specific environment variables such as `OPENAI_*`, `ANTHROPIC_*`, or `GEMINI_*`
4. `.env.local` and `.env` in the current working directory
5. `~/.codex/config.toml` for a fallback model name when available
6. `~/.config/opencode/opencode.jsonc` for OpenAI-compatible provider and base URL hints

If autodiscovery misses something, rerun with explicit overrides:

```bash
python scripts/probe_models.py --protocol openai --base-url https://example.com/v1 --api-key "$env:OPENAI_API_KEY" --model gpt-4o
python scripts/probe_models.py --protocol anthropic --base-url https://example.com --api-key "$env:ANTHROPIC_API_KEY" --model claude-3-7-sonnet
python scripts/probe_models.py --protocol gemini --base-url https://example.com/v1beta --api-key "$env:GEMINI_API_KEY" --model gemini-2.0-flash
```

## Workflow

1. Resolve runtime configuration before asking the user for credentials. Assume the endpoint is already configured unless discovery proves otherwise.
2. Allow local or self-hosted relays to run without an API key when the endpoint accepts anonymous requests.
3. Run `python scripts/probe_models.py` with the default `full` probe set when the question is high-stakes or the relay already looks suspicious.
4. Run `python scripts/probe_models.py --probe-set fast` only when you need a quick triage first.
5. Read the JSON report and summarize:
   - `status`
   - `declared_model`
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

- `suspected_actual_model`: only trust this when `confidence` is strong and the score gap is meaningful.
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
python C:\Users\84915\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\84915\.codex\skills\model-authenticator
```

Forward-test by using the skill on a real relay question phrased the way a user would ask it. Do not trust a passing result until the script output and the natural-language summary agree.
