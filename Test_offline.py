import streamlit as st
import asyncio
import sys
import os
import types
import json
import time

# =====================================================================
# 🛠️ MOCKING : SIMULATION DE L'API ANTHROPIC ET DE LA CONFIGURATION
# =====================================================================

# 1. On simule la config locale
if "backend" not in sys.modules:
    sys.modules["backend"] = types.ModuleType("backend")
if "backend.config" not in sys.modules:
    config_mod = types.ModuleType("backend.config")
    class MockSettings:
        ANTHROPIC_API_KEY = "mocked-key"
        SILOBREAK_API_KEY = ""
        SILOBREAK_BASE_URL = ""
    config_mod.settings = MockSettings()
    sys.modules["backend.config"] = config_mod

if "backend.agents" not in sys.modules:
    agents_mod = types.ModuleType("backend.agents")
    agents_mod.__path__ = [os.path.dirname(os.path.abspath(__file__))]
    sys.modules["backend.agents"] = agents_mod

# 2. On simule la librairie Anthropic entière (pas besoin d'internet !)
class MockMessageContent:
    def __init__(self, text):
        self.text = text

class MockMessageResponse:
    def __init__(self, text):
        self.content = [MockMessageContent(text)]

class MockMessagesAPI:
    def create(self, model, max_tokens, system, messages):
        # On lit le prompt système pour savoir quel agent est en train de "parler"
        # et on renvoie un JSON simulé correspondant à ce que Claude aurait généré.
        time.sleep(1) # Simule un petit délai réseau de 1 sec
        
        if "Agent 1" in system:
            return MockMessageResponse(json.dumps({
                "company": "BNP Paribas Partner (Test)",
                "total_signals": 3,
                "signals": [
                    {"category": "CAT1", "severity": 4, "summary": "Amende régulatoire (Simulée)"},
                    {"category": "CAT4", "severity": 5, "summary": "Fuite de données en 2023"}
                ],
                "triage_summary": "Test: Signaux mockés avec succès.",
                "highest_severity": 5
            }))
        elif "Agent 2" in system:
            return MockMessageResponse(json.dumps({
                "agent": "Legal Agent",
                "legal_risk_score": 80,
                "recommendation": "CAUTION"
            }))
        elif "Agent 3" in system:
            return MockMessageResponse(json.dumps({
                "agent": "Executive Agent",
                "combined_score": 40,
                "recommendation": "MONITOR"
            }))
        elif "Agent 4" in system:
            return MockMessageResponse(json.dumps({
                "agent": "Operations Agent",
                "combined_score": 90,
                "recommendation": "AVOID"
            }))
        elif "Agent 5" in system:
            return MockMessageResponse(json.dumps({
                "overall_evidence_quality": "HIGH",
                "score_validation": {
                    "legal_score_validated": 80,
                    "executive_score_validated": 40,
                    "operations_score_validated": 90
                }
            }))
        elif "Agent 6" in system:
            # Astuce : Je ne mets PAS le "cyber_vulnerability_score" ici
            # pour forcer ton code Python (lignes 118-125 de agent_orchestrator)
            # à faire le calcul mathématique de fallback !
            return MockMessageResponse(json.dumps({
                "risk_level": "HIGH",
                "decision_intelligence": "AVOID",
                "executive_summary": "Ceci est un test hors-ligne. L'API d'Anthropic n'a pas été contactée. Le score a été calculé par la fonction de fallback Python.",
                "top_issues": ["Fuite de données simulée", "Risque Légal simulé"]
            }))
        
        return MockMessageResponse('{"error": "Agent non reconnu"}')

class MockAnthropicClient:
    def __init__(self, api_key=None):
        self.messages = MockMessagesAPI()

# On injecte la fausse librairie dans Python
if "anthropic" not in sys.modules:
    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MockAnthropicClient
    sys.modules["anthropic"] = fake_anthropic

# =====================================================================
# 📦 IMPORT DE TES AGENTS (Utiliseront le faux module Anthropic)
# =====================================================================
from backend.agents.agent_silobreak import run_silobreak_agent
from backend.agents.agent_legal import run_legal_agent
from backend.agents.agent_executive import run_executive_agent
from backend.agents.agent_operations import run_operations_agent
from backend.agents.agent_evidence import run_evidence_agent
from backend.agents.agent_orchestrator import run_orchestrator_agent

# =====================================================================
# 🎨 INTERFACE STREAMLIT
# =====================================================================
st.set_page_config(page_title="Testeur OFFLINE", page_icon="🔌", layout="wide")
st.title("🔌 Testeur de Pipeline (Mode OFFLINE)")
st.info("Ce mode intercepte les appels API et renvoie des données de test. Tu peux tester la logique métier sans aucune connexion.")

company_name = st.text_input("Nom de l'entreprise à tester", value="Test Corp")
run_btn = st.button("🚀 Lancer l'analyse (Mode Mock)", type="primary")

async def run_test():
    try:
        # Agent 1
        with st.status("🕵️‍♂️ Agent 1 : Triage (Mock)...", expanded=True) as s1:
            triage_data = await run_silobreak_agent(company_name, "test.com")
            st.json(triage_data, expanded=False)
            s1.update(label="✅ Agent 1 terminé", state="complete", expanded=False)

        # Agents 2, 3, 4
        with st.status("🧠 Agents 2, 3, 4 : Analyses (Parallèle Mock)...", expanded=True) as s234:
            legal_analysis, executive_analysis, operations_analysis = await asyncio.gather(
                run_legal_agent(company_name, triage_data),
                run_executive_agent(company_name, triage_data),
                run_operations_agent(company_name, triage_data)
            )
            c1, c2, c3 = st.columns(3)
            with c1: st.write("**Légal**"); st.json(legal_analysis, expanded=False)
            with c2: st.write("**Exécutif**"); st.json(executive_analysis, expanded=False)
            with c3: st.write("**Opérations**"); st.json(operations_analysis, expanded=False)
            s234.update(label="✅ Agents 2, 3, 4 terminés", state="complete", expanded=False)

        # Agent 5
        with st.status("⚖️ Agent 5 : Evidence (Mock)...", expanded=True) as s5:
            evidence_validation = await run_evidence_agent(
                company_name, triage_data, legal_analysis, executive_analysis, operations_analysis
            )
            st.json(evidence_validation, expanded=False)
            s5.update(label="✅ Agent 5 terminé", state="complete", expanded=False)

        # Agent 6
        with st.status("📊 Agent 6 : Orchestrateur...", expanded=True) as s6:
            final_report = await run_orchestrator_agent(
                company_name, "test.com", triage_data, legal_analysis, executive_analysis, operations_analysis, evidence_validation
            )
            s6.update(label="✅ Agent 6 terminé", state="complete", expanded=False)

        # RÉSULTAT
        st.success("🎉 Logique Python validée avec succès !")
        
        score = final_report.get("cyber_vulnerability_score", 0)
        risk = final_report.get("risk_level", "UNKNOWN")
        
        st.markdown(f"""
        <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin:0;">Score CVS Calculé : <span style="color:#00e676; font-size:40px;">{score}/100</span></h2>
            <h3 style="margin:0;">Niveau : {risk}</h3>
            <p style="margin-top:10px; font-size:16px;"><em>Vérification du calcul (80*0.35 + 40*0.2 + 90*0.3 + 5) = {round((80*0.35)+(40*0.2)+(90*0.3)+5)}</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("JSON Final Structuré")
        st.json(final_report)

    except Exception as e:
        st.error(f"❌ Erreur lors de l'exécution : {str(e)}")
        st.exception(e)

if run_btn:
    asyncio.run(run_test())
