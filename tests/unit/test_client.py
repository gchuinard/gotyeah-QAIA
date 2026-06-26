from __future__ import annotations

import pytest
from pydantic import BaseModel

from qaia.domain.errors import GenerationError
from qaia.generation.client import AnthropicStructuredLLM


class _Out(BaseModel):
    value: int


class _RaisingMessages:
    def parse(self, **kwargs: object) -> object:
        # Simulate messages.parse validating a truncated/schema-divergent response:
        # the SDK runs model_validate internally, which raises pydantic ValidationError.
        _Out.model_validate({"value": "not-an-int"})
        raise AssertionError("unreachable")  # model_validate raises first


class _RaisingClient:
    messages = _RaisingMessages()


def test_validation_error_is_wrapped_as_generation_error() -> None:
    llm = AnthropicStructuredLLM(client=_RaisingClient())  # type: ignore[arg-type]
    with pytest.raises(GenerationError):
        llm.parse(model="m", max_tokens=10, system="s", messages=[], output_format=_Out)
