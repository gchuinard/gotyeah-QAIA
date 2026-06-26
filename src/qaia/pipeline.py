"""Composition root: load -> generate -> write -> (future heal) -> publish.

Pure orchestration over the ports; adapters are injected. The optional executor
param is the pre-wired extension point — when present (later), run() will call
``executor.run_and_heal`` between write and publish without touching generation.
"""

from __future__ import annotations

from pathlib import Path

from qaia.domain.models import (
    GeneratedTestSuite,
    GenerationOptions,
    PublishResult,
    PublishTarget,
)
from qaia.ports import Executor, PrPublisher, SpecLoader, TestGenerator, TestWriter


class GenerationPipeline:
    def __init__(
        self,
        loader: SpecLoader,
        generator: TestGenerator,
        writer: TestWriter,
        publisher: PrPublisher | None = None,
        executor: Executor | None = None,
    ) -> None:
        self._loader = loader
        self._generator = generator
        self._writer = writer
        self._publisher = publisher
        self._executor = executor  # FUTURE: run-and-heal stage; unused in the MVP.

    def generate_and_write(
        self, ref: Path, options: GenerationOptions, dest: Path
    ) -> tuple[GeneratedTestSuite, list[Path]]:
        spec = self._loader.load(ref)
        suite = self._generator.generate(spec, options)
        paths = self._writer.write(suite, dest)
        return suite, paths

    def run(
        self,
        ref: Path,
        options: GenerationOptions,
        target: PublishTarget,
        dest: Path,
    ) -> PublishResult:
        if self._publisher is None:
            raise RuntimeError("a PrPublisher is required to open a PR")
        suite, _ = self.generate_and_write(ref, options, dest)
        return self._publisher.publish(suite, target)
