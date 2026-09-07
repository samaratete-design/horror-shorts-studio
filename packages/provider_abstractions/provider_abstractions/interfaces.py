"""
Provider interfaces.

CRITICAL RULE: business logic (engines, services) must depend only on these
abstract classes, never on a concrete provider (Anthropic, OpenAI, ElevenLabs,
Runway, etc). Concrete implementations live in this package's `impl/` modules
and are wired up at the composition root (apps/api/app/core/container.py).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel


class LLMProvider(ABC):
    """Any text/JSON-generating LLM (Claude, GPT, Gemini, local model...)."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        schema: Optional[type[BaseModel]] = None,
        max_tokens: int = 2000,
        temperature: float = 1.0,
    ) -> Any:
        """
        Returns a parsed `schema` instance if `schema` is provided,
        otherwise returns raw text.
        """
        raise NotImplementedError


class EmbeddingProvider(ABC):
    """Turns text into a fixed-length vector for similarity search."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, aspect_ratio: str = "9:16") -> bytes:
        raise NotImplementedError


@dataclass(frozen=True)
class GeneratedAudio:
    """Result of a VoiceProvider generation call: the audio plus its real duration."""
    audio: bytes
    duration: float


class VoiceProvider(ABC):
    @abstractmethod
    async def generate(self, text: str, voice: str) -> GeneratedAudio:
        raise NotImplementedError


class VideoProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, duration_seconds: float) -> bytes:
        raise NotImplementedError
@dataclass(frozen=True)
class GeneratedVideo:
    """Result of a VideoProvider generation call: the video plus its real duration."""
    video: bytes
    duration: float


@dataclass(frozen=True)
class GeneratedMusic:
    """Result of a MusicProvider generation call: the audio plus its real duration."""
    audio: bytes
    duration: float


class MusicProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, duration_seconds: float) -> GeneratedMusic:
        raise NotImplementedError
