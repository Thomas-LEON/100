# ============================================================
# backend/agents/pipeline.py
# Main Pipeline Coordinator — runs all 6 agents in sequence
#
# Flow: Agent1(Silobreak) → Agent2(Legal) → Agent3(Executive)
#       → Agent4(Operations) → Agent5(Evidence) → Agent6(Orchestrator)
#       → PDF Generation
# ============================================================
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import Report, Company, ReportStatus, RiskLevel
from .agent_silobreak import run_silobreak_agent
from .agent_legal import run_legal_agent
from .agent_executive import run_executive_agent
from .agent_operations import run_operations_agent
from .agent_evidence import run_evidence_agent
from .agent_orchestrator import run_orchestrator_agent
from ..services.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    report_id: int,
    company_name: str,
    domain: Optional[str],
    db: AsyncSession,
) -> None:
    """
    Execute the full 6-agent adverse news pipeline for a given report.
    Updates the report record at each stage.
    Runs as a background task.
    """
    logger.info(f"[PIPELINE] Starting for report_id={report_id}, company={company_name}")

    try:
        # ── Mark as PROCESSING ──────────────────────────────────────────
        await _update_report_status(db, report_id, ReportStatus.PROCESSING)

        # ── AGENT 1: Silobreak Acquisition & Triage ─────────────────────
        logger.info(f"[AGENT 1] Silobreak triage for {company_name}")
        triage_data = await run_silobreak_agent(company_name, domain)
        await _save_agent_output(db, report_id, "raw_data_json", triage_data)

        # ── AGENTS 2, 3, 4: Run in parallel (independent) ───────────────
        logger.info(f"[AGENTS 2-4] Running analytical agents in parallel")
        legal_task = run_legal_agent(company_name, triage_data)
        executive_task = run_executive_agent(company_name, triage_data)
        operations_task = run_operations_agent(company_name, triage_data)

        legal_analysis, executive_analysis, operations_analysis = await asyncio.gather(
            legal_task, executive_task, operations_task,
            return_exceptions=False,
        )

        await _save_agent_output(db, report_id, "legal_analysis_json", legal_analysis)
        await _save_agent_output(db, report_id, "executive_analysis_json", executive_analysis)
        await _save_agent_output(db, report_id, "operations_analysis_json", operations_analysis)

        # ── AGENT 5: Evidence Validation ────────────────────────────────
        logger.info(f"[AGENT 5] Evidence validation")
        evidence_validation = await run_evidence_agent(
            company_name,
            triage_data,
            legal_analysis,
            executive_analysis,
            operations_analysis,
        )
        await _save_agent_output(db, report_id, "evidence_json", evidence_validation)

        # ── AGENT 6: Orchestrator / Final Synthesis ──────────────────────
        logger.info(f"[AGENT 6] Orchestrator final synthesis")
        final_report = await run_orchestrator_agent(
            company_name,
            domain,
            triage_data,
            legal_analysis,
            executive_analysis,
            operations_analysis,
            evidence_validation,
        )
        await _save_agent_output(db, report_id, "final_report_json", final_report)

        # ── Extract Key Fields ───────────────────────────────────────────
        cvs = final_report.get("cyber_vulnerability_score", 0)
        risk_level_str = final_report.get("risk_level", "UNKNOWN").upper()
        top_issues_list = final_report.get("top_issues", [])
        top_issues_str = ", ".join(top_issues_list[:5])

        risk_level_map = {
            "LOW": RiskLevel.LOW,
            "MEDIUM": RiskLevel.MEDIUM,
            "HIGH": RiskLevel.HIGH,
        }
        risk_level = risk_level_map.get(risk_level_str, RiskLevel.UNKNOWN)

        # ── Generate PDF ────────────────────────────────────────────────
        logger.info(f"[PDF] Generating report PDF")
        pdf_path = await generate_report_pdf(report_id, final_report)

        # ── Mark COMPLETED ───────────────────────────────────────────────
        from sqlalchemy import update
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(
                status=ReportStatus.COMPLETED,
                vulnerability_score=float(cvs),
                risk_level=risk_level,
                top_issues=top_issues_str,
                pdf_path=pdf_path,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.execute(stmt)
        await db.commit()

        logger.info(
            f"[PIPELINE] ✅ Completed report_id={report_id} | "
            f"CVS={cvs} | Risk={risk_level_str} | PDF={pdf_path}"
        )

    except Exception as e:
        logger.error(f"[PIPELINE] ❌ Failed report_id={report_id}: {e}", exc_info=True)
        await _update_report_status(db, report_id, ReportStatus.FAILED)
        raise


async def _update_report_status(
    db: AsyncSession, report_id: int, status: ReportStatus
) -> None:
    from sqlalchemy import update
    stmt = update(Report).where(Report.id == report_id).values(status=status)
    await db.execute(stmt)
    await db.commit()


async def _save_agent_output(
    db: AsyncSession, report_id: int, field_name: str, data: dict
) -> None:
    from sqlalchemy import update
    stmt = (
        update(Report)
        .where(Report.id == report_id)
        .values(**{field_name: json.dumps(data, ensure_ascii=False)})
    )
    await db.execute(stmt)
    await db.commit()
