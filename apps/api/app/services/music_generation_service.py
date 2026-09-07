from shared_types.music_plan import MusicCue
from shared_types.music_asset import MusicAsset

from provider_abstractions.interfaces import MusicProvider


class MusicGenerationError(Exception):
    """Raised when music asset generation fails."""


class InvalidMusicGenerationRequestError(Exception):
    """Raised when the generation request is invalid, before the provider is called."""


class MusicGenerationService:
    """
    Turns a single MusicCue into a MusicAsset (real generated audio).

    The requested duration passed to MusicProvider is the PLANNED duration
    (cue.end_time - cue.start_time). The provider's actual returned duration
    may differ — that's recorded as actual_duration and left for Assembly
    to reconcile. This service does not own timeline: MusicAsset carries
    no start_time/end_time.
    """

    def __init__(self, music_provider: MusicProvider):
        self._music_provider = music_provider

    async def generate(self, story_id: str, cue: MusicCue) -> MusicAsset:
        self._validate(story_id, cue)

        planned_duration = cue.end_time - cue.start_time

        try:
            generated = await self._music_provider.generate(
                cue.music_prompt, planned_duration
            )
        except Exception as exc:
            raise MusicGenerationError("Music asset generation failed") from exc

        return MusicAsset(
            story_id=story_id,
            cue_number=cue.cue_number,
            asset=generated.audio,
            actual_duration=generated.duration,
        )

    @staticmethod
    def _validate(story_id: str, cue: MusicCue) -> None:
        if not story_id:
            raise InvalidMusicGenerationRequestError("story_id is required")

        if cue is None:
            raise InvalidMusicGenerationRequestError("cue is required")
