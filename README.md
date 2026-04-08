# Model Authenticator Skill

[简体中文](./README.zh-CN.md)

Behavioral probe skill for detecting the likely real model behind relay, proxy, and model-routing APIs instead of trusting the advertised model name.

This repository contains a single portable skill at `skills/model-authenticator/`. It is designed for skills-compatible agents and was built to audit the common failure mode where a relay claims a premium model but actually serves a cheaper substitute.

## What It Does

- Probe a live endpoint through repeated behavior tests instead of trusting the returned `model` field
- Support OpenAI-compatible, Anthropic-compatible, and Gemini-style APIs
- Infer likely family and tier from JSON discipline, tool-call behavior, instruction priority, context recall, and family hints
- Return either a strong single candidate or a ranked candidate list when confidence is lower
- Flag likely downgrade or cross-family substitution with explicit evidence
- Auto-discover configured `model` and `base_url` before asking for overrides

## Repository Layout

- `skills/model-authenticator/SKILL.md`: Trigger description and runtime workflow
- `skills/model-authenticator/agents/openai.yaml`: Optional UI metadata
- `skills/model-authenticator/references/`: Scoring rubric and protocol notes
- `skills/model-authenticator/scripts/probe_models.py`: Main probe CLI
- `skills/model-authenticator/scripts/mock_model_server.py`: Local mock relay for validation
- `skills/model-authenticator/scripts/test_probe_models.py`: Integration tests

## Requirements

- Python 3.11 or newer
- A reachable endpoint to test
- Optional API key if the target relay requires authentication

## Installation

Copy this folder into your runtime's local skills directory:

```text
skills/model-authenticator
```

For Codex-style local setups in this environment, that is typically:

```powershell
Copy-Item -Recurse .\skills\model-authenticator "$HOME\.codex\skills\"
```

The exact install path depends on the client. The skill itself is the `skills/model-authenticator/` folder.

## Configuration Discovery

The probe script resolves configuration in this order:

1. CLI flags
2. `MODEL_AUTH_*` environment variables
3. Provider-specific variables such as `OPENAI_*`, `ANTHROPIC_*`, and `GEMINI_*`
4. `.env.local` and `.env` in the current working directory
5. `~/.codex/config.toml`
6. `~/.config/opencode/opencode.jsonc`

This makes zero-argument probing possible when your relay is already configured locally.

## Usage

### Zero-Argument Probe

```bash
python skills/model-authenticator/scripts/probe_models.py
```

### Explicit OpenAI-Compatible Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol openai --base-url https://example.com/v1 --api-key YOUR_KEY --model gpt-4o
```

### Explicit Anthropic-Compatible Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol anthropic --base-url https://example.com --api-key YOUR_KEY --model claude-3-7-sonnet
```

### Explicit Gemini-Style Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol gemini --base-url https://example.com/v1beta --api-key YOUR_KEY --model gemini-2.0-flash
```

### Fail the Process When a Mismatch Is Detected

```bash
python skills/model-authenticator/scripts/probe_models.py --fail-on-mismatch
```

## Output Model

The script emits JSON with these key fields:

- `status`: `ok`, `partial`, or `unreachable`
- `declared_model`: the claimed model you targeted
- `suspected_actual_model`: strong single conclusion when confidence is high enough
- `candidate_models`: ranked fallback list when the evidence is weaker
- `confidence`: aggregated confidence score
- `risk_level`: `low`, `medium`, `high`, or `unknown`
- `mismatch_detected`: whether the endpoint likely substituted or downgraded the declared model
- `evidence`: high-signal reasons supporting the result
- `contradictions`: conflicting signals or connectivity failures

If `status` is `unreachable`, do not infer the real model. Fix connectivity first.

## How It Scores

The probe set combines several lightweight checks:

- Strict JSON formatting
- Minimal-output obedience
- System-instruction priority
- Context-anchor recall under distraction
- Tool-call discipline
- Family hint probe

These features are matched against candidate profiles such as OpenAI premium, OpenAI small-tier, Anthropic Sonnet-like, Gemini Flash-like, Qwen instruct-like, and DeepSeek-like behavior.

Detailed scoring notes live in:

- `skills/model-authenticator/references/fingerprint-rubric.md`
- `skills/model-authenticator/references/protocol-notes.md`

## Validation

Run the included tests:

```bash
python skills/model-authenticator/scripts/test_probe_models.py
```

Quick structural validation:

```bash
python C:\Users\84915\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/model-authenticator
```

## Limitations

- This skill performs behavioral attribution, not cryptographic proof
- Some relays rewrite or normalize responses, which can blur family-level signals
- Middleware can alter style without changing the underlying model
- A single session may be inconclusive; rerun when the endpoint is unstable or partially implemented

## Repository

```text
https://github.com/changeworldBT/model-authenticator-skill
```
