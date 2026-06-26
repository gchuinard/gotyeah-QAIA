# CLAUDE.md — QAIA conventions & guardrails

Authoritative conventions for working in this repo. Read `PLAN.md` for the full design.

## Project overview

QAIA turns a spec into tests and opens a PR. **Build-now slice (MVP):** a Gherkin
`.feature` → one-shot Anthropic structured generation → pytest+httpx tests written
to `tests/generated/` → a GitHub PR. **Final vision (LATER, not built):** E2E
(Playwright), agentic execution + self-healing, and ticket sources (Jira/Linear
via MCP).

## Architecture & module boundaries

Ports & adapters. The core is a few Pydantic domain types (`qaia.domain.models`)
and `Protocol` seams (`qaia.ports`). **Adapters depend on ports, never on each
other** (no adapter→adapter imports). GENERATION (deterministic) and the future
EXECUTION+self-healing (agentic) communicate **only** through the
`GeneratedTestSuite` domain type, so they never import each other — this is the
non-monolithic, two-module constraint.

Pipeline: `load (SpecLoader) → generate (TestGenerator) → write (TestWriter) →
publish (PrPublisher)`. The optional `executor` stage is the reserved insertion
point between write and publish.

## Repository layout

`src/qaia/` — `domain/` (models, errors) · `ports.py` · `pipeline.py` · `cli.py` ·
`api/` (minimal FastAPI) · `specs/` (feature loader) · `generation/` (LLM client,
prompts, generator) · `writer/` · `github/` (PR publisher) · `execution/` (FUTURE,
empty). `tests/` holds the tool's own tests; `tests/generated/` is the output sink
(gitignored, excluded from collection).

## Development workflow

- `uv` for env/deps. `uv sync` to set up; `uv run <cmd>` to run tools.
- Generate: `uv run qaia generate examples/sample.feature` (`--dry-run` to skip the PR).
- API locally: `uv run uvicorn qaia.api.app:app --reload`.

## Coding conventions

- Python 3.12, full type hints, **`mypy --strict` clean**, `ruff` lint + format.
- Pydantic v2 models are the cross-module contract. Keep the LLM-facing schema
  (`LlmTestArtifacts`) flat and fully-required; provenance lives on
  `GeneratedTestSuite`, stamped by the generator, never by the LLM.
- New input source → new `SpecLoader` + `SourceKind`. New test target → new
  `TestGenerator` + `TestKind`. Additive; do not edit the pipeline.

## Configuration

- **Env-only** via `pydantic-settings`. Secrets are `SecretStr` (never logged/
  rendered). `.env` is gitignored; `.env.example` lists NAMES only.
- The Anthropic SDK reads `ANTHROPIC_API_KEY` itself; settings only assert presence.

## Generation module contract

One deterministic call: `messages.parse(model="claude-sonnet-4-6", max_tokens,
system, messages, output_format=LlmTestArtifacts)`. No assistant prefill, no
`budget_tokens`, `thinking` omitted. Prompts (`generation/prompts.py`) are
versioned and reviewable and contain NO tool/shell instructions.

## GitHub PR conventions

Branch `qaia/<feature-slug>-<short-uuid>`; one commit, all files under
`tests/generated/`. PR body carries provenance. **Never push the default branch,
never auto-merge** — the PR is the human review gate. PR creation uses the REST
Git Data API over `httpx` (no `gh` CLI, no subprocess).

## Security (REQUIRED)

- **GENERATION is a pure text→data transform.** No shell, no subprocess, no
  MCP/tool access, no filesystem write outside `tests/generated/`. A `.feature` is
  **untrusted input** and a prompt-injection vector; stripped of capability, the
  worst a hostile spec yields is bad test *text* a human reviews in a PR.
- **Generated code is untrusted data** — never `eval`/`exec`'d by the tool or on
  the Pi. It runs only in the target repo's PR CI, and later in the dedicated
  execution sandbox.
- **Filenames from the model are validated** (`^(test_[a-z0-9_]+|conftest)\.py$`,
  no separators/`..`/absolute) and confined to `tests/generated/`.
- **Secrets** never logged or committed (`SecretStr` + redaction filter + gitleaks).
  GitHub auth is a **fine-grained PAT** scoped to one repo (`Contents`,
  `Pull requests`: write).
- **`--allowedTools` belongs to the FUTURE execution sandbox only**
  (`config/allowed_tools.yaml`, `ExecutionContext.allowed_tools`). The execution
  phase will run `claude -p` as a subprocess in a **separate hardened container**.

## Testing

The tool's own tests use `FakeStructuredLLM`/`FakePrPublisher` (`tests/_fakes.py`)
and `httpx.MockTransport` — **no network, no secrets**. `tests/generated/` is
excluded from collection. CI runs `ruff` + `mypy --strict` + `pytest`.

## CI/CD & deploy

`ci.yml` gates merges (fully mocked). `deploy.yml` cross-builds the arm64 image
(buildx → GHCR) and SSH-deploys to the Pi from `main` behind a protected
Environment. `generated-tests.yml` is the template that runs generated tests in
GitHub's sandbox (belongs in the target repo).

## Docker / Raspberry Pi runtime

Multi-stage `python:3.12-slim` (pin by digest in prod), non-root user,
`read_only` rootfs + tmpfs, `cap_drop: [ALL]`, `no-new-privileges`, HEALTHCHECK on
`/health`. Secrets via `env_file` (root:0600), never baked into image layers.
