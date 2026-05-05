import streamlit as st
import asyncio
import sys
import os
import types
import json
import time
import importlib.util

# =====================================================================
# 1. SETUP DE L'ENVIRONNEMENT VIRTUEL (Mocking)
# On recrée l'arborescence "backend" en mémoire pour que les imports
# "from ..config import settings" de tes agents fonctionnent parfaitement.
# =====================================================================

# Faux module backend
if "backend" not in sys.modules:
    sys.modules["backend"] = types.ModuleType("backend")

# Faux module backend.config
if "backend.config" not in sys.modules:
    config_mod = types.ModuleType("backend.config")
    class MockSettings:
        ANTHROPIC_API_KEY = "offline-mock-key"
        SILOBREAK_API_KEY = ""
        SILOBREAK_BASE_URL = "http://mock"
    config_mod.settings = MockSettings()
    sys.modules["backend.config"] = config_mod

# Faux module backend.agents
if "backend.agents" not in sys.modules:
    sys.modules["backend.agents"] = types.ModuleType("backend.agents")

# Fausse librairie httpx (pour agent_silobreak)
if "httpx" not in sys.modules:
    fake_httpx = types.ModuleType("httpx")
    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def get(self, *args, **kwargs):
            class MockResponse:
                def raise_for_status(self): pass
                def json(self): return {"status": "mocked", "results": []}
            return MockResponse()
    fake_httpx.AsyncClient = MockAsyncClient
    fake_httpx.HTTPError = Exception
    sys.modules["httpx"] = fake_httpx

# Fausse librairie anthropic (pour tous les agents)
if "anthropic" not in sys.modules:
    class MockMessageContent:
        def __init__(self, text): self.text = text
    class MockMessageResponse:
        def __init__(self, text): self.content = [MockMessageContent(text)]
    class MockMessagesAPI:
        def create(self, model, max_tokens, system, messages):
            time.sleep(0.8) # Simule le temps de traitement LLM (800ms)
            if "Agent 1" in system:
                return MockMessageResponse('{"company": "Cible Test", "total_signals": 2, "signals": [{"category": "CAT1", "severity": 4, "summary": "Sanction OFAC simulée"}], "highest_severity": 4, "triage_summary": "Triage hors-ligne réussi."}')
            elif "Agent 2" in system:
                return MockMessageResponse('{"agent": "Legal Agent", "legal_risk_score": 85, "recommendation": "CAUTION", "key_risk_flags": ["Sanction OFAC"]}')
            elif "Agent 3" in system:
                return MockMessageResponse('{"agent": "Executive Agent", "combined_score": 40, "recommendation": "MONITOR", "key_risk_flags": []}')
            elif "Agent 4" in system:
                return MockMessageResponse('{"agent": "Operations Agent", "combined_score": 90, "recommendation": "AVOID", "key_risk_flags": ["Cyberattaque majeure"]}')
            elif "Agent 5" in system:
                return MockMessageResponse('{"overall_evidence_quality": "HIGH", "score_validation": {"legal_score_validated": 85, "executive_score_validated": 40, "operations_score_validated": 90}, "verified_top_issues": ["Sanction OFAC"]}')
            elif "Agent 6" in system:
                return MockMessageResponse('{"risk_level": "HIGH", "decision_intelligence": "AVOID", "executive_summary": "Analyse exécutée hors-ligne.", "top_issues": ["Sanction OFAC", "Cyberattaque"]}')
            return MockMessageResponse('{}')
            
    class MockAnthropicClient:
        def __init__(self, api_key=None): self.messages = MockMessagesAPI()
        
    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MockAnthropicClient
    sys.modules["anthropic"] = fake_anthropic

# =====================================================================
# 2. CHARGEMENT CHIRURGICAL DES AGENTS
# On charge les fichiers du dossier courant en leur faisant croire
# qu'ils appartiennent au package "backend.agents"
# =====================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))

def load_agent(module_name):
    file_path = os.path.join(current_dir, f"{module_name}.py")
    if not os.path.exists(file_path):
        st.error(f"❌ Fichier introuvable : {module_name}.py dans le dossier {current_dir}")
        st.stop()
        
    # On assigne manuellement le fichier au namespace "backend.agents.XXX"
    spec = importlib.util.spec_from_file_location(f"backend.agents.{module_name}", file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"backend.agents.{module_name}"] = mod
    spec.loader.exec_module(mod)
    return mod

