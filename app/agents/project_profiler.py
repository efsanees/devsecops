"""
Project Profiler Agent — repo'nun dilini, framework'ünü, build komutlarını tespit eder.

Orchestrator'da SEQUENTIAL çalışır (diğer agent'lardan önce):
sonuçları (file_list, language, framework, vb.) state'e yazılır,
paralel agent'lar bu state'i okur.

analyze_repo() senkron (requests tabanlı) — asyncio.to_thread ile
event loop'u bloklamadan thread pool'da çalıştırılır.
"""

import asyncio
import logging

from app.agents.base import Agent, AgentResult
from app.analyzer.repo_analyzer import analyze_repo, detect_commands

logger = logging.getLogger(__name__)


class ProjectProfilerAgent(Agent):
    name = "project_profiler"

    async def run(self, state: dict) -> AgentResult:
        repo_url = state["repo_url"]
        token = state.get("token", "")

        logger.info("[ProjectProfiler] Başlıyor: %s", repo_url)

        # analyze_repo senkron — thread pool'a gönder
        profile = await asyncio.to_thread(analyze_repo, repo_url, token)

        if profile["language"] == "unknown":
            logger.warning("[ProjectProfiler] Dil tespit edilemedi")

        build_cmd, test_cmd = detect_commands(profile)

        data = {
            **profile,
            "build_cmd": build_cmd,
            "test_cmd": test_cmd,
        }

        logger.info(
            "[ProjectProfiler] Tamamlandı: %s / %s (%d dosya)",
            profile["language"],
            profile["framework"],
            len(profile.get("files", [])),
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=data,
        )
