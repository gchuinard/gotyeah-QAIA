from __future__ import annotations

import pytest

from qaia.settings import Settings

# Deliberately NOT secret-shaped (no sk-ant- / ghp_ prefixes) so public-repo
# secret scanning doesn't flag these test placeholders.
_FAKE_ANTHROPIC = "anthropic-key-placeholder-not-real"
_FAKE_GITHUB = "github-token-placeholder-not-real"


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_ANTHROPIC)
    monkeypatch.setenv("GITHUB_TOKEN", _FAKE_GITHUB)
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")

    settings = Settings()

    assert settings.github_repo == "owner/repo"
    assert settings.generation_model == "claude-sonnet-4-6"
    assert settings.anthropic_api_key.get_secret_value() == _FAKE_ANTHROPIC


def test_secrets_never_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", _FAKE_ANTHROPIC)
    monkeypatch.setenv("GITHUB_TOKEN", _FAKE_GITHUB)

    settings = Settings()

    text = f"{settings!r} {settings.anthropic_api_key} {settings.github_token}"
    assert _FAKE_ANTHROPIC not in text
    assert _FAKE_GITHUB not in text
