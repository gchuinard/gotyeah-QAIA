"""The single file that touches the Anthropic SDK.

PURE generation: one structured call, no shell/subprocess/filesystem/MCP. The SDK
client is treated as opaque (typed ``Any``) so this adapter is robust across SDK
versions; the type-safety we keep is the validated Pydantic result, narrowed via
``isinstance`` against the caller's ``output_format``.
"""

from __future__ import annotations

from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, SecretStr, ValidationError

from qaia.domain.errors import GenerationError

T = TypeVar("T", bound=BaseModel)


class AnthropicStructuredLLM:
    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        *,
        api_key: SecretStr | None = None,
    ) -> None:
        # Pass the key explicitly (it lives in Settings, possibly loaded from .env
        # which the SDK can't see). Falls back to the SDK's own env lookup.
        if client is not None:
            self._client: Any = client
        elif api_key is not None:
            self._client = anthropic.Anthropic(api_key=api_key.get_secret_value())
        else:
            self._client = anthropic.Anthropic()

    def parse(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, object]],
        output_format: type[T],
    ) -> T:
        try:
            response: Any = self._client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                output_format=output_format,
            )
        # AnthropicError covers transport/API failures; ValidationError covers a
        # truncated or schema-divergent response (messages.parse validates the
        # JSON internally and raises pydantic's ValidationError on bad output).
        except (anthropic.AnthropicError, ValidationError) as exc:
            raise GenerationError(f"Anthropic structured generation failed: {exc}") from exc

        parsed = getattr(response, "parsed_output", None)
        if not isinstance(parsed, output_format):
            raise GenerationError("structured generation returned no parsed output")
        return parsed
