from shared_types.story_dna import StoryDNA
from shared_types.structured_script import StructuredScript

from app.services.ai_provider import AIProvider


class ScriptGenerationError(Exception):
    """Raised when structured script generation fails."""


class InvalidScriptRequestError(Exception):
    """Raised when the generation request is invalid, before the provider is called."""


class ScriptGenerationService:
    def __init__(self, ai_provider: AIProvider):
        self._ai_provider = ai_provider

    async def generate(self, story_dna: StoryDNA) -> StructuredScript:
        if story_dna is None:
            raise InvalidScriptRequestError("story_dna is required and cannot be None")

        try:
            return await self._ai_provider.generate_structured_script(story_dna)
        except Exception as exc:
            raise ScriptGenerationError(
                "Structured script generation failed"
            ) from exc
