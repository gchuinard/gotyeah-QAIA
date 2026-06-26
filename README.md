# QAIA

Generate automated tests from specs and open a PR. **MVP slice:** a Gherkin
`.feature` → pytest + httpx tests (via the Anthropic API, structured output) →
written to `tests/generated/` → a GitHub PR.

See `PLAN.md` for the design and `CLAUDE.md` for conventions and security rules.

## Requirements

- Python 3.12, [`uv`](https://docs.astral.sh/uv/)
- `ANTHROPIC_API_KEY`, `GITHUB_TOKEN` (fine-grained PAT: Contents + Pull requests
  write), and `GITHUB_REPO` (`owner/repo`) — see `.env.example`.

## Quickstart

```bash
uv sync
cp .env.example .env   # then fill in the values

# Generate locally without opening a PR:
uv run qaia generate examples/sample.feature --dry-run

# Generate and open a PR on $GITHUB_REPO:
uv run qaia generate examples/sample.feature
```

## Develop

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

## Run the API

```bash
uv run uvicorn qaia.api.app:app --reload   # /health, /version
```

## What is NOT here yet

E2E (Playwright), agentic execution + self-healing (`claude -p` in a sandbox),
and ticket sources (Jira/Linear via MCP) are **reserved seams**, not implemented.
The generation phase has no shell/tool access by design; `--allowedTools` belongs
to the future execution sandbox only.
