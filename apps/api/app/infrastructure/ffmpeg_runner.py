from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class FFmpegExecutionError(Exception):
    """Raised when the FFmpeg subprocess exits with a non-zero return code."""


class FFmpegRunner(ABC):
    @abstractmethod
    async def run(self, command: list[str]) -> None:
        raise NotImplementedError


class SubprocessFFmpegRunner(FFmpegRunner):
    """
    Real FFmpeg execution via subprocess. Assumes `ffmpeg` is on PATH
    (confirmed installed as FFmpeg 8.1.2 in this Termux environment).
    """

    async def run(self, command: list[str]) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise FFmpegExecutionError(
                f"ffmpeg exited with code {process.returncode}: "
                f"{stderr.decode(errors='replace')}"
            )
