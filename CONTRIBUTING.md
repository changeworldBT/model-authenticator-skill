# Contributing

Thanks for improving `model-authenticator`.

Open an issue or pull request for probe behavior, candidate profiles, protocol adapters, documentation, or validation fixtures. Keep changes narrow and explain what user-facing failure mode the change addresses.

## Before a Pull Request

Run the integration tests:

```bash
python skills/model-authenticator/scripts/test_probe_models.py -v
```

Run structural validation when the local skill-creator validator is available:

```bash
python C:\Users\84915\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/model-authenticator
```

If you change scoring, add or update a mock profile or regression test so the new behavior is reproducible without hitting a live provider.

## Evidence Standard

This project performs behavioral attribution, not cryptographic proof. Avoid claiming an exact hidden SKU unless the score gap and probe evidence support it. Prefer `candidate_models` and clear uncertainty when signals are mixed.
