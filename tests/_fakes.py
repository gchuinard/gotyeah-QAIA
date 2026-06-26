"""Test doubles for the ports — no network, no SDK, no real GitHub."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from qaia.domain.models import (
    GeneratedTestSuite,
    LlmTestArtifacts,
    PublishResult,
    PublishTarget,
)

_T = TypeVar("_T", bound=BaseModel)


class FakeStructuredLLM:
    """Implements the StructuredLLM port; returns canned artifacts, records calls."""

    def __init__(self, artifacts: LlmTestArtifacts) -> None:
        self._artifacts = artifacts
        self.calls: list[dict[str, object]] = []

    def parse(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, object]],
        output_format: type[_T],
    ) -> _T:
        self.calls.append(
            {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
        )
        return output_format.model_validate(self._artifacts.model_dump())


class FakePrPublisher:
    """Implements the PrPublisher port; records publishes, returns a canned result."""

    def __init__(self) -> None:
        self.published: list[tuple[GeneratedTestSuite, PublishTarget]] = []

    def publish(self, suite: GeneratedTestSuite, target: PublishTarget) -> PublishResult:
        self.published.append((suite, target))
        return PublishResult(
            pr_url="https://example.test/pull/1",
            branch=f"{target.branch_prefix}/demo",
            commit_sha="deadbeefcafe",
        )
