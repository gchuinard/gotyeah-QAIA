"""Minimal FastAPI app satisfying the mandated stack.

MVP exposes /health and /version ONLY — deliberately no unauthenticated generate
endpoint on a host holding spend-capable + repo-write credentials. A future
authenticated trigger endpoint would bind behind the reserved auth dependency in
``deps.py``.
"""

from __future__ import annotations

from fastapi import FastAPI

from qaia import __version__

app = FastAPI(title="QAIA", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"name": "qaia", "version": __version__}
