"""Loads a Gherkin .feature file into a normalized ``SpecInput``.

Light in-house validation only — no heavy Gherkin parser dependency. The model
parses Gherkin natively; we just confirm it is a feature and extract a stable
name for deterministic file/branch/PR naming. Swappable for a parser-backed
loader later without touching anything downstream.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

from qaia.domain.errors import InvalidFeatureError
from qaia.domain.models import SourceKind, SpecInput

_FEATURE_RE = re.compile(r"^\s*Feature:\s*(?P<name>.+?)\s*$", re.MULTILINE)


class FeatureFileSpecLoader:
    source_kind: ClassVar[SourceKind] = SourceKind.GHERKIN_FEATURE

    def load(self, ref: Path) -> SpecInput:
        try:
            text = ref.read_text(encoding="utf-8")
        except OSError as exc:
            raise InvalidFeatureError(f"cannot read feature file: {ref}") from exc

        match = _FEATURE_RE.search(text)
        if match is None:
            raise InvalidFeatureError(f"no 'Feature:' line found in {ref}")

        name = match.group("name").strip()
        if not name:
            raise InvalidFeatureError(f"empty feature name in {ref}")

        return SpecInput(feature_name=name, raw_text=text, source_kind=self.source_kind)
