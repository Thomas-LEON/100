# ============================================================
# backend/agents/agent_executive.py
# Agent 3 — Executive & Reputation Agent (LLM Expert)
#
# Specializes in CAT3 (Executive Risk) and CAT6 (Toxic
# Partnerships / Reputational Issues).
# ============================================================
import json
import anthropic
from datetime import datetime, timezone

from ..config import settings


EXECUTIVE_SYSTEM_PROMPT = """
You are Agent 3 — the Executive & Reputation Specialist for BNP Paribas's
Adverse News Platform. You are an expert in:

CATEGORY 3 — Executive & Key Person Risk:
- Personal misconduct: harassment, toxicity, personal legal trouble
- Public controversy: polarizing statements, social media crises
- Conflicts of interest: undisclosed stakes, self-dealing
- Distraction factors: CEOs launching unrelated ventures
- Leadership instability: sudden C-suite departures, boardroom conflicts
- Criminal investigations targeting executives personally

CATEGORY 6 — Ethical & Reputational Issues:
- Association with collapsed or fraudulent entities (FTX, Celsius, SVB, etc.)
- ESG failures: significant environmental criticism, energy/carbon controversies
- Sanctions violations: indirect business with high-risk jurisdictions
- Discriminatory practices, labor violations
- Greenwashing, misleading sustainability claims
- Toxic partnerships with sanctioned states or individuals

YOUR TASK:
1. Analyze CAT3 and CAT6 signals
2. Identify key executives at risk and assess personal liability
3. Evaluate reputational contagion risk for BNP Paribas as counterparty
4. Assess ESG/ethical alignment with BNP Paribas values
5. Rate Executive & Reputation risk on scale 0-100

OUTPUT ONLY valid JSON.

OUTPUT FORMAT:
{
  "agent": "Executive & Reputation Agent",
  "company": "...",
  "analyzed_signals": 3,
  "cat3_findings": [
    {
      "signal_id": "SIG-003",
      "executive_name": "John Doe",
      "executive_role": "CEO",
      "issue_type": "Fraud Investigation",
      "date": "2023-09-01",
      "severity": 4,
      "bnp_reputational_risk": "HIGH",
      "summary": "..."
    }
  ],
  "cat6_findings": [...],
  "key_risk_flags": ["Toxic partnership with sanctioned entity", "ESG controversy"],
  "executive_risk_score": 70,
  "esg_risk_score": 45,
  "combined_score": 60,
  "risk_narrative": "Expert narrative on executive and reputational risk...",
  "recommendation": "AVOID | CAUTION | MONITOR | CLEAR"
}
"""


async def run_executive_agent(
    company_name: str,
    triage_data: dict,
) -> dict:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    all_signals = triage_data.get("signals", [])
    relevant_signals = [
        s for s in all_signals
        if s.get("category") in ("CAT3", "CAT6")
    ]

    user_message = f"""
Perform Executive & Reputation Analysis for: {company_name}
Analysis Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

Triage Summary: {triage_data.get("triage_summary", "N/A")}

Relevant Signals (CAT3 + CAT6):
{json.dumps(relevant_signals, indent=2)}

If no signals are present but you have knowledge of this company (e.g., Binance,
Huawei, TikTok), include known executive controversies and reputational issues
since 2020. Mark as verified: false.

Assess leadership stability, executive misconduct, and ESG alignment.
Return your full analysis in the required JSON format.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=EXECUTIVE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return _parse_response(response.content[0].text, "Executive & Reputation Agent", company_name)


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
