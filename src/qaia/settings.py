"""Typed, env-only configuration.

Secrets are held as ``SecretStr`` so they are never rendered by ``repr``/``str``/
JSON. The Anthropic SDK reads ``ANTHROPIC_API_KEY`` itself; we only assert its
presence (fail-fast) so a missing key surfaces at startup, not mid-call.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required secrets (env: ANTHROPIC_API_KEY, GITHUB_TOKEN).
    anthropic_api_key: SecretStr
    github_token: SecretStr

    # Target repo "owner/repo". Empty until the user sets GITHUB_REPO; the CLI
    # fails clearly if a real (non dry-run) publish is attempted without it.
    github_repo: str = ""

    default_base_branch: str = "main"
    generation_model: str = "claude-sonnet-4-6"
    max_tokens: int = 16000
    # Local dir the tool writes to (may be absolute / OS-native).
    generated_tests_dir: Path = Path("tests/generated")
    # Repo-relative POSIX path the PR commits to (distinct from the local dir).
    repo_tests_path: str = "tests/generated"
    branch_prefix: str = "qaia"

    # Env var the GENERATED tests read for the system-under-test base URL.
    sut_base_url_env: str = "BASE_URL"
