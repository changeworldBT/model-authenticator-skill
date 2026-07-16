# Model Authenticator Skill

[简体中文](./README.zh-CN.md)

Behavioral probe skill for detecting the likely real model behind relay, proxy, and model-routing APIs instead of trusting the advertised model name.

This repository contains a single portable skill at `skills/model-authenticator/`. It is designed for skills-compatible agents and was built to audit the common failure mode where a relay claims a premium model but actually serves a cheaper substitute.

## What It Does

- Probe a live endpoint through repeated behavior tests instead of trusting the returned `model` field
- Support OpenAI-compatible, Anthropic-compatible, and Gemini-style APIs
- Infer likely family and tier from JSON discipline, tool-call behavior, instruction priority, context recall, thinking traces, and family hints
- Return either a strong single candidate or a ranked candidate list when confidence is lower
- Flag likely downgrade or cross-family substitution with explicit evidence
- Auto-discover configured `model` and `base_url` before asking for overrides
- Recognize 10 model families: OpenAI, Anthropic, Gemini, DeepSeek, Qwen, Llama, Mistral, Kimi, MiniMax, and GLM (Z.ai)

## Supported Families

| Family | Tiers | Example Models |
|---|---|---|
| **openai** | premium, small | GPT-5.5, GPT-5.4, GPT-5, GPT-4.1, o3, o4-mini-high; GPT-5-mini, GPT-4o-mini, GPT-4.1-nano |
| **anthropic** | premium (opus/sonnet), small (haiku) | Claude Opus 4.8, Sonnet 5, Sonnet 4.6; Haiku 4.5 |
| **gemini** | premium (pro), small (flash) | Gemini 3.1 Pro, Gemini 3 Pro, Gemini 2.5 Pro; Gemini 3 Flash, 2.5 Flash |
| **deepseek** | chat, reasoner | DeepSeek V4, V4-Pro, V4-Flash, V3.2; DeepSeek-R1 |
| **qwen** | instruct | Qwen3.6, Qwen3.5, Qwen3-Max, Qwen3-Plus |
| **llama** | instruct | Llama 4 Maverick, Llama 3.1 70B |
| **mistral** | instruct | Mistral Large 2, Codestral |
| **kimi** | instruct | Kimi K2.6, K2.5, Moonshot V1 |
| **minimax** | instruct | MiniMax M2.7, M2.5, Mimo V3 |
| **glm** | premium | GLM-5.2, GLM-5.1, GLM-5, GLM-4.6 |

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

The probe script resolves each effective value in this order:

1. CLI flags
2. `MODEL_AUTH_*` environment variables
3. Provider-specific variables such as `OPENAI_*`, `ANTHROPIC_*`, and `GEMINI_*`
4. `.env.local` and `.env` in the current working directory
5. `~/.codex/config.toml`
6. `~/.config/opencode/opencode.jsonc`

This makes zero-argument probing possible when your relay is already configured locally.
Reports include `runtime.config_sources` so you can see which source actually supplied the model, base URL, API key, protocol, or defaults.

## Usage

### Zero-Argument Probe

```bash
python skills/model-authenticator/scripts/probe_models.py
```

### Explicit OpenAI-Compatible Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol openai --base-url https://example.com/v1 --api-key YOUR_KEY --model gpt-5.5
```

### Explicit GLM/Zhipu Endpoint (OpenAI-compatible)

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol openai --base-url https://open.bigmodel.cn/api/paas/v4 --api-key YOUR_KEY --model glm-5.2
```

### Explicit Anthropic-Compatible Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol anthropic --base-url https://example.com --api-key YOUR_KEY --model claude-sonnet-5
```

### Explicit Gemini-Style Endpoint

```bash
python skills/model-authenticator/scripts/probe_models.py --protocol gemini --base-url https://example.com/v1beta --api-key YOUR_KEY --model gemini-3.1-pro
```

### Fail the Process Only for a Confirmed Mismatch

```bash
python skills/model-authenticator/scripts/probe_models.py --fail-on-mismatch
```

The command exits with code `2` only when the observed family/tier conflicts with the declared label **and** confidence is at least `0.7`. A low-confidence contradiction remains `medium` risk and does not fail automation.

### Fast Triage, Saved Report, and Timeout

```bash
python skills/model-authenticator/scripts/probe_models.py --probe-set fast
python skills/model-authenticator/scripts/probe_models.py --report-path report.json
python skills/model-authenticator/scripts/probe_models.py --timeout 60
```

Run `python skills/model-authenticator/scripts/probe_models.py --help` for the full CLI surface.

## Output Model

The script emits JSON with these key fields:

- `status`: `ok`, `partial`, or `unreachable`
- `declared_model`: the claimed model you targeted
- `runtime`: protocol, masked base URL, declared model, and `config_sources`
- `suspected_actual_model`: strong single conclusion when confidence is high enough
- `candidate_models`: ranked fallback list when the evidence is weaker
- `confidence`: aggregated confidence score
- `risk_level`: `low`, `medium`, `high`, or `unknown`
- `mismatch_detected`: whether the endpoint likely substituted or downgraded the declared model
- `evidence`: high-signal reasons supporting the result
- `contradictions`: conflicting signals or connectivity failures

If `status` is `unreachable`, do not infer the real model. Fix connectivity first. For high-cost decisions, run the full probe at least twice in separate sessions and compare both reports before escalating a confirmed mismatch.

## How It Scores

The probe set combines several lightweight checks:

- Strict JSON formatting
- Minimal-output obedience
- System-instruction priority
- Context-anchor recall under distraction
- Tool-call discipline
- Thinking trace detection
- Family hint probe

Candidates are ranked by **normalized support** (each profile's realized share of its own maximum positive weight), then by raw score as a tiebreaker. This prevents profiles with larger total weights from always winning over profiles that match their signals perfectly.

Detailed scoring notes live in:

- `skills/model-authenticator/references/fingerprint-rubric.md`
- `skills/model-authenticator/references/protocol-notes.md`

## Validation

Run the included tests:

```bash
python skills/model-authenticator/scripts/test_probe_models.py
```

## Limitations

- This skill performs behavioral attribution, not cryptographic proof
- Some relays rewrite or normalize responses, which can blur family-level signals
- Middleware can alter style without changing the underlying model
- A single session may be inconclusive; rerun when the endpoint is unstable or partially implemented
- A behavioral profile cannot cryptographically prove an exact hidden SKU, ownership, or provider deployment

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) before changing probe behavior, candidate profiles, protocol adapters, or validation fixtures.

## Contributors

See the live GitHub contributors graph: <https://github.com/changeworldBT/model-authenticator-skill/graphs/contributors>.

## Repository

```text
https://github.com/changeworldBT/model-authenticator-skill
```
