"""Writes generated test files to disk — the egress trust boundary.

Every model-supplied filename is validated (no separators, no ``..``, no absolute
paths) and the resolved path is confirmed to stay inside the destination dir.
Content is written as inert UTF-8; it is NEVER imported or executed here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from qaia.domain.errors import UnsafePathError
from qaia.domain.models import GeneratedTestSuite

# Allowed: pytest test modules (test_*.py) and the conftest the generator emits.
# Matched with re.fullmatch — `$` would also accept a trailing newline.
_ALLOWED_FILENAME = re.compile(r"(test_[a-z0-9_]+|conftest)\.py")
_MANIFEST_NAME = "generation_manifest.json"


class LocalFsTestWriter:
    def write(self, suite: GeneratedTestSuite, dest: Path) -> list[Path]:
        dest_root = dest.resolve()
        dest_root.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for generated in suite.files:
            target = self._resolve_llm_file(generated.filename, dest_root)
            target.write_text(generated.content, encoding="utf-8")
            written.append(target)

        manifest_path = dest_root / _MANIFEST_NAME
        manifest_path.write_text(self._manifest_json(suite, written), encoding="utf-8")
        written.append(manifest_path)
        return written

    @staticmethod
    def _resolve_llm_file(filename: str, dest_root: Path) -> Path:
        if not _ALLOWED_FILENAME.fullmatch(filename):
            raise UnsafePathError(f"rejected unsafe test filename: {filename!r}")
        # Belt-and-suspenders even though the regex already forbids separators/'..'.
        candidate = (dest_root / filename).resolve()
        if candidate.parent != dest_root:
            raise UnsafePathError(f"path escapes generated dir: {filename!r}")
        return candidate

    @staticmethod
    def _manifest_json(suite: GeneratedTestSuite, written: list[Path]) -> str:
        payload = {
            "feature_name": suite.feature_name,
            "test_kind": suite.test_kind.value,
            "files": sorted(p.name for p in written),
            "requirements": suite.requirements,
            "notes": suite.notes,
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
