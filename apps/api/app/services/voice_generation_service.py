from shared_types.structured_script import StructuredScript
from shared_types.voice_track import VoiceSegment, VoiceTrack

from provider_abstractions.interfaces import VoiceProvider


class VoiceGenerationError(Exception):
    """Raised when voice generation fails."""


class InvalidVoiceRequestError(Exception):
    """Raised when the generation request is invalid, before the provider is called."""


class VoiceGenerationService:
    """
    Turns a StructuredScript's narration and dialogue lines into a VoiceTrack.

    Voice selection uses a fixed simple mapping for now:
    narrator -> "narrator_voice", every character -> "default_voice".

    Timing: start_time/end_time are cumulative within each scene, built from
    the real duration returned by the VoiceProvider for each segment. The
    cursor resets to 0.0 at the start of every scene — segment times are
    relative to the scene, not the whole track.
    """

    def __init__(self, voice_provider: VoiceProvider):
        self._voice_provider = voice_provider

    async def generate(self, story_id: str, script: StructuredScript) -> VoiceTrack:
        self._validate(story_id, script)

        segments: list[VoiceSegment] = []

        try:
            for scene in script.scenes:
                cursor = 0.0

                if scene.narration:
                    voice = self._resolve_voice("narrator_voice", scene.emotion)
                    generated = await self._voice_provider.generate(
                        scene.narration, voice
                    )
                    start = cursor
                    end = cursor + generated.duration
                    segments.append(
                        VoiceSegment(
                            scene_number=scene.scene_number,
                            speaker="narrator",
                            start_time=start,
                            end_time=end,
                            audio=generated.audio,
                        )
                    )
                    cursor = end

                for line in scene.dialogue:
                    voice = self._resolve_voice("default_voice", line.emotion)
                    generated = await self._voice_provider.generate(
                        line.line, voice
                    )
                    start = cursor
                    end = cursor + generated.duration
                    segments.append(
                        VoiceSegment(
                            scene_number=scene.scene_number,
                            speaker=line.character,
                            start_time=start,
                            end_time=end,
                            audio=generated.audio,
                        )
                    )
                    cursor = end
        except Exception as exc:
            raise VoiceGenerationError("Voice generation failed") from exc

        return VoiceTrack(story_id=story_id, segments=segments)

    @staticmethod
    def _resolve_voice(base_voice: str, emotion: str | None) -> str:
        normalized_emotion = emotion.strip().lower() if emotion else ""
        return f"{base_voice}_{normalized_emotion or 'neutral'}"

    @staticmethod
    def _validate(story_id: str, script: StructuredScript) -> None:
        if not story_id or not story_id.strip():
            raise InvalidVoiceRequestError("story_id is required and cannot be empty")

        if script is None:
            raise InvalidVoiceRequestError("script is required and cannot be None")

        if not script.scenes:
            raise InvalidVoiceRequestError("script must contain at least one scene")
