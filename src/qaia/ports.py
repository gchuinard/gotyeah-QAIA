"""Ports — the interchangeable seams as ``Protocol``s only (zero implementation).

Adapters and the pipeline depend on these protocols, never on each other. This
is what keeps GENERATION (deterministic) and the future EXECUTION+self-healing
(agentic) decoupled: both speak only the shared domain types.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, TypeVar

from pydantic import BaseModel

from qaia.domain.models import (
    ExecutionContext,
    ExecutionReport,
    GeneratedTestSuite,
    GenerationOptions,
    PublishResult,
    PublishTarget,
    SourceKind,
    SpecInput,
    TestKind,
)

T = TypeVar("T", bound=BaseModel)


class SpecLoader(Protocol):
    """Normalizes any input into a ``SpecInput``."""

    source_kind: ClassVar[SourceKind]

    def load(self, ref: Path) -> SpecInput: ...


class StructuredLLM(Protocol):
    """Isolates the LLM SDK shape so generators are testable without a network."""

    def parse(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, object]],
        output_format: type[T],
    ) -> T: ...


class TestGenerator(Protocol):
    """The deterministic GENERATION boundary."""

    test_kind: ClassVar[TestKind]

    def generate(self, spec: SpecInput, options: GenerationOptions) -> GeneratedTestSuite: ...


class TestWriter(Protocol):
    """Confines untrusted LLM output to a single directory (egress boundary)."""

    def write(self, suite: GeneratedTestSuite, dest: Path) -> list[Path]: ...


class PrPublisher(Protocol):
    """Opens a GitHub PR from the in-memory suite. Never merges, never pushes default."""

    def publish(self, suite: GeneratedTestSuite, target: PublishTarget) -> PublishResult: ...


class Executor(Protocol):
    """FUTURE agentic run-and-heal seam. Reserved; unimplemented in the MVP.

    Consumes/returns the SAME ``GeneratedTestSuite`` type so GENERATION and
    EXECUTION never import each other. ``ctx`` already carries the explicit
    ``allowed_tools`` whitelist — the sandbox contract, encoded up front.
    """

    def run_and_heal(self, suite: GeneratedTestSuite, ctx: ExecutionContext) -> ExecutionReport: ...
