from unittest.mock import AsyncMock

import pytest

from shared_types.story_dna import EndingType, POV, StoryDNA, TwistType

from app.services.ai_provider import AIProvider
from app.services.story_generation_service import (
    InvalidStoryRequestError,
    StoryGenerationError,
    StoryGenerationService,
)


class FakeAIProvider(AIProvider):
    def __init__(self, dna: StoryDNA):
        self.dna = dna
        self.received_idea = None

    async def generate_story_dna(self, original_idea: str) -> StoryDNA:
        self.received_idea = original_idea
        return self.dna


def make_story_dna() -> StoryDNA:
    return StoryDNA(
        premise="A woman receives phone calls from herself one day in the future.",
        setting="isolated apartment",
        threat="future version of the protagonist",
        fear_mechanism="paranoia and loss of control",
        narrative_device="phone calls",
        twist_type=TwistType.IDENTITY_REVEAL,
        ending_type=EndingType.AMBIGUOUS,
        pov=POV.FIRST_PERSON,
        time_period="present_day",
        supernatural_element="unknown",
        conflict="The protagonist must determine whether the calls are warnings or manipulation.",
        emotional_theme="paranoia",
        protagonist_archetype="ordinary_person",
        antagonist_archetype="unknown_force",
        core_fear="loss of control",
        visual_style="dark_realistic",
        unique_story_hook="Every call predicts an event that happens exactly one minute later.",
    )


async def test_generate_returns_story_dna_and_assigns_story_id():
    dna = make_story_dna()
    provider = FakeAIProvider(dna)
    service = StoryGenerationService(provider)

    result = await service.generate(
        story_id="story-123",
        original_idea="A woman gets phone calls from herself in the future.",
    )

    assert result is dna
    assert isinstance(result, StoryDNA)
    assert result.story_id == "story-123"
    assert provider.received_idea == (
        "A woman gets phone calls from herself in the future."
    )


async def test_generate_wraps_provider_failure():
    class FailingAIProvider(AIProvider):
        async def generate_story_dna(self, original_idea: str) -> StoryDNA:
            raise RuntimeError("AI provider unavailable")

    service = StoryGenerationService(FailingAIProvider())

    try:
        await service.generate(
            story_id="story-123",
            original_idea="A haunted apartment.",
        )
        assert False, "Expected StoryGenerationError"
    except StoryGenerationError as exc:
        assert str(exc) == "Story generation failed"
        assert isinstance(exc.__cause__, RuntimeError)


async def test_generate_rejects_empty_story_id_without_calling_provider():
    provider = FakeAIProvider(make_story_dna())
    service = StoryGenerationService(provider)

    try:
        await service.generate(story_id="", original_idea="A haunted apartment.")
        assert False, "Expected InvalidStoryRequestError"
    except InvalidStoryRequestError:
        pass

    assert provider.received_idea is None


async def test_generate_rejects_whitespace_only_story_id():
    provider = FakeAIProvider(make_story_dna())
    service = StoryGenerationService(provider)

    try:
        await service.generate(story_id="   ", original_idea="A haunted apartment.")
        assert False, "Expected InvalidStoryRequestError"
    except InvalidStoryRequestError:
        pass

    assert provider.received_idea is None


async def test_generate_rejects_empty_original_idea_without_calling_provider():
    provider = FakeAIProvider(make_story_dna())
    service = StoryGenerationService(provider)

    try:
        await service.generate(story_id="story-123", original_idea="")
        assert False, "Expected InvalidStoryRequestError"
    except InvalidStoryRequestError:
        pass

    assert provider.received_idea is None


async def test_generate_calls_provider_exactly_once():
    dna = make_story_dna()
    provider = AsyncMock(spec=AIProvider)
    provider.generate_story_dna.return_value = dna

    service = StoryGenerationService(provider)
    await service.generate(story_id="story-123", original_idea="A haunted apartment.")

    provider.generate_story_dna.assert_awaited_once_with("A haunted apartment.")
