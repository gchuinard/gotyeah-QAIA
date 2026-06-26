"""Pytest + httpx test generator (the MVP ``TestGenerator``).

Calls the injected ``StructuredLLM``, receives ``LlmTestArtifacts``, and stamps
provenance the LLM should not own. Imports only the LLM port, prompts, and domain
models — never the SDK, never another adapter.
"""

from __future__ import annotations

from typing import ClassVar

from qaia.domain.models import (
    GeneratedTestSuite,
    GenerationOptions,
    LlmTestArtifacts,
    SpecInput,
    TestKind,
)
from qaia.generation.prompts import SYSTEM_PROMPT, build_user_prompt
from qaia.ports import StructuredLLM


class PytestHttpxGenerator:
    test_kind: ClassVar[TestKind] = TestKind.API_PYTEST_HTTPX

    def __init__(self, llm: StructuredLLM) -> None:
        self._llm = llm

    def generate(self, spec: SpecInput, options: GenerationOptions) -> GeneratedTestSuite:
        user_prompt = build_user_prompt(spec, options.extra_instructions)
        messages: list[dict[str, object]] = [{"role": "user", "content": user_prompt}]
        artifacts = self._llm.parse(
            model=options.model,
            max_tokens=options.max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_format=LlmTestArtifacts,
        )
        return GeneratedTestSuite.from_artifacts(
            artifacts,
            test_kind=self.test_kind,
            feature_name=spec.feature_name,
        )