# Chargement sécurisé
agent_silobreak = load_agent("agent_silobreak")
agent_legal = load_agent("agent_legal")
agent_executive = load_agent("agent_executive")
agent_operations = load_agent("agent_operations")
agent_evidence = load_agent("agent_evidence")
agent_orchestrator = load_agent("agent_orchestrator")

# =====================================================================
# 3. INTERFACE STREAMLIT
# =====================================================================
st.set_page_config(page_title="BNP Paribas - Testeur Agents", page_icon="🏦", layout="wide")
st.title("🏦 Plateforme Adverse News - Testeur Hors-Ligne")
st.markdown("Ce sas de test exécute tes fichiers locaux. Les appels API vers Anthropic et Silobreak sont interceptés et simulés.")

company_name = st.text_input("Nom de l'entité à analyser", value="BNP Partner (Test Local)")
run_btn = st.button("🚀 Lancer le pipeline complet", type="primary")

async def run_pipeline():
    try:
        # Agent 1
        with st.status("🕵️‍♂️ Agent 1 : Triage (Silobreak Mock)...", expanded=True) as s1:
            triage_data = await agent_silobreak.run_silobreak_agent(company_name, "test.com")
            st.json(triage_data, expanded=False)
            s1.update(label="✅ Agent 1 terminé", state="complete", expanded=False)

        # Agents 2, 3, 4
        with st.status("🧠 Agents 2, 3, 4 : Analyses par piliers (Parallèle)...", expanded=True) as s234:
            legal_analysis, executive_analysis, operations_analysis = await asyncio.gather(
                agent_legal.run_legal_agent(company_name, triage_data),
                agent_executive.run_executive_agent(company_name, triage_data),
                agent_operations.run_operations_agent(company_name, triage_data)
            )
            c1, c2, c3 = st.columns(3)
            with c1: st.write("**Légal (35%)**"); st.json(legal_analysis, expanded=False)
            with c2: st.write("**Exécutif (20%)**"); st.json(executive_analysis, expanded=False)
            with c3: st.write("**Opérations (30%)**"); st.json(operations_analysis, expanded=False)
            s234.update(label="✅ Agents 2, 3, 4 terminés", state="complete", expanded=False)

        # Agent 5
        with st.status("⚖️ Agent 5 : Fact-Checker (Evidence)...", expanded=True) as s5:
            evidence_validation = await agent_evidence.run_evidence_agent(
                company_name, triage_data, legal_analysis, executive_analysis, operations_analysis
            )
            st.json(evidence_validation, expanded=False)
            s5.update(label="✅ Agent 5 terminé", state="complete", expanded=False)

        # Agent 6
        with st.status("📊 Agent 6 : Orchestrateur (Synthèse)...", expanded=True) as s6:
            final_report = await agent_orchestrator.run_orchestrator_agent(
                company_name, "test.com", triage_data, legal_analysis, executive_analysis, operations_analysis, evidence_validation
            )
            s6.update(label="✅ Agent 6 terminé", state="complete", expanded=False)

        # RÉSULTAT FINAL
        st.success("🎉 Exécution de la logique métier terminée avec succès !")
        
        # Le calcul de ton Orchestrateur prend le relais ici :
        score = final_report.get("cyber_vulnerability_score", 0)
        risk = final_report.get("risk_level", "UNKNOWN")
        
        st.markdown(f"""
        <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #333;">
            <h2 style="margin:0;">Score de Vulnérabilité (CVS) : <span style="color:#00e676; font-size:40px;">{score}/100</span></h2>
            <h3 style="margin:0;">Niveau de risque : {risk}</h3>
            <p style="margin-top:10px; font-size:16px;"><em>Vérification du calcul mathématique (Ligne 118 agent_orchestrator) : (85*0.35) + (40*0.20) + (90*0.30) + 5 = 70</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Structure JSON Finale")
        st.json(final_report)

    except Exception as e:
        st.error(f"❌ Erreur critique lors de l'exécution : {str(e)}")
        st.exception(e)

if run_btn:
    asyncio.run(run_pipeline())
