from __future__ import annotations

import json

import httpx
from pydantic import SecretStr

from qaia.domain.models import GeneratedFile, GeneratedTestSuite, PublishTarget, TestKind
from qaia.github.pr import GitHubPrPublisher


def _suite() -> GeneratedTestSuite:
    return GeneratedTestSuite(
        test_kind=TestKind.API_PYTEST_HTTPX,
        feature_name="User Login",
        files=[
            GeneratedFile(
                filename="test_login.py",
                content="def test_login() -> None:\n    assert True\n",
                description="login",
            )
        ],
        requirements=["pytest", "httpx"],
        notes=None,
    )


def test_publish_runs_full_git_data_sequence() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        calls.append((method, path))

        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "basecommitsha"}})
        if method == "GET" and path.endswith("/git/commits/basecommitsha"):
            return httpx.Response(200, json={"tree": {"sha": "basetreesha"}})
        if method == "POST" and path.endswith("/git/blobs"):
            return httpx.Response(201, json={"sha": "blobsha"})
        if method == "POST" and path.endswith("/git/trees"):
            body = json.loads(request.content)
            assert body["base_tree"] == "basetreesha"
            assert body["tree"][0]["path"] == "tests/generated/test_login.py"
            return httpx.Response(201, json={"sha": "newtreesha"})
        if method == "POST" and path.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "newcommitsha"})
        if method == "POST" and path.endswith("/git/refs"):
            body = json.loads(request.content)
            assert body["ref"] != "refs/heads/main"  # never the default branch
            return httpx.Response(201, json={"ref": body["ref"]})
        if method == "POST" and path.endswith("/pulls"):
            body = json.loads(request.content)
            assert body["base"] == "main"
            assert body["head"].startswith("qaia/user-login-")
            return httpx.Response(
                201, json={"html_url": "https://github.com/o/r/pull/7", "number": 7}
            )
        if method == "POST" and path.endswith("/labels"):
            return httpx.Response(200, json=[])  # GitHub returns an array here

        raise AssertionError(f"unexpected call: {method} {path}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    publisher = GitHubPrPublisher(SecretStr("ghp_test"), client=client)
    target = PublishTarget(
        repo="o/r",
        base_branch="main",
        branch_prefix="qaia",
        path_prefix="tests/generated",
        labels=["qaia:generated"],
        model="claude-sonnet-4-6",
    )

    result = publisher.publish(_suite(), target)

    assert result.pr_url == "https://github.com/o/r/pull/7"
    assert result.commit_sha == "newcommitsha"
    assert result.branch.startswith("qaia/user-login-")
    assert [m for m, _ in calls].count("GET") == 2
    assert ("POST", "/repos/o/r/pulls") in calls
    assert ("POST", "/repos/o/r/issues/7/labels") in calls


def test_label_failure_is_best_effort() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "b"}})
        if method == "GET" and path.endswith("/git/commits/b"):
            return httpx.Response(200, json={"tree": {"sha": "t"}})
        if method == "POST" and path.endswith("/git/blobs"):
            return httpx.Response(201, json={"sha": "bl"})
        if method == "POST" and path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "nt"})
        if method == "POST" and path.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "nc"})
        if method == "POST" and path.endswith("/git/refs"):
            return httpx.Response(201, json={})
        if method == "POST" and path.endswith("/pulls"):
            return httpx.Response(
                201, json={"html_url": "https://github.com/o/r/pull/9", "number": 9}
            )
        if method == "POST" and path.endswith("/labels"):
            return httpx.Response(403, json={"message": "Resource not accessible by token"})
        raise AssertionError(f"unexpected call: {method} {path}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    publisher = GitHubPrPublisher(SecretStr("ghp_test"), client=client)
    target = PublishTarget(repo="o/r", base_branch="main", labels=["qaia:generated"])

    # A 403 on labels must NOT discard the already-created PR.
    result = publisher.publish(_suite(), target)
    assert result.pr_url == "https://github.com/o/r/pull/9"
    assert result.commit_sha == "nc"
