"""``qaia generate <feature>`` — the MVP operational entrypoint.

A run-and-exit batch job (no listening socket) is the smallest attack surface for
a process holding spend-capable + repo-write credentials. Builds settings, wires
the adapters, runs the pipeline, prints the PR URL.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from pydantic import ValidationError

from qaia.domain.errors import QaiaError
from qaia.domain.models import GenerationOptions, PublishTarget
from qaia.generation.client import AnthropicStructuredLLM
from qaia.generation.generator import PytestHttpxGenerator
from qaia.github.pr import GitHubPrPublisher
from qaia.logging import configure_logging
from qaia.pipeline import GenerationPipeline
from qaia.settings import Settings
from qaia.specs.feature_loader import FeatureFileSpecLoader
from qaia.writer.file_writer import LocalFsTestWriter

app = typer.Typer(help="QAIA — generate pytest+httpx tests from a Gherkin feature and open a PR.")


@app.callback()
def _root() -> None:
    """QAIA — spec to tests to PR. Keeps `generate` as a named subcommand."""


@app.command()
def generate(
    feature: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to a .feature file."
    ),
    repo: str | None = typer.Option(None, "--repo", help='Target "owner/repo".'),
    base_branch: str | None = typer.Option(None, "--base-branch", help="PR base branch."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Generate and write locally; do not open a PR."
    ),
) -> None:
    configure_logging()
    log = logging.getLogger("qaia.cli")

    try:
        settings = Settings()  # fail-fast on missing ANTHROPIC_API_KEY / GITHUB_TOKEN
    except ValidationError as exc:
        typer.echo(
            "Configuration error — set ANTHROPIC_API_KEY and GITHUB_TOKEN (see .env.example).",
            err=True,
        )
        raise typer.Exit(2) from exc

    options = GenerationOptions(model=settings.generation_model, max_tokens=settings.max_tokens)
    dest = settings.generated_tests_dir

    loader = FeatureFileSpecLoader()
    generator = PytestHttpxGenerator(AnthropicStructuredLLM(api_key=settings.anthropic_api_key))
    writer = LocalFsTestWriter()

    try:
        if dry_run:
            pipeline = GenerationPipeline(loader, generator, writer)
            suite, paths = pipeline.generate_and_write(feature, options, dest)
            typer.echo(
                f"Generated {len(suite.files)} test file(s) for '{suite.feature_name}' (dry-run)."
            )
            for path in paths:
                typer.echo(f"  - {path}")
            return

        target_repo = repo or settings.github_repo
        if not target_repo:
            typer.echo("No target repo. Set GITHUB_REPO or pass --repo owner/repo.", err=True)
            raise typer.Exit(2)

        publisher = GitHubPrPublisher(settings.github_token)
        pipeline = GenerationPipeline(loader, generator, writer, publisher)
        target = PublishTarget(
            repo=target_repo,
            base_branch=base_branch or settings.default_base_branch,
            branch_prefix=settings.branch_prefix,
            path_prefix=settings.repo_tests_path,
            labels=["qaia:generated"],
            model=settings.generation_model,
        )
        result = pipeline.run(feature, options, target, dest)
        log.info("opened PR %s (branch %s)", result.pr_url, result.branch)
        typer.echo(f"Opened PR: {result.pr_url}")
    except QaiaError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
