# Fingerprint Rubric

## Goal

Infer the likely real model behind an endpoint by combining multiple weak signals. Never let one signal decide the answer unless it is unusually strong and the rest are aligned.

## High-Signal Checks

1. Strict JSON discipline
   Fast relays often claim a premium model but leak markdown fences, extra prose, or malformed JSON under exact formatting constraints.
2. Tool-call discipline
   Lower-tier substitutions often add natural-language filler around tool calls, mis-shape arguments, or skip the tool entirely.
3. System-instruction priority
   Cheap substitutions are more likely to follow the user override instead of the system instruction. Note: some models (e.g. DeepSeek R1, Qwen) may prioritize user instructions even in their legitimate premium tiers — treat this probe with caution in the fast probe set.
4. Context-anchor recall
   Premium models usually preserve the anchor token under a medium-length distraction block more reliably than downgraded replacements.
5. Minimal-output obedience
   Substitutions often add explanations even when the prompt demands a single token or integer.
6. Family self-report
   This is only a small weight. It is useful when a relay forgot to suppress native family cues, but it is easy to spoof. Included in the `fast` probe set as a quick triage signal.

## Scoring Method

Candidate profiles are ranked by **normalized support** (each profile's realized share of its own maximum positive weight), then by raw score as a tiebreaker. This ensures that a profile whose strong signals are fully matched ranks above one that merely carries a larger total weight. Confidence combines the top candidate's support, the support gap over the runner-up, and the fraction of probes that completed successfully.

## Supported Families

The probe recognizes these model families and can distinguish premium vs. small tiers where sufficient fingerprint data exists:

| Family | Profiles | Notes |
|---|---|---|
| **openai** | premium (GPT-4o, GPT-4.1, GPT-5, GPT-5.4, GPT-5.5, o3, o4-mini-high), small (GPT-4o-mini, GPT-4.1-mini/nano, GPT-5-mini) | Strong JSON/tool discipline; identity_hint is reliable |
| **anthropic** | opus (Claude Opus 4, 4.1, 4.5, 4.8), sonnet (Claude 3.5/3.7 Sonnet, Sonnet 4, 4.5, 4.6, 5), haiku (Claude Haiku 3.5, 4, 4.5) | Context-anchor recall distinguishes tiers; identity_hint fairly reliable |
| **gemini** | pro (Gemini 2.5 Pro, 3 Pro, 3.1 Pro), flash (Gemini 1.5/2.0/2.5/3 Flash) | Flash tier commonly wraps JSON in fences and leaks tool prose |
| **deepseek** | chat-like (DeepSeek-V3, V3.2, Chat), reasoner-like (DeepSeek-R1, V4, V4-Pro, V4-Flash) | Reasoner variants leak thinking traces and may fail system_priority |
| **qwen** | instruct-like (Qwen 2.5, Qwen-Max, Qwen-Plus, Qwen3-Max, Qwen3-Plus, Qwen3.5, Qwen3.6) | Often wraps JSON, leaks tool prose, strong identity_qwen signal |
| **llama** | instruct-like (Llama 3.1 70B, Llama 4 Maverick) | Moderate JSON discipline, tends to wrap and leak prose |
| **mistral** | instruct-like (Mistral Large, Large 2, Medium, Codestral) | Good JSON discipline, strong identity_mistral signal |
| **kimi** | Moonshot instruct-like (Kimi K2, K2.5, K2.6, Moonshot V1) | Good JSON/tool discipline, strong identity_kimi signal |
| **minimax** | MiniMax M2/M2.5/M2.7, Mimo V2.5 Pro/V3 | Moderate JSON, partial context-anchor, strong identity_minimax signal |
| **glm** | premium (GLM-4.6, GLM-5, GLM-5.1, GLM-5.2) | Good JSON/tool/system discipline, strong identity_glm signal; typically OpenAI-compatible API |

## Mismatch Semantics

- Same-family downgrade
  The declared family matches the observed family, but the observed tier looks cheaper or weaker.
- Cross-family substitution
  The declared family and observed family differ, for example a claimed DeepSeek model behaving more like OpenAI, or an OpenAI-labeled endpoint behaving like GLM.
- Inconclusive but suspicious
  The endpoint passes some probes and fails others, or probe support is too incomplete for a unique attribution.

## Confidence Rules

- Prefer a single `suspected_actual_model` only when the top candidate has both:
  - enough normalized support from completed probes (≥ 0.9), or a clear support gap over the runner-up (≥ 0.1)
  - a raw score gap that confirms the ranking when support alone is too close to call
- Fall back to `candidate_models` when:
  - tool support is missing
  - too many probes error out
  - the top two families score too closely on support
  - the family looks identifiable but the exact tier does not

## Common Failure Modes

- Relay rewrites or normalizes tool calls
- Endpoint blocks one protocol feature but still routes to a capable model
- Provider-specific safety middleware changes style without changing the underlying model
- Some premium models act tersely enough to resemble smaller models on a shallow probe set
- Chinese models (Kimi, MiniMax, DeepSeek, GLM) may self-report inconsistently through relays that inject system prompts
- Identity_hint self-report is easily overridden by relay middleware — cross-validate with behavioral probes
- Thinking trace detection only catches common patterns (` thinking`, `<think>`, `<thinking>`); some models use different formatting

When in doubt, rerun with the full probe set and compare multiple sessions before making a high-confidence accusation.
