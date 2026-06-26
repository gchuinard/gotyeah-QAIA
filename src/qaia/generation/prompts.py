"""Versioned, reviewable prompt builders for the generation module.

No tool/shell instructions ever appear here: generation is a pure text->data
transform. The prompts pin a fixed convention (the ``base_url`` fixture) so the
output is deterministic and never hardcodes a host.
"""

from __future__ import annotations

from qaia.domain.models import SpecInput

PROMPT_VERSION = "1"

SYSTEM_PROMPT = """You are a senior QA automation engineer. From a Gherkin feature, \
produce runnable API tests in Python using pytest and httpx.

Rules:
- Emit one pytest test function per Gherkin scenario; name each test_<snake_case_scenario>.
- NEVER hardcode a host or base URL. Use the pytest fixtures `base_url` (str) and \
`client` (httpx.Client) provided by the conftest you also emit.
- Emit a `conftest.py` that defines:
    * a session-scoped `base_url` fixture reading os.environ["BASE_URL"] and raising a \
clear error if it is unset;
    * a `client` fixture that yields httpx.Client(base_url=base_url) and closes it.
- Assert the HTTP status code and the relevant response body fields for each scenario.
- Use only the Python standard library, pytest, and httpx. Do no network I/O at import time.
- Test file names MUST match ^test_[a-z0-9_]+\\.py$. The conftest MUST be named exactly \
conftest.py.

Return the structured artifacts: the list of files (filename, content, description), the \
pip requirements (e.g. pytest, httpx), and optional notes for the reviewer.
"""


def build_user_prompt(spec: SpecInput, extra: str | None = None) -> str:
    parts = [
        f"Feature name: {spec.feature_name}",
        "",
        "Gherkin .feature content:",
        "```gherkin",
        spec.raw_text.strip(),
        "```",
    ]
    if extra:
        parts += ["", "Additional instructions:", extra]
    return "\n".join(parts)
