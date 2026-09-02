from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from originality_engine.vector_store import VectorStore, VectorMatch
from shared_types.story_dna import StoryDNA

from app.models.story import StoryDNAModel


class PgVectorStore(VectorStore):
    """Production VectorStore backed by pgvector's <-> (cosine distance) operator."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, story_id: str, dna: StoryDNA) -> None:
        # Persistence of story_dna rows happens through the normal story
        # creation flow (see app/routers/stories.py); this method exists to
        # satisfy the VectorStore interface for direct engine use/tests.
        raise NotImplementedError("Use the stories router / repository to persist DNA rows.")

    async def nearest(self, embedding: list[float], top_k: int = 10) -> list[VectorMatch]:
        stmt = (
            select(StoryDNAModel, StoryDNAModel.embedding.cosine_distance(embedding).label("distance"))
            .where(StoryDNAModel.embedding.is_not(None))
            .order_by("distance")
            .limit(top_k)
        )
        rows = (await self._session.execute(stmt)).all()

        matches = []
        for model, distance in rows:
            similarity = 1.0 - float(distance)
            matches.append(
                VectorMatch(
                    story_id=str(model.story_id),
                    dna=_model_to_dna(model),
                    similarity=max(0.0, min(1.0, similarity)),
                )
            )
        return matches


def _model_to_dna(model: StoryDNAModel) -> StoryDNA:
    return StoryDNA(
        id=str(model.id),
        story_id=str(model.story_id),
        premise=model.premise,
        setting=model.setting,
        threat=model.threat,
        fear_mechanism=model.fear_mechanism,
        narrative_device=model.narrative_device,
        twist_type=model.twist_type,
        ending_type=model.ending_type,
        pov=model.pov,
        time_period=model.time_period,
        supernatural_element=model.supernatural_element,
        conflict=model.conflict,
        emotional_theme=model.emotional_theme,
        protagonist_archetype=model.protagonist_archetype,
        antagonist_archetype=model.antagonist_archetype,
        core_fear=model.core_fear,
        visual_style=model.visual_style,
        unique_story_hook=model.unique_story_hook,
        embedding=list(model.embedding) if model.embedding is not None else None,
    )
