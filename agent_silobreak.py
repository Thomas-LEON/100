# ============================================================
# backend/agents/agent_silobreak.py
# Agent 1 — Silobreak Acquisition & Triage Agent
#
# Role: Connect to Silobreak OSINT/Threat Feed API and pull
# raw adverse news data for a given company. Filter to
# events >= 2020 only. Returns structured raw signal set.
# ============================================================
import json
import httpx
from datetime import datetime, timezone
from typing import Optional
import anthropic

from ..config import settings


SILOBREAK_SYSTEM_PROMPT = """
You are Agent 1 — the Silobreak Acquisition & Triage Agent for BNP Paribas's
Adverse News Platform. Your role is to process raw OSINT/threat intelligence
data about a company and perform initial triage.

RULES:
1. ONLY consider events/news dated January 2020 or later. Discard anything older.
2. Extract ALL adverse signals: regulatory, legal, financial crime, executive risk,
   operational failures, cyber incidents, reputational issues.
3. Classify each signal into one of 6 categories:
   - CAT1: Regulatory & Legal Enforcement (fines, lawsuits, license revocations)
   - CAT2: Financial Crime & Integrity (AML/KYC, fraud, sanctions)
   - CAT3: Executive & Key Person Risk (misconduct, controversy, conflicts)
   - CAT4: Operational & Security Risks (hacks, outages, data breaches)
   - CAT5: Financial Health & Stability (insolvency, mass layoffs >15-20%, valuation shocks)
   - CAT6: Ethical & Reputational Issues (ESG failures, toxic partnerships)
4. For each signal include: date, headline, source, category, severity (1-5), summary.
5. Output ONLY valid JSON — no markdown, no preamble.

OUTPUT FORMAT:
{
  "company": "Company Name",
  "domain": "domain.com",
  "data_sources": ["source1", "source2"],
  "total_signals": 12,
  "signals": [
    {
      "id": "SIG-001",
      "date": "2023-06-15",
      "category": "CAT2",
      "category_label": "Financial Crime & Integrity",
      "severity": 5,
      "headline": "...",
      "source": "Reuters",
      "source_url": "https://...",
      "summary": "...",
      "verified": true
    }
  ],
  "triage_summary": "Brief overview of what was found",
  "highest_severity": 5,
  "cutoff_applied": "2020-01-01",
  "triage_timestamp": "2026-04-05T14:30:00Z"
}
"""


async def run_silobreak_agent(
    company_name: str,
    domain: Optional[str] = None,
) -> dict:
    """
    Agent 1: Acquire and triage adverse news signals via Silobreak API.
    Falls back to Claude's knowledge if Silobreak is unavailable.
    """
    raw_data = await _fetch_from_silobreak(company_name, domain)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = f"""
Perform acquisition and triage for the following company:

Company Name: {company_name}
Domain: {domain or "unknown"}
Current Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

Raw data from Silobreak OSINT API:
{json.dumps(raw_data, indent=2)}

Analyze this data, apply the 2020 date filter, classify all adverse signals
into the 6 categories, and return the structured JSON output.
If Silobreak returned no data, use your training knowledge about this company
but clearly mark signals as verified: false.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SILOBREAK_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    # Clean potential markdown code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback structure if JSON parsing fails
        result = {
            "company": company_name,
            "domain": domain,
            "data_sources": ["Claude Knowledge Base"],
            "total_signals": 0,
            "signals": [],
            "triage_summary": f"Triage parsing error for {company_name}. Raw output stored.",
            "highest_severity": 0,
            "cutoff_applied": "2020-01-01",
            "triage_timestamp": datetime.now(timezone.utc).isoformat(),
            "_raw_output": raw_text,
        }

    return result


async def _fetch_from_silobreak(company_name: str, domain: Optional[str]) -> dict:
    """
    Attempt to fetch from Silobreak API.
    Returns mock data structure if API is unavailable (dev mode).
    """
    if not settings.SILOBREAK_API_KEY or settings.SILOBREAK_API_KEY == "your-silobreak-api-key":
        # Dev mode: return empty structure, Claude will use its knowledge
        return {
            "status": "dev_mode",
            "message": "Silobreak API not configured. Using Claude knowledge base.",
            "company": company_name,
            "domain": domain,
            "results": [],
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.SILOBREAK_BASE_URL}/search",
                headers={
                    "Authorization": f"Bearer {settings.SILOBREAK_API_KEY}",
                    "Content-Type": "application/json",
                },
                params={
                    "query": company_name,
                    "domain": domain,
                    "date_from": "2020-01-01",
                    "limit": 50,
                    "categories": "regulatory,legal,financial_crime,cyber,reputational",
                },
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {
            "status": "api_error",
            "error": str(e),
            "company": company_name,
            "results": [],
        }
