# `execution/` — FUTURE module (not implemented in the MVP)

This package reserves the namespace for the **agentic EXECUTION + self-healing**
phase. It is intentionally empty.

## Why it is empty on purpose

The hard privilege boundary of QAIA is that **GENERATION has no execution
capability**. A `.feature` is untrusted input and a prompt-injection vector; the
generation phase therefore has no shell, no subprocess, no tool/MCP access. The
emptiness of this package is part of that guarantee.

## What will live here later

An `Executor` adapter implementing `qaia.ports.Executor.run_and_heal(suite, ctx)`:

- Runs `claude -p` **headless as a subprocess**, inside a **separate hardened
  container** (drop all caps, no Docker socket, restricted egress, only the
  workspace mounted) — never sharing the generation process.
- Uses the whitelist from `config/allowed_tools.yaml` as the `--allowedTools` set.
  `ExecutionContext.allowed_tools` already carries this in the port signature.
- Runs the generated tests, reads failures, patches, repeats up to
  `ExecutionContext.max_iterations`, then returns an `ExecutionReport`.

It slots into `GenerationPipeline.run` at one well-defined point — **between write
and publish** — so it can heal locally and then open a green PR, without the
generation module ever changing.
