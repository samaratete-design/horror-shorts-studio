from shared_types.story_dna import StoryDNA
from app.services.ai_provider import AIProvider


class StoryGenerationError(Exception):
    """Raised when story generation fails."""


class InvalidStoryRequestError(Exception):
    """Raised when the generation request is invalid, before the provider is called."""


class StoryGenerationService:
    def __init__(self, ai_provider: AIProvider):
        self._ai_provider = ai_provider

    async def generate(self, story_id: str, original_idea: str) -> StoryDNA:
        self._validate(story_id, original_idea)

        try:
            dna = await self._ai_provider.generate_story_dna(original_idea)
        except Exception as exc:
            raise StoryGenerationError("Story generation failed") from exc

        dna.story_id = story_id
        return dna

    @staticmethod
    def _validate(story_id: str, original_idea: str) -> None:
        if not story_id or not story_id.strip():
            raise InvalidStoryRequestError("story_id is required and cannot be empty")

        if not original_idea or not original_idea.strip():
            raise InvalidStoryRequestError("original_idea is required and cannot be empty")
