"""
Real LLM provider backed by the Anthropic API.

Requires ANTHROPIC_API_KEY in the environment. This is NOT a stub -
it makes real API calls and is intended for production use, gated only
by configuration (see apps/api/app/core/container.py).
"""
import json
from typing import Any, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from provider_abstractions.interfaces import LLMProvider


class AnthropicLLMProvider(LLMProvider):
    """
    Real LLM provider backed by the Anthropic API.

    No os.environ access here - `api_key` must be passed explicitly by the
    caller (the composition root, app.core.container.get_llm_provider,
    reads it from the single centralized Settings object and raises a
    controlled ProviderConfigurationError if it's missing before this class
    is ever constructed).
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        if not api_key:
            raise ValueError("AnthropicLLMProvider requires a non-empty api_key.")
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        schema: Optional[type[BaseModel]] = None,
        max_tokens: int = 2000,
        temperature: float = 1.0,
    ) -> Any:
        effective_system = system or ""
        if schema is not None:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            effective_system = (
                f"{effective_system}\n\n"
                "You must respond with ONLY valid JSON matching this schema. "
                "No prose, no markdown fences, no preamble.\n\n"
                f"Schema:\n{schema_json}"
            ).strip()

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=effective_system or None,
            messages=[{"role": "user", "content": prompt}],
        )

        text = "".join(block.text for block in response.content if block.type == "text")

        if schema is None:
            return text

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            if cleaned.endswith("json"):
                cleaned = cleaned[:-4]

        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMOutputParsingError(
                f"Failed to parse {schema.__name__} from LLM output: {exc}\nRaw output: {text[:500]}"
            ) from exc


class LLMOutputParsingError(RuntimeError):
    """Raised when the LLM's response doesn't conform to the requested schema."""
