# Fingerprint Rubric

## Goal

Infer the likely real model behind an endpoint by combining multiple weak signals. Never let one signal decide the answer unless it is unusually strong and the rest are aligned.

## High-Signal Checks

1. Strict JSON discipline
   Fast relays often claim a premium model but leak markdown fences, extra prose, or malformed JSON under exact formatting constraints.
2. Tool-call discipline
   Lower-tier substitutions often add natural-language filler around tool calls, mis-shape arguments, or skip the tool entirely.
3. System-instruction priority
   Cheap substitutions are more likely to follow the user override instead of the system instruction.
4. Context-anchor recall
   Premium models usually preserve the anchor token under a medium-length distraction block more reliably than downgraded replacements.
5. Minimal-output obedience
   Substitutions often add explanations even when the prompt demands a single token or integer.
6. Family self-report
   This is only a small weight. It is useful when a relay forgot to suppress native family cues, but it is easy to spoof.

## Mismatch Semantics

- Same-family downgrade
  The declared family matches the observed family, but the observed tier looks cheaper or weaker.
- Cross-family substitution
  The declared family and observed family differ, for example a claimed OpenAI model behaving more like Qwen or Gemini.
- Inconclusive but suspicious
  The endpoint passes some probes and fails others, or probe support is too incomplete for a unique attribution.

## Confidence Rules

- Prefer a single `suspected_actual_model` only when the top score has both:
  - enough absolute support from completed probes
  - a clear gap over the runner-up
- Fall back to `candidate_models` when:
  - tool support is missing
  - too many probes error out
  - the top two families score too closely
  - the family looks identifiable but the exact tier does not

## Common Failure Modes

- Relay rewrites or normalizes tool calls
- Endpoint blocks one protocol feature but still routes to a capable model
- Provider-specific safety middleware changes style without changing the underlying model
- Some premium models act tersely enough to resemble smaller models on a shallow probe set

When in doubt, rerun with the full probe set and compare multiple sessions before making a high-confidence accusation.
