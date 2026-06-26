"""Domain models — the stable contract that flows across every seam.

Two layers are deliberately split:
  * ``LlmTestArtifacts`` — the flat schema the LLM fills via structured output.
  * ``GeneratedTestSuite`` — the provenance-stamped domain object the rest of the
    system speaks. Generation owns the stamp (``test_kind``, ``feature_name``);
    the LLM never does.

``SourceKind`` / ``TestKind`` enums keep future inputs (Jira/Linear) and future
generators (Playwright E2E) additive rather than rewrites.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    """Where a spec came from."""

    GHERKIN_FEATURE = "gherkin_feature"
    # FUTURE: JIRA = "jira"; LINEAR = "linear"


class TestKind(StrEnum):
    """What kind of tests a generator produces."""

    API_PYTEST_HTTPX = "api_pytest_httpx"
    # FUTURE: E2E_PLAYWRIGHT = "e2e_playwright"


class SpecInput(BaseModel):
    """A normalized spec, regardless of origin."""

    feature_name: str
    raw_text: str
    source_kind: SourceKind


class GeneratedFile(BaseModel):
    """One file the generator produced."""

    filename: str
    content: str
    description: str


class LlmTestArtifacts(BaseModel):
    """Structured-output schema the LLM fills.

    Kept flat and fully-required (``notes`` nullable) so it maps cleanly to a
    strict json_schema. The LLM owns test content only — not provenance.
    """

    files: list[GeneratedFile]
    requirements: list[str]
    notes: str | None


class GeneratedTestSuite(BaseModel):
    """Provenance-stamped domain object — the seam both modules speak."""

    test_kind: TestKind
    feature_name: str
    files: list[GeneratedFile]
    requirements: list[str] = Field(default_factory=list)
    notes: str | None = None

    @classmethod
    def from_artifacts(
        cls,
        artifacts: LlmTestArtifacts,
        *,
        test_kind: TestKind,
        feature_name: str,
    ) -> GeneratedTestSuite:
        return cls(
            test_kind=test_kind,
            feature_name=feature_name,
            files=artifacts.files,
            requirements=artifacts.requirements,
            notes=artifacts.notes,
        )


class GenerationOptions(BaseModel):
    """Knobs for a single generation call."""

    model: str
    max_tokens: int
    extra_instructions: str | None = None


class PublishTarget(BaseModel):
    """Routing for a PR. Title/body are derived from the suite by the publisher."""

    repo: str  # "owner/repo"
    base_branch: str = "main"
    branch_prefix: str = "qaia"
    path_prefix: str = "tests/generated"
    labels: list[str] = Field(default_factory=list)
    model: str = ""  # provenance only — included in the PR body when set


class PublishResult(BaseModel):
    """Outcome of opening a PR."""

    pr_url: str
    branch: str
    commit_sha: str


# --- FUTURE (execution + self-healing) — reserved, unimplemented in the MVP ---


class ExecutionContext(BaseModel):
    """Sandbox contract for the future agentic executor.

    ``allowed_tools`` encodes the ``claude -p --allowedTools`` whitelist before
    any execution code exists. Lives here so the seam is type-stable today.
    """

    workspace: Path
    allowed_tools: list[str]
    max_iterations: int = 3
    timeout_seconds: int = 600


class ExecutionReport(BaseModel):
    """Outcome of a future run-and-heal pass."""

    passed: bool
    iterations: int
    patched_files: list[str]
    log: str
