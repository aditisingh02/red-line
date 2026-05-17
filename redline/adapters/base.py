"""TargetAdapter interface — all targets implement this."""
from __future__ import annotations

import abc


class TargetAdapter(abc.ABC):
    @abc.abstractmethod
    async def send_prompt(self, prompt: str) -> str:
        """Send a prompt to the target agent and return its response string."""
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verify the target is reachable before the scan begins."""
        raise NotImplementedError
