from __future__ import annotations

from qaia.domain.models import (
    GenerationOptions,
    LlmTestArtifacts,
    SourceKind,
    SpecInput,
    TestKind,
)
from qaia.generation.generator import PytestHttpxGenerator
from tests._fakes import FakeStructuredLLM


def test_generator_stamps_provenance(sample_artifacts: LlmTestArtifacts) -> None:
    fake = FakeStructuredLLM(sample_artifacts)
    spec = SpecInput(
        feature_name="Login",
        raw_text="Feature: Login\n",
        source_kind=SourceKind.GHERKIN_FEATURE,
    )

    suite = PytestHttpxGenerator(fake).generate(
        spec, GenerationOptions(model="claude-sonnet-4-6", max_tokens=16000)
    )

    assert suite.test_kind is TestKind.API_PYTEST_HTTPX
    assert suite.feature_name == "Login"
    assert [f.filename for f in suite.files] == [f.filename for f in sample_artifacts.files]
    # The SDK is hidden behind the StructuredLLM port — no network was touched.
    assert fake.calls[0]["model"] == "claude-sonnet-4-6"
