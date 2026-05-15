"""
Orchestrator — 5 agent'ı koordine eder, sonuçları birleştirir.

Akış:
  1. Job durumunu DB'de "running" yap
  2. ProjectProfilerAgent  (sequential — file_list ve profile üretir)
  3. download_repo()       (bir kez indir, herkese paylaş)
  4. asyncio.gather()      (SAST, SCA, Secret, PipelineAnalyzer paralel)
  5. LLM Reasoner (Groq)  (bulgular → öneri metni)
  6. Pipeline Generator   (profile → YAML)
  7. DSOMM Scorer         (tüm sonuçlar → kategori puanları)
  8. DB'ye kaydet, WebSocket'e "completed" yayınla
  9. temp_dir temizle

State sözlüğü nasıl akar:
  Orchestrator bir state dict oluşturur.
  - Profiler çalışır → state["profile"] ve state["file_list"] güncellenir
  - Repo indirilir   → state["temp_dir"] güncellenir
  - Paralel agent'lar state'i OKUR, yazmaz (race condition yok)
  - Orchestrator agent sonuçlarını toplar

asyncio.gather neden return_exceptions=True:
  Bir Docker aracı yoksa veya ağ kopuksa o agent exception fırlatır.
  return_exceptions=True ile diğer agent'lar durmuyor; exception'lar
  AgentResult(success=False, error=...) olarak muamele görür.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from datetime import datetime, timezone

from groq import Groq

from app.agents.base import AgentResult
from app.agents.pipeline_analyzer import PipelineAnalyzerAgent
from app.agents.project_profiler import ProjectProfilerAgent
from app.agents.remediation_agent import run_remediation
from app.agents.sast_agent import SASTAgent
from app.agents.sca_agent import SCAAgent
from app.agents.secret_agent import SecretAgent
from app.api.ws import ensure_queue, publish
from app.generator.pipeline_generator import generate_pipeline
from app.scoring.dsomm import calculate_dsomm
from app.utils.repo_downloader import download_repo

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_result(result) -> AgentResult:
    """asyncio.gather'dan gelen exception'ı AgentResult'a çevirir."""
    if isinstance(result, Exception):
        return AgentResult(
            agent_name="unknown",
            success=False,
            error=str(result),
        )
    return result


async def _emit(job_id: str, event_type: str, **kwargs) -> None:
    await publish(job_id, {"type": event_type, **kwargs})


async def _run_llm_reasoner(profile: dict, all_findings: list[dict]) -> str:
    """
    Groq'a tüm bulguları gönderir, insan-okunabilir öneri metni alır.
    Hata durumunda boş string döner — orchestrator bunu tolere eder.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return ""

    # Özet istatistik — tüm bulgu listesini LLM'e göndermiyoruz (token limiti)
    sast = [f for f in all_findings if f.get("type") == "SAST"]
    sca = [f for f in all_findings if f.get("type") == "SCA"]
    secrets = [f for f in all_findings if f.get("type") == "SECRET"]

    def sev_counts(findings: list[dict]) -> str:
        high = sum(1 for f in findings if f.get("severity") in ("HIGH", "CRITICAL"))
        med = sum(1 for f in findings if f.get("severity") == "MEDIUM")
        return f"HIGH/CRITICAL: {high}, MEDIUM: {med}"

    top_sast = [
        f"{f.get('rule_id', '')} — {f.get('file', '')}:{f.get('line', '')} — {f.get('message', '')[:80]}"
        for f in sast[:5]
    ]
    top_sca = [
        f"{f.get('vuln_id', '')} — {f.get('package', '')}@{f.get('version', '')} — {f.get('summary', '')[:80]}"
        for f in sca[:5]
    ]

    prompt = f"""Sen bir DevSecOps güvenlik uzmanısın. Aşağıdaki repo analiz sonuçlarını inceleyip
kısa ve eyleme dönüştürülebilir Türkçe öneriler sun.

