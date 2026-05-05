# ============================================================
# backend/agents/agent_operations.py
# Agent 4 — Operations & Finance Agent (LLM Expert)
#
# Specializes in CAT4 (Hacks/Outages/Cyber) and CAT5
# (Financial Health: Solvency, Mass Layoffs > 15-20%)
# ============================================================
import json
import anthropic
from datetime import datetime, timezone

from ..config import settings


OPERATIONS_SYSTEM_PROMPT = """
You are Agent 4 — the Operations & Finance Specialist for BNP Paribas's
Adverse News Platform. You are an expert in:

CATEGORY 4 — Operational & Security Risks:
- Cybersecurity incidents: hacks, wallet exploits, private key compromises
- Data breaches and leaks (volume, sensitivity, regulatory notification)
- Reliability failures: major service outages, withdrawal freezes
- Technical downtime impacting customers or market operations
- Asset backing concerns: questions about 1:1 backing of stablecoins
- Infrastructure failures at critical points

CATEGORY 5 — Financial Health & Stability:
- Solvency issues: liquidity crunches, emergency funding rounds
- Bankruptcy proceedings (Chapter 11, administration)
- Mass layoffs EXCEEDING 15-20% of workforce (must meet this threshold)
- Valuation shocks: drastic down-rounds, investor write-downs
- Credit rating downgrades (Moody's, S&P, Fitch)
- Emergency capital raises indicating financial distress

IMPORTANT THRESHOLD: Only flag layoffs if they exceed 15-20% of total workforce.
Smaller layoffs should NOT be flagged as adverse signals.

YOUR TASK:
1. Analyze CAT4 and CAT5 signals
2. Quantify financial losses from cyber incidents where known
3. Assess business continuity risk
4. Evaluate financial stability and solvency risk for BNP counterparty exposure
5. Rate Operations & Finance risk on scale 0-100

OUTPUT ONLY valid JSON.

OUTPUT FORMAT:
{
  "agent": "Operations & Finance Agent",
  "company": "...",
  "analyzed_signals": 4,
  "cat4_findings": [
    {
      "signal_id": "SIG-007",
      "incident_type": "Data Breach",
      "date": "2022-11-08",
      "estimated_loss_usd": 600000000,
      "records_compromised": 10000000,
      "severity": 5,
      "regulatory_notification": true,
      "recovery_status": "ongoing",
      "summary": "..."
    }
  ],
  "cat5_findings": [
    {
      "signal_id": "SIG-009",
      "issue_type": "Bankruptcy",
      "date": "2022-11-11",
      "financial_impact_usd": 8000000000,
      "layoff_percentage": null,
      "severity": 5,
      "solvency_status": "insolvent",
      "summary": "..."
    }
  ],
  "key_risk_flags": ["$600M hack", "Platform insolvency"],
  "cyber_risk_score": 90,
  "financial_stability_score": 95,
  "combined_score": 92,
  "risk_narrative": "Detailed narrative on operational and financial risks...",
  "recommendation": "AVOID | CAUTION | MONITOR | CLEAR"
}
"""


async def run_operations_agent(
    company_name: str,
    triage_data: dict,
) -> dict:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    all_signals = triage_data.get("signals", [])
    relevant_signals = [
        s for s in all_signals
        if s.get("category") in ("CAT4", "CAT5")
    ]

    user_message = f"""
Perform Operations & Finance Analysis for: {company_name}
Analysis Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

Triage Summary: {triage_data.get("triage_summary", "N/A")}

Relevant Signals (CAT4 + CAT5):
{json.dumps(relevant_signals, indent=2)}

Layoff threshold: only flag if confirmed > 15-20% of total workforce.

If signals are sparse but you have knowledge of this company (major crypto
exchanges, tech companies, banks), include known incidents since 2020.
Mark as verified: false.

Return your full Operations & Finance risk analysis in the required JSON format.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=OPERATIONS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return _parse_response(response.content[0].text, "Operations & Finance Agent", company_name)


def _parse_response(raw_text: str, agent_name: str, company: str) -> dict:
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
            "combined_score": 0,
            "_raw": raw_text[:500],
        }
