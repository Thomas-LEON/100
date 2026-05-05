# ============================================================
# backend/agents/agent_legal.py
# Agent 2 — Legal & Integrity Agent (LLM Expert)
#
# Specializes in CAT1 (Regulatory/Legal) and CAT2 (Financial
# Crime / AML / KYC / Fraud) signals from triage output.
# ============================================================
import json
import anthropic
from datetime import datetime, timezone
from typing import Optional

from ..config import settings


LEGAL_SYSTEM_PROMPT = """
You are Agent 2 — the Legal & Integrity Specialist for BNP Paribas's
Adverse News Platform. You are an expert in:

CATEGORY 1 — Regulatory & Legal Enforcement:
- Government enforcement actions (SEC, CFTC, NYDFS, FCA, AMF, ECB, OFAC)
- Fines, settlements, consent orders
- License revocations, suspensions, banking charter issues
- Class-action lawsuits, IP disputes, material breach of contract
- Ongoing judicial proceedings

CATEGORY 2 — Financial Crime & Integrity:
- AML/KYC failures (OFAC sanctioned entities, FATF greylists)
- Terrorist financing, darknet market connections
- Fraud: market manipulation, misleading investors, commingling funds
- Internal control deficiencies, deficient compliance programs
- Internal audit findings, whistleblower disclosures

YOUR TASK:
1. Analyze the provided signals (CAT1 and CAT2 from triage)
2. Assess severity, regulatory impact, and BNP Paribas exposure risk
3. Identify if this entity presents a direct counterparty risk
4. Quantify financial penalty exposure if known
5. Rate overall Legal & Integrity risk on scale 0-100

OUTPUT ONLY valid JSON — no markdown, no commentary outside JSON.

OUTPUT FORMAT:
{
  "agent": "Legal & Integrity Agent",
  "company": "...",
  "analyzed_signals": 5,
  "cat1_findings": [
    {
      "signal_id": "SIG-001",
      "type": "Regulatory Fine",
      "regulator": "CFTC",
      "date": "2023-06-15",
      "financial_penalty_usd": 4350000000,
      "status": "settled",
      "severity": 5,
      "bnp_exposure": "HIGH",
      "summary": "..."
    }
  ],
  "cat2_findings": [...],
  "key_risk_flags": ["AML non-compliance", "OFAC sanctions exposure"],
  "legal_risk_score": 85,
  "risk_narrative": "Two-paragraph expert narrative on legal and integrity risk...",
  "recommendation": "AVOID | CAUTION | MONITOR | CLEAR",
  "analyst_notes": "..."
}
"""


async def run_legal_agent(
    company_name: str,
    triage_data: dict,
) -> dict:
    """
    Agent 2: Deep-dive into legal, regulatory, and financial crime signals.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Filter only CAT1 and CAT2 signals
    all_signals = triage_data.get("signals", [])
    relevant_signals = [
        s for s in all_signals
        if s.get("category") in ("CAT1", "CAT2")
    ]

    user_message = f"""
Perform Legal & Integrity Analysis for: {company_name}
Analysis Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

Triage Summary: {triage_data.get("triage_summary", "N/A")}

Relevant Signals (CAT1 + CAT2):
{json.dumps(relevant_signals, indent=2)}

All Signals Count: {triage_data.get("total_signals", 0)}
Highest Severity Observed: {triage_data.get("highest_severity", 0)}

Analyze these signals deeply. If relevant signals list is empty but the
company is known to you (e.g., Binance, FTX, etc.), use your training
knowledge to identify legal and integrity issues since 2020. Mark such
findings as verified: false.

Produce a thorough Legal & Integrity risk assessment in the required JSON format.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=LEGAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return _parse_agent_response(response.content[0].text, "Legal & Integrity Agent", company_name)


def _parse_agent_response(raw_text: str, agent_name: str, company: str) -> dict:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        raw_text = parts[1] if len(parts) > 1 else raw_text
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "agent": agent_name,
            "company": company,
            "error": "JSON parse failed",
            "legal_risk_score": 0,
            "_raw": raw_text[:500],
        }