Proje: {profile.get('language', '?')} / {profile.get('framework', '?')}
Docker: {profile.get('has_docker', False)}, Test dosyası: {profile.get('has_tests', False)}

SAST bulguları ({sev_counts(sast)}):
{chr(10).join(top_sast) or 'Yok'}

SCA (bağımlılık) bulguları ({sev_counts(sca)}):
{chr(10).join(top_sca) or 'Yok'}

Hardcoded secret sayısı: {len(secrets)}

Lütfen:
1. En kritik 3 riski kısaca belirt (madde madde)
2. Her risk için somut düzeltme öner
3. Genel güvenlik olgunluk değerlendirmesi yap (2-3 cümle)
Cevabın toplam uzunluğu 300 kelimeyi geçmesin."""

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[Orchestrator] LLM reasoner hatası: %s", exc)
        return ""


class Orchestrator:

    async def run(
        self,
        job_id: str,
        repo_url: str,
        token: str = "",
        platform: str = "github_actions",
    ) -> dict:
        """
        Tam analiz akışını çalıştırır.
        BackgroundTasks tarafından çağrılır (async, event loop içinde).

        Returns:
            Nihai sonuç dict'i (DB'ye de kaydedilir).
        """
        ensure_queue(job_id)
        start_time = time.monotonic()
        temp_base: str | None = None

        # ── DB güncellemeleri sync olduğu için import burada ──
        from app.database import SessionLocal
        from app.models.job import Job, AgentRun

        def _update_job(status: str, result: dict | None = None, error: str | None = None):
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                if job:
                    job.status = status
                    if status == "running":
                        job.started_at = _now()
                    if status in ("completed", "failed"):
                        job.finished_at = _now()
                    if result:
                        job.result = result
                    if error:
                        job.error = error
                    db.commit()

        def _save_agent_run(name: str, agent_result: AgentResult):
            with SessionLocal() as db:
                run = AgentRun(
                    job_id=job_id,
                    agent_name=name,
                    status="completed" if agent_result.success else "failed",
                    started_at=_now(),
                    finished_at=_now(),
                    duration_seconds=agent_result.duration_seconds,
                    data=agent_result.data,
                    findings=agent_result.findings,
                    error=agent_result.error,
                )
                db.add(run)
                db.commit()

        try:
            await asyncio.to_thread(_update_job, "running")
            await _emit(job_id, "job_started", message="Analiz başladı")

            # ── ADIM 1: Project Profiler (sequential) ────────────────────
            await _emit(job_id, "agent_started", agent="project_profiler")
            profiler = ProjectProfilerAgent()
            state: dict = {"repo_url": repo_url, "token": token}
            profile_result = await profiler.execute(state)
            await asyncio.to_thread(_save_agent_run, "project_profiler", profile_result)

            if not profile_result.success:
                raise RuntimeError(f"Profiler başarısız: {profile_result.error}")

            profile = profile_result.data
            file_list = profile.get("files", [])
            state["profile"] = profile
            state["file_list"] = file_list

            await _emit(job_id, "agent_completed", agent="project_profiler",
                        data={"language": profile.get("language"), "framework": profile.get("framework")})

            # ── ADIM 2: Repo indir (bir kez, herkese paylaş) ─────────────
            await _emit(job_id, "job_status", message="Repo indiriliyor")
            repo_dir, temp_base = await asyncio.to_thread(download_repo, repo_url, token)
            state["temp_dir"] = repo_dir
            logger.info("[Orchestrator] Repo hazır: %s", repo_dir)

            # ── ADIM 3: 4 agent paralel ───────────────────────────────────
            # Her agent state'i okur, return_exceptions ile birinden
            # exception gelse diğerleri durmuyor.
            for agent_name in ("sast", "sca", "secret_detection", "pipeline_analyzer"):
                await _emit(job_id, "agent_started", agent=agent_name)

            parallel_results = await asyncio.gather(
                SASTAgent().execute(state),
                SCAAgent().execute(state),
                SecretAgent().execute(state),
                PipelineAnalyzerAgent().execute(state),
                return_exceptions=True,
            )

            sast_r   = _safe_result(parallel_results[0])
            sca_r    = _safe_result(parallel_results[1])
            secret_r = _safe_result(parallel_results[2])
            pipeline_r = _safe_result(parallel_results[3])

            # Her agent'ın sonucunu kaydet ve event yayınla
            for name, result in [
                ("sast", sast_r), ("sca", sca_r),
                ("secret_detection", secret_r), ("pipeline_analyzer", pipeline_r),
            ]:
                await asyncio.to_thread(_save_agent_run, name, result)
                event_type = "agent_completed" if result.success else "agent_failed"
                await _emit(job_id, event_type, agent=name,
                            data=result.data, error=result.error)

            # ── ADIM 4: Tüm bulgular ──────────────────────────────────────
            all_findings: list[dict] = []
            for r in (sast_r, sca_r, secret_r):
                all_findings.extend(r.findings)

            # ── ADIM 5: LLM Reasoner ──────────────────────────────────────
            await _emit(job_id, "job_status", message="Bulgular yorumlanıyor")
            llm_summary = await _run_llm_reasoner(profile, all_findings)

            # ── ADIM 5b: Remediation önerileri ───────────────────────────
            await _emit(job_id, "job_status", message="AI düzeltme önerileri üretiliyor")
            await run_remediation(sast_r.findings, sca_r.findings, profile)

            # ── ADIM 6: Pipeline Generator ────────────────────────────────
            await _emit(job_id, "job_status", message="Pipeline YAML üretiliyor")
            try:
                pipeline_yaml = await asyncio.to_thread(
                    generate_pipeline, profile, file_list, platform
                )
            except Exception as exc:
                logger.warning("[Orchestrator] Pipeline üretilemedi: %s", exc)
                pipeline_yaml = ""

            # ── ADIM 7: DSOMM Scorer ──────────────────────────────────────
            dsomm = calculate_dsomm(
                profile=profile,
                pipeline_result=pipeline_r.data if pipeline_r.success else {},
                sast_result=sast_r.data if sast_r.success else {},
                sca_result=sca_r.data if sca_r.success else {},
                secret_result=secret_r.data if secret_r.success else {},
                file_list=file_list,
            )

            # ── ADIM 8: Sonucu birleştir ve kaydet ────────────────────────
            elapsed = round(time.monotonic() - start_time, 1)

            final_result = {
                "job_id": job_id,
                "repo_url": repo_url,
                "platform": platform,
                "profile": {k: v for k, v in profile.items() if k != "files"},
                "dsomm": dsomm,
                "pipeline_analysis": pipeline_r.data if pipeline_r.success else {},
                "findings": {
                    "sast": sast_r.findings,
                    "sca": sca_r.findings,
                    "secret": secret_r.findings,
                    "pipeline": pipeline_r.findings,
                },
                "llm_summary": llm_summary,
                "pipeline_yaml": pipeline_yaml,
                "elapsed_seconds": elapsed,
            }

            await asyncio.to_thread(_update_job, "completed", final_result)
            await _emit(job_id, "job_completed",
                        message=f"Analiz tamamlandı ({elapsed}s)",
                        score=dsomm["total_score"],
                        level=dsomm["level"])

            logger.info("[Orchestrator] Tamamlandı: job=%s, skor=%d, süre=%.1fs",
                        job_id, dsomm["total_score"], elapsed)
            return final_result

        except Exception as exc:
            logger.error("[Orchestrator] Hata: %s", exc, exc_info=True)
            await asyncio.to_thread(_update_job, "failed", error=str(exc))
            await _emit(job_id, "job_failed", error=str(exc))
            raise

        finally:
            # Temp dizini her durumda temizle
            if temp_base and os.path.exists(temp_base):
                shutil.rmtree(temp_base, ignore_errors=True)
                logger.info("[Orchestrator] Temp dizin temizlendi: %s", temp_base)
