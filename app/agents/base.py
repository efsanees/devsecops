"""
Agent ABC ve AgentResult — tüm agent'ların uymak zorunda olduğu sözleşme.

Her agent:
  1. Agent sınıfından türer
  2. async run(state: dict) -> AgentResult implement eder
  3. state: orchestrator'ın tüm agent'lara geçirdiği paylaşımlı bağlam
     (repo_url, temp_dir, file_list, profiler çıktısı, vb.)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "data": self.data,
            "findings": self.findings,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class Agent(ABC):
    """
    Tüm agent'ların türediği temel sınıf.

    Kullanım:
        class MyAgent(Agent):
            name = "my_agent"

            async def run(self, state: dict) -> AgentResult:
                ...
    """

    name: str = "base_agent"

    async def execute(self, state: dict) -> AgentResult:
        """run()'u zamanlar ve hata yönetimi sağlar. Alt sınıflar bu metodu override etmez."""
        start = time.monotonic()
        try:
            result = await self.run(state)
            result.duration_seconds = time.monotonic() - start
            return result
        except Exception as exc:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    @abstractmethod
    async def run(self, state: dict) -> AgentResult:
        """
        Agent'ın asıl iş mantığı. Her alt sınıf bunu implement etmek zorunda.

        Args:
            state: Orchestrator'dan gelen paylaşımlı bağlam sözlüğü.
                   En az şunları içerir:
                   - repo_url (str)
                   - temp_dir (str | None): İndirilen repo'nun geçici dizini
                   - file_list (list[str]): Repo dosya yolları

        Returns:
            AgentResult: Başarı/hata durumu, bulgular ve ek veri.
        """
        ...
