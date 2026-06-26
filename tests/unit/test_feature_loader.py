from __future__ import annotations

from pathlib import Path

import pytest

from qaia.domain.errors import InvalidFeatureError
from qaia.domain.models import SourceKind
from qaia.specs.feature_loader import FeatureFileSpecLoader


def test_loads_feature(tmp_path: Path) -> None:
    path = tmp_path / "login.feature"
    path.write_text("Feature: User login\n  Scenario: ok\n", encoding="utf-8")

    spec = FeatureFileSpecLoader().load(path)

    assert spec.feature_name == "User login"
    assert spec.source_kind is SourceKind.GHERKIN_FEATURE
    assert "Scenario" in spec.raw_text


def test_rejects_missing_feature_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.feature"
    path.write_text("no feature keyword here\n", encoding="utf-8")

    with pytest.raises(InvalidFeatureError):
        FeatureFileSpecLoader().load(path)


def test_rejects_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(InvalidFeatureError):
        FeatureFileSpecLoader().load(tmp_path / "does_not_exist.feature")
