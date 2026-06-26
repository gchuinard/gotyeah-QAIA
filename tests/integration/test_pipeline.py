from __future__ import annotations

from pathlib import Path

from qaia.domain.models import GenerationOptions, LlmTestArtifacts, PublishTarget
from qaia.generation.generator import PytestHttpxGenerator
from qaia.pipeline import GenerationPipeline
from qaia.specs.feature_loader import FeatureFileSpecLoader
from qaia.writer.file_writer import LocalFsTestWriter
from tests._fakes import FakePrPublisher, FakeStructuredLLM


def test_pipeline_end_to_end(
    tmp_path: Path,
    sample_artifacts: LlmTestArtifacts,
    sample_feature_path: Path,
) -> None:
    publisher = FakePrPublisher()
    pipeline = GenerationPipeline(
        loader=FeatureFileSpecLoader(),
        generator=PytestHttpxGenerator(FakeStructuredLLM(sample_artifacts)),
        writer=LocalFsTestWriter(),
        publisher=publisher,
    )
    dest = tmp_path / "generated"

    result = pipeline.run(
        sample_feature_path,
        GenerationOptions(model="claude-sonnet-4-6", max_tokens=16000),
        PublishTarget(repo="o/r", base_branch="main", path_prefix="tests/generated"),
        dest,
    )

    assert result.pr_url == "https://example.test/pull/1"
    assert (dest / "test_health.py").exists()
    assert (dest / "conftest.py").exists()
    assert (dest / "generation_manifest.json").exists()
    assert publisher.published[0][1].repo == "o/r"
