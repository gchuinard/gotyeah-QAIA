from __future__ import annotations

from pathlib import Path

import pytest

from qaia.domain.errors import UnsafePathError
from qaia.domain.models import GeneratedFile, GeneratedTestSuite, TestKind
from qaia.writer.file_writer import LocalFsTestWriter


def _suite(files: list[GeneratedFile]) -> GeneratedTestSuite:
    return GeneratedTestSuite(
        test_kind=TestKind.API_PYTEST_HTTPX,
        feature_name="F",
        files=files,
        requirements=["pytest"],
        notes=None,
    )


def test_writes_valid_files(tmp_path: Path) -> None:
    dest = tmp_path / "generated"
    suite = _suite(
        [
            GeneratedFile(filename="test_x.py", content="x = 1\n", description="d"),
            GeneratedFile(filename="conftest.py", content="y = 2\n", description="d"),
        ]
    )

    paths = LocalFsTestWriter().write(suite, dest)

    assert sorted(p.name for p in paths) == [
        "conftest.py",
        "generation_manifest.json",
        "test_x.py",
    ]
    for path in paths:
        assert path.parent == dest.resolve()
    assert (dest / "test_x.py").read_text(encoding="utf-8") == "x = 1\n"


@pytest.mark.parametrize(
    "bad",
    [
        "../evil.py",
        "/etc/passwd.py",
        "a/b.py",
        "evil.txt",
        "Test_X.py",
        "test_x.py.bak",
        "test_.py",
        "test_evil.py\n",  # trailing newline must not slip past the allowlist
        "conftest.py\n",
    ],
)
def test_rejects_unsafe_filenames(tmp_path: Path, bad: str) -> None:
    suite = _suite([GeneratedFile(filename=bad, content="x = 1\n", description="d")])

    with pytest.raises(UnsafePathError):
        LocalFsTestWriter().write(suite, tmp_path / "generated")
