from unittest.mock import AsyncMock

import pytest

from app.services.ai_provider import AIProvider
from app.services.script_generation_service import (
    ScriptGenerationError,
    ScriptGenerationService,
)
from shared_types.story_dna import StoryDNA
from shared_types.structured_script import (
    DialogueLine,
    SceneItem,
    StructuredScript,
)


def make_story_dna() -> StoryDNA:
    return StoryDNA(
        premise="رجل يسمع طرقًا على باب شقته رغم أنه يعيش وحده.",
        setting="شقة قديمة في القاهرة",
        threat="كيان غامض خلف الباب",
        fear_mechanism="العزلة والشك في الواقع",
        narrative_device="كشف تدريجي",
        twist_type="identity_reveal",
        ending_type="ambiguous",
        pov="first_person",
        time_period="present",
        supernatural_element="كيان خارق",
        conflict="الرجل يحاول معرفة من يطرق الباب",
        emotional_theme="الخوف من الوحدة",
        protagonist_archetype="ordinary_person",
        antagonist_archetype="supernatural_entity",
        core_fear="being watched",
        visual_style="dark cinematic horror",
        unique_story_hook="الطرق يأتي من داخل الشقة أحيانًا",
    )


def make_structured_script() -> StructuredScript:
    return StructuredScript(
        title="الباب الأخير",
        logline="رجل يسمع طرقًا على باب شقته رغم أنه يعيش وحده.",
        tone="psychological horror",
        language="ar",
        estimated_duration=45.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="Establish the mystery",
                location="شقة قديمة",
                time_of_day="night",
                characters=["أحمد"],
                action="أحمد يسمع طرقًا على الباب.",
                dialogue=[
                    DialogueLine(
                        character="أحمد",
                        line="مين؟",
                        emotion="terrified",
                    )
                ],
                narration="كان أحمد متأكدًا أنه يعيش وحده.",
                emotion="fear",
                estimated_duration=12.0,
            )
        ],
    )


@pytest.mark.asyncio
async def test_generate_returns_structured_script_from_story_dna():
    dna = make_story_dna()
    expected_script = make_structured_script()

    ai_provider = AsyncMock(spec=AIProvider)
    ai_provider.generate_structured_script.return_value = expected_script

    service = ScriptGenerationService(ai_provider)

    result = await service.generate(dna)

    assert result is expected_script
    assert isinstance(result, StructuredScript)
    assert result.title == "الباب الأخير"
    assert len(result.scenes) == 1
    assert result.scenes[0].dialogue[0].emotion == "terrified"

    ai_provider.generate_structured_script.assert_awaited_once_with(dna)


@pytest.mark.asyncio
async def test_generate_wraps_ai_provider_error():
    dna = make_story_dna()

    ai_provider = AsyncMock(spec=AIProvider)
    ai_provider.generate_structured_script.side_effect = RuntimeError(
        "AI provider unavailable"
    )

    service = ScriptGenerationService(ai_provider)

    with pytest.raises(
        ScriptGenerationError,
        match="Structured script generation failed",
    ) as exc_info:
        await service.generate(dna)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    ai_provider.generate_structured_script.assert_awaited_once_with(dna)
