import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from shared_types.story_dna import StoryDNA, TwistType, EndingType, POV
from shared_types.structured_script import StructuredScript, SceneItem
from app.domain.story_workflow import StoryStatus, InvalidTransitionError
from app.services.story_workflow_orchestrator import StoryWorkflowOrchestrator


def make_story_dna(story_id: str) -> StoryDNA:
    return StoryDNA(
        story_id=story_id,
        premise="A man receives calls from himself one hour in the future.",
        setting="empty apartment",
        threat="a version of himself from the future",
        fear_mechanism="loss of control over one's own timeline",
        narrative_device="phone calls",
        twist_type=TwistType.TIME_LOOP,
        ending_type=EndingType.CLIFFHANGER,
        pov=POV.FIRST_PERSON,
        conflict="man vs his own future self",
        emotional_theme="paranoia",
        core_fear="losing agency over your own life",
        unique_story_hook="the calls get closer together each time",
    )


def make_structured_script() -> StructuredScript:
    return StructuredScript(
        title="The Empty Apartment",
        logline="A man receives calls from himself, one hour ahead.",
        tone="dread",
        language="ar",
        estimated_duration=90.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="establish isolation",
                location="empty apartment",
                time_of_day="night",
                characters=["Man"],
                action="He stares at his phone, waiting.",
                dialogue=[],
                narration="I knew the call was coming.",
                emotion="dread",
                estimated_duration=15.0,
            )
        ],
    )


def make_orchestrator(
    workflow_service=None,
    generation_service=None,
    repository=None,
    script_generation_service=None,
    editing_service=None,
    voice_generation_service=None,
):
    return StoryWorkflowOrchestrator(
        workflow_service=workflow_service or AsyncMock(),
        generation_service=generation_service or AsyncMock(),
        repository=repository or AsyncMock(),
        script_generation_service=script_generation_service or AsyncMock(),
        editing_service=editing_service or AsyncMock(),
        voice_generation_service=voice_generation_service or AsyncMock(),
    )


@pytest.mark.asyncio
async def test_advance_to_generation_runs_full_pipeline_in_order():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )
    generating_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.GENERATING,
    )
    editing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.EDITING,
    )

    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()

    call_order = []
    workflow_service = AsyncMock()

    async def transition_side_effect(sid, target_state):
        call_order.append(("transition", target_state))

        if target_state == StoryStatus.ANALYZING:
            return analyzing_story
        if target_state == StoryStatus.GENERATING:
            return generating_story
        if target_state == StoryStatus.EDITING:
            return editing_story

        return SimpleNamespace(
            id=sid,
            original_idea=original_idea,
            status=target_state,
        )

    workflow_service.transition_story.side_effect = transition_side_effect

    generation_service = AsyncMock()

    async def generate_side_effect(story_id, original_idea):
        call_order.append(("generate",))
        return expected_dna

    generation_service.generate.side_effect = generate_side_effect

    repository = AsyncMock()

    async def save_dna_side_effect(sid, dna):
        call_order.append(("save_dna",))

    async def save_script_side_effect(sid, script):
        call_order.append(("save_script",))

    repository.save_dna.side_effect = save_dna_side_effect
    repository.save_script.side_effect = save_script_side_effect

    script_generation_service = AsyncMock()

    async def generate_script_side_effect(dna):
        call_order.append(("generate_script",))
        return expected_script

    script_generation_service.generate.side_effect = generate_script_side_effect

    editing_service = AsyncMock()

    async def edit_side_effect(sid, script):
        call_order.append(("edit",))

    editing_service.edit.side_effect = edit_side_effect

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
    )

    result = await orchestrator.advance_to_generation(story_id)

    assert call_order == [
        ("transition", StoryStatus.ANALYZING),
        ("generate",),
        ("transition", StoryStatus.GENERATING),
        ("save_dna",),
        ("generate_script",),
        ("save_script",),
        ("edit",),
        ("transition", StoryStatus.EDITING),
    ]

    assert result == {
        "dna": expected_dna,
        "script": expected_script,
    }


