"""Opens a GitHub PR via the REST Git Data API over httpx.

Chosen over the ``gh`` CLI (no subprocess — preserves the generation no-shell
boundary) and PyGithub (heavier, weaker typing). Uses the Git Data API so no
local checkout is needed, which suits a minimal arm64 container.

Hard rules: never target/push the default branch directly, never auto-merge —
the PR is the human review gate.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

import httpx
from pydantic import SecretStr

from qaia.domain.errors import PublishError
from qaia.domain.models import GeneratedFile, GeneratedTestSuite, PublishResult, PublishTarget

_API_BASE = "https://api.github.com"
_BLOB_MODE = "100644"
_log = logging.getLogger("qaia.github")


class GitHubPrPublisher:
    def __init__(
        self,
        token: SecretStr,
        *,
        client: httpx.Client | None = None,
        api_base: str = _API_BASE,
    ) -> None:
        self._token = token
        self._api_base = api_base.rstrip("/")
        self._client = client if client is not None else httpx.Client(timeout=30.0)

    def publish(self, suite: GeneratedTestSuite, target: PublishTarget) -> PublishResult:
        branch = f"{target.branch_prefix}/{_slug(suite.feature_name)}-{uuid.uuid4().hex[:8]}"
        if branch == target.base_branch:
            raise PublishError("refusing to publish onto the base branch")

        repo = target.repo
        base_sha = self._base_ref_sha(repo, target.base_branch)
        base_tree_sha = self._commit_tree_sha(repo, base_sha)

        # Repo-relative POSIX prefix: GitHub tree paths use '/' and no leading slash.
        repo_prefix = target.path_prefix.replace("\\", "/").strip("/")
        tree = [
            {
                "path": f"{repo_prefix}/{f.filename}" if repo_prefix else f.filename,
                "mode": _BLOB_MODE,
                "type": "blob",
                "sha": self._create_blob(repo, f.content),
            }
            for f in suite.files
        ]
        new_tree_sha = self._create_tree(repo, base_tree_sha, tree)
        commit_sha = self._create_commit(
            repo,
            message=f"[QAIA] generated API tests for {suite.feature_name}",
            tree_sha=new_tree_sha,
            parent_sha=base_sha,
        )
        self._create_branch(repo, branch, commit_sha)
        pr_url, number = self._open_pr(repo, target, branch, suite)
        result = PublishResult(pr_url=pr_url, branch=branch, commit_sha=commit_sha)

        # Best-effort: the PR already exists; a label failure (e.g. the PAT lacks
        # Issues scope) must not discard the result or cause a duplicate PR on retry.
        if target.labels:
            try:
                self._add_labels(repo, number, target.labels)
            except PublishError as exc:
                _log.warning("could not add labels to PR #%s: %s", number, exc)

        return result

    # --- HTTP helpers ---------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token.get_secret_value()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _send(
        self, method: str, url: str, *, json_body: dict[str, Any] | None = None
    ) -> httpx.Response:
        try:
            response = self._client.request(method, url, headers=self._headers(), json=json_body)
        except httpx.HTTPError as exc:
            raise PublishError(f"GitHub request failed: {method} {url}: {exc}") from exc
        if response.status_code >= 300:
            raise PublishError(
                f"GitHub API {method} {url} -> {response.status_code}: {response.text}"
            )
        return response

    def _request(
        self, method: str, url: str, *, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data: Any = self._send(method, url, json_body=json_body).json()
        if not isinstance(data, dict):
            raise PublishError(f"unexpected GitHub response shape for {url}")
        return data

    # --- Git Data API steps ---------------------------------------------------

    def _base_ref_sha(self, repo: str, base_branch: str) -> str:
        data = self._request("GET", f"{self._api_base}/repos/{repo}/git/ref/heads/{base_branch}")
        return str(data["object"]["sha"])

    def _commit_tree_sha(self, repo: str, commit_sha: str) -> str:
        data = self._request("GET", f"{self._api_base}/repos/{repo}/git/commits/{commit_sha}")
        return str(data["tree"]["sha"])

    def _create_blob(self, repo: str, content: str) -> str:
        data = self._request(
            "POST",
            f"{self._api_base}/repos/{repo}/git/blobs",
            json_body={"content": content, "encoding": "utf-8"},
        )
        return str(data["sha"])

    def _create_tree(self, repo: str, base_tree_sha: str, tree: list[dict[str, Any]]) -> str:
        data = self._request(
            "POST",
            f"{self._api_base}/repos/{repo}/git/trees",
            json_body={"base_tree": base_tree_sha, "tree": tree},
        )
        return str(data["sha"])

    def _create_commit(self, repo: str, *, message: str, tree_sha: str, parent_sha: str) -> str:
        data = self._request(
            "POST",
            f"{self._api_base}/repos/{repo}/git/commits",
            json_body={"message": message, "tree": tree_sha, "parents": [parent_sha]},
        )
        return str(data["sha"])

    def _create_branch(self, repo: str, branch: str, commit_sha: str) -> None:
        self._request(
            "POST",
            f"{self._api_base}/repos/{repo}/git/refs",
            json_body={"ref": f"refs/heads/{branch}", "sha": commit_sha},
        )

    def _open_pr(
        self, repo: str, target: PublishTarget, branch: str, suite: GeneratedTestSuite
    ) -> tuple[str, int]:
        data = self._request(
            "POST",
            f"{self._api_base}/repos/{repo}/pulls",
            json_body={
                "title": f"[QAIA] Generated API tests for {suite.feature_name}",
                "head": branch,
                "base": target.base_branch,
                "body": _pr_body(suite, target),
            },
        )
        return str(data["html_url"]), int(data["number"])

    def _add_labels(self, repo: str, number: int, labels: list[str]) -> None:
        # GitHub returns a JSON array here; we don't need the body, only success.
        self._send(
            "POST",
            f"{self._api_base}/repos/{repo}/issues/{number}/labels",
            json_body={"labels": labels},
        )


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "feature"


def _pr_body(suite: GeneratedTestSuite, target: PublishTarget) -> str:
    lines = [
        f"Auto-generated by QAIA from feature **{suite.feature_name}**.",
        "",
        f"- Test kind: `{suite.test_kind.value}`",
        f"- Files: {len(suite.files)}",
    ]
    if target.model:
        lines.append(f"- Model: `{target.model}`")
    lines += ["", "### Files", *(_file_line(f) for f in suite.files)]
    if suite.requirements:
        reqs = ", ".join(f"`{r}`" for r in suite.requirements)
        lines += ["", "### Requirements", reqs]
    if suite.notes:
        lines += ["", "### Notes", suite.notes]
    lines += ["", "_Review before merging. QAIA never auto-merges._"]
    return "\n".join(lines)


def _file_line(f: GeneratedFile) -> str:
    return f"- `{f.filename}` — {f.description}"
