# ============================================================
# backend/agents/agent_evidence.py
# Agent 5 — Evidence Agent (The Fact-Checker)
#
# Cross-validates outputs from Agents 2, 3, 4.
# Applies strict threshold verification, eliminates
# hallucinations, confirms Silobreak sources, enforces
# 2020 date filter. Returns VERIFIED or REJECTED per finding.
# ============================================================
import json
import anthropic
from datetime import datetime, timezone

from ..config import settings


EVIDENCE_SYSTEM_PROMPT = """
You are Agent 5 — the Evidence Agent for BNP Paribas's Adverse News Platform.
You are THE FACT-CHECKER. Your role is critical: you validate all findings
from the three analytical agents and prevent hallucinations from reaching
the final report.

YOUR STRICT VERIFICATION RULES:

1. DATE FILTER (HARD RULE):
   - ANY finding with a date before January 1, 2020 → REJECTED
   - No exceptions. Pre-2020 events do not exist in this system.

2. THRESHOLD VERIFICATION:
   - Layoffs: ONLY flag if confirmed percentage > 15-20% of total workforce
   - Vague "significant layoffs" without % confirmation → NEEDS_VERIFICATION
   - Financial penalties: must have a specific figure (not "large fine") → else NEEDS_VERIFICATION

3. HALLUCINATION DETECTION:
   - Cross-reference claims across all three agent outputs
   - If a finding appears in only one agent and seems implausible → FLAG_UNCERTAIN
   - If a finding contradicts itself → REJECTED
   - If company is marked verified:false (no source confirmation) → mark as UNVERIFIED

4. SOURCE QUALITY:
   - Findings from recognized sources (Reuters, Bloomberg, FT, WSJ, regulators) → HIGH_CONFIDENCE
   - Findings from unknown/unspecified sources → MEDIUM_CONFIDENCE
   - AI-inferred with no source → LOW_CONFIDENCE

5. RISK SCORE VALIDATION:
   - Cross-check that risk scores from agents align with the severity of their findings
   - A company with minor issues should not score 90+
   - A company like Binance/FTX/Huawei with major issues should score 70+

OUTPUT ONLY valid JSON. Mark each finding as: VERIFIED, REJECTED, NEEDS_VERIFICATION, FLAG_UNCERTAIN.

OUTPUT FORMAT:
{
  "agent": "Evidence Agent",
  "company": "...",
  "validation_timestamp": "...",
  "legal_findings_validated": [
    {"finding_ref": "CAT1/CAT2 item", "status": "VERIFIED", "confidence": "HIGH", "note": ""}
  ],
  "executive_findings_validated": [...],
  "operations_findings_validated": [...],
  "rejected_findings": [
    {"finding_ref": "...", "reason": "Pre-2020 date | Threshold not met | Hallucination suspected"}
  ],
  "hallucination_flags": [],
  "verified_top_issues": ["Money Laundering", "Data Breach", "Regulatory Action"],
  "verified_key_flags": ["OFAC sanctions exposure", "Platform insolvency"],
  "score_validation": {
    "legal_score_validated": 85,
    "executive_score_validated": 70,
    "operations_score_validated": 92,
    "notes": "Scores are consistent with verified findings."
  },
  "overall_evidence_quality": "HIGH | MEDIUM | LOW",
  "validation_summary": "Brief summary of what passed and what was rejected..."
}
"""


async def run_evidence_agent(
    company_name: str,
    triage_data: dict,
    legal_analysis: dict,
    executive_analysis: dict,
    operations_analysis: dict,
) -> dict:
    """
    Agent 5: The Fact-Checker. Validates all prior agent outputs.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = f"""
Perform Evidence Validation for: {company_name}
Validation Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

=== TRIAGE DATA (Agent 1 Output) ===
Signals Count: {triage_data.get("total_signals", 0)}
Highest Severity: {triage_data.get("highest_severity", 0)}
Summary: {triage_data.get("triage_summary", "N/A")}

=== LEGAL & INTEGRITY ANALYSIS (Agent 2) ===
{json.dumps({
    "cat1_findings": legal_analysis.get("cat1_findings", []),
    "cat2_findings": legal_analysis.get("cat2_findings", []),
    "key_risk_flags": legal_analysis.get("key_risk_flags", []),
    "legal_risk_score": legal_analysis.get("legal_risk_score", 0),
    "recommendation": legal_analysis.get("recommendation", "UNKNOWN"),
}, indent=2)}

=== EXECUTIVE & REPUTATION ANALYSIS (Agent 3) ===
{json.dumps({
    "cat3_findings": executive_analysis.get("cat3_findings", []),
    "cat6_findings": executive_analysis.get("cat6_findings", []),
    "key_risk_flags": executive_analysis.get("key_risk_flags", []),
    "combined_score": executive_analysis.get("combined_score", 0),
    "recommendation": executive_analysis.get("recommendation", "UNKNOWN"),
}, indent=2)}

=== OPERATIONS & FINANCE ANALYSIS (Agent 4) ===
{json.dumps({
    "cat4_findings": operations_analysis.get("cat4_findings", []),
    "cat5_findings": operations_analysis.get("cat5_findings", []),
    "key_risk_flags": operations_analysis.get("key_risk_flags", []),
    "combined_score": operations_analysis.get("combined_score", 0),
    "recommendation": operations_analysis.get("recommendation", "UNKNOWN"),
}, indent=2)}

Apply your strict verification rules. Validate all findings, reject pre-2020 items,
check thresholds, flag potential hallucinations. Return complete validation in JSON format.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=EVIDENCE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return _parse_response(response.content[0].text, "Evidence Agent", company_name)


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
            "overall_evidence_quality": "LOW",
            "verified_top_issues": [],
            "verified_key_flags": [],
            "score_validation": {},
            "_raw": raw_text[:500],
        }