@pytest.mark.asyncio
async def test_advance_to_generation_does_not_generate_when_analyzing_transition_fails():
    story_id = str(uuid.uuid4())

    workflow_service = AsyncMock()
    workflow_service.transition_story.side_effect = InvalidTransitionError(
        "Transition not allowed."
    )

    generation_service = AsyncMock()
    repository = AsyncMock()
    script_generation_service = AsyncMock()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    with pytest.raises(InvalidTransitionError):
        await orchestrator.advance_to_generation(story_id)

    generation_service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_generation_does_not_transition_to_generating_when_dna_generation_fails():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.side_effect = RuntimeError("generation failed")

    repository = AsyncMock()
    script_generation_service = AsyncMock()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_awaited_once_with(
        story_id,
        StoryStatus.ANALYZING,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_saves_generated_dna():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."
    expected_dna = make_story_dna(story_id)

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()
    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = make_structured_script()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    await orchestrator.advance_to_generation(story_id)

    repository.save_dna.assert_awaited_once_with(
        story_id,
        expected_dna,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_save_dna_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()
    repository.save_dna.side_effect = RuntimeError("save dna failed")

    script_generation_service = AsyncMock()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    with pytest.raises(RuntimeError, match="save dna failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_any_await(
        story_id,
        StoryStatus.FAILED,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_generates_script_from_dna():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."
    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    await orchestrator.advance_to_generation(story_id)

    script_generation_service.generate.assert_awaited_once_with(
        expected_dna,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_saves_generated_script():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."
    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    await orchestrator.advance_to_generation(story_id)

    repository.save_script.assert_awaited_once_with(
        story_id,
        expected_script,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_script_generation_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.side_effect = RuntimeError(
        "script generation failed"
    )

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    with pytest.raises(RuntimeError, match="script generation failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_any_await(
        story_id,
        StoryStatus.FAILED,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_save_script_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()
    repository.save_script.side_effect = RuntimeError("save script failed")

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = make_structured_script()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    with pytest.raises(RuntimeError, match="save script failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_any_await(
        story_id,
        StoryStatus.FAILED,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_returns_dna_and_script():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
    )

    result = await orchestrator.advance_to_generation(story_id)

    assert result == {
        "dna": expected_dna,
        "script": expected_script,
    }


@pytest.mark.asyncio
async def test_orchestrator_requires_repository_raises_clear_error():
    with pytest.raises(TypeError):
        StoryWorkflowOrchestrator(
            workflow_service=Mock(),
            generation_service=Mock(),
        )


@pytest.mark.asyncio
async def test_orchestrator_requires_script_generation_service():
    with pytest.raises(TypeError):
        StoryWorkflowOrchestrator(
            workflow_service=Mock(),
            generation_service=Mock(),
            repository=Mock(),
        )


@pytest.mark.asyncio
async def test_advance_to_generation_calls_editing_service_after_script_is_saved():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()
    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    editing_service = AsyncMock()

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
    )

    await orchestrator.advance_to_generation(story_id)

    editing_service.edit.assert_awaited_once_with(
        story_id,
        expected_script,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_saves_generated_edit_plan():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."
    expected_dna = make_story_dna(story_id)
    expected_script = make_structured_script()
    expected_edit_plan = SimpleNamespace(story_id=story_id, total_duration=90.0, cuts=[])

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = expected_dna

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    editing_service = AsyncMock()
    editing_service.edit.return_value = expected_edit_plan

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
    )

    await orchestrator.advance_to_generation(story_id)

    repository.save_edit_plan.assert_awaited_once_with(
        story_id,
        expected_edit_plan,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_save_edit_plan_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()
    repository.save_edit_plan.side_effect = RuntimeError("save edit plan failed")

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = make_structured_script()

    editing_service = AsyncMock()
    editing_service.edit.return_value = SimpleNamespace(
        story_id=story_id, total_duration=90.0, cuts=[]
    )

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
    )

    with pytest.raises(RuntimeError, match="save edit plan failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_any_await(
        story_id,
        StoryStatus.FAILED,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_saves_generated_voice_track():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."
    expected_script = make_structured_script()
    expected_voice_track = SimpleNamespace(story_id=story_id, segments=[])

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = expected_script

    editing_service = AsyncMock()
    editing_service.edit.return_value = SimpleNamespace(
        story_id=story_id, total_duration=90.0, cuts=[]
    )

    voice_generation_service = AsyncMock()
    voice_generation_service.generate.return_value = expected_voice_track

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
        voice_generation_service=voice_generation_service,
    )

    await orchestrator.advance_to_generation(story_id)

    voice_generation_service.generate.assert_awaited_once_with(
        story_id,
        expected_script,
    )
    repository.save_voice_track.assert_awaited_once_with(
        story_id,
        expected_voice_track,
    )


@pytest.mark.asyncio
async def test_advance_to_generation_save_voice_track_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    original_idea = "A man receives calls from himself one hour in the future."

    analyzing_story = SimpleNamespace(
        id=story_id,
        original_idea=original_idea,
        status=StoryStatus.ANALYZING,
    )

    workflow_service = AsyncMock()
    workflow_service.transition_story.return_value = analyzing_story

    generation_service = AsyncMock()
    generation_service.generate.return_value = make_story_dna(story_id)

    repository = AsyncMock()
    repository.save_voice_track.side_effect = RuntimeError("save voice track failed")

    script_generation_service = AsyncMock()
    script_generation_service.generate.return_value = make_structured_script()

    editing_service = AsyncMock()
    editing_service.edit.return_value = SimpleNamespace(
        story_id=story_id, total_duration=90.0, cuts=[]
    )

    voice_generation_service = AsyncMock()
    voice_generation_service.generate.return_value = SimpleNamespace(
        story_id=story_id, segments=[]
    )

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        generation_service=generation_service,
        repository=repository,
        script_generation_service=script_generation_service,
        editing_service=editing_service,
        voice_generation_service=voice_generation_service,
    )

    with pytest.raises(RuntimeError, match="save voice track failed"):
        await orchestrator.advance_to_generation(story_id)

    workflow_service.transition_story.assert_any_await(
        story_id,
        StoryStatus.FAILED,
    )
