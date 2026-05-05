import streamlit as st
import asyncio
import sys
import os
import types
import json
import time
import importlib.util

# =====================================================================
# 🛠️ MOCKING : SIMULATION DE LA CONFIG ET DES LIBRAIRIES EXTERNES
# =====================================================================

# 1. Fausse configuration (Satisfait les "from ..config import settings")
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

# 2. Fausse librairie HTTPX (Evite de devoir pip install httpx)
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

# 3. Fausse librairie Anthropic (Simule Claude offline)
if "anthropic" not in sys.modules:
    class MockMessageContent:
        def __init__(self, text): self.text = text
    class MockMessageResponse:
        def __init__(self, text): self.content = [MockMessageContent(text)]
    class MockMessagesAPI:
        def create(self, model, max_tokens, system, messages):
            time.sleep(1) # Simule le temps de calcul
            if "Agent 1" in system:
                return MockMessageResponse('{"company": "Cible Test", "total_signals": 2, "signals": [{"category": "CAT1", "severity": 4, "summary": "Amende régulatoire simulée"}], "highest_severity": 4, "triage_summary": "Signaux mockés avec succès."}')
            elif "Agent 2" in system:
                return MockMessageResponse('{"agent": "Legal Agent", "legal_risk_score": 85, "recommendation": "CAUTION"}')
            elif "Agent 3" in system:
                return MockMessageResponse('{"agent": "Executive Agent", "combined_score": 40, "recommendation": "MONITOR"}')
            elif "Agent 4" in system:
                return MockMessageResponse('{"agent": "Operations Agent", "combined_score": 90, "recommendation": "AVOID"}')
            elif "Agent 5" in system:
                return MockMessageResponse('{"overall_evidence_quality": "HIGH", "score_validation": {"legal_score_validated": 85, "executive_score_validated": 40, "operations_score_validated": 90}}')
            elif "Agent 6" in system:
                # Je ne mets pas de cyber_vulnerability_score ici pour forcer ton algorithme de fallback en Python à faire le calcul !
                return MockMessageResponse('{"risk_level": "HIGH", "decision_intelligence": "AVOID", "executive_summary": "Test exécuté à 100% hors ligne en simulant les APIs externes.", "top_issues": ["Fuite de données", "Amende"]}')
            return MockMessageResponse('{}')
            
    class MockAnthropicClient:
        def __init__(self, api_key=None): self.messages = MockMessagesAPI()
        
    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = MockAnthropicClient
    sys.modules["anthropic"] = fake_anthropic

# =====================================================================
# 📦 CHARGEMENT CHIRURGICAL DES AGENTS (Contourne les erreurs d'imports)
# =====================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))

def load_agent(module_name, file_name):
    """Charge un module Python de force dans le bon namespace."""
    file_path = os.path.join(current_dir, file_name)
    if not os.path.exists(file_path):
        st.error(f"❌ Fichier introuvable : {file_name}. Mets ce script dans le même dossier que tes agents.")
        st.stop()
        
    spec = importlib.util.spec_from_file_location(f"backend.agents.{module_name}", file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"backend.agents.{module_name}"] = mod
    spec.loader.exec_module(mod)
    return mod

# On force l'import de tes fichiers
agent_silobreak = load_agent("agent_silobreak", "agent_silobreak.py")
agent_legal = load_agent("agent_legal", "agent_legal.py")
agent_executive = load_agent("agent_executive", "agent_executive.py")
agent_operations = load_agent("agent_operations", "agent_operations.py")
agent_evidence = load_agent("agent_evidence", "agent_evidence.py")
agent_orchestrator = load_agent("agent_orchestrator", "agent_orchestrator.py")

# =====================================================================
# 🎨 INTERFACE STREAMLIT
# =====================================================================
st.set_page_config(page_title="Testeur OFFLINE", page_icon="🔌", layout="wide")
st.title("🔌 Testeur de Pipeline (Mode OFFLINE)")
st.info("Ce mode intercepte les appels API et renvoie des données de test. Tu peux tester ta logique sans connexion.")

company_name = st.text_input("Nom de l'entreprise à tester", value="BNP Partner (Test)")
run_btn = st.button("🚀 Lancer l'analyse (Mode Mock)", type="primary")

async def run_test():
    try:
        # Agent 1
        with st.status("🕵️‍♂️ Agent 1 : Triage (Mock)...", expanded=True) as s1:
            triage_data = await agent_silobreak.run_silobreak_agent(company_name, "test.com")
            st.json(triage_data, expanded=False)
            s1.update(label="✅ Agent 1 terminé", state="complete", expanded=False)

        # Agents 2, 3, 4
        with st.status("🧠 Agents 2, 3, 4 : Analyses (Parallèle Mock)...", expanded=True) as s234:
            legal_analysis, executive_analysis, operations_analysis = await asyncio.gather(
                agent_legal.run_legal_agent(company_name, triage_data),
                agent_executive.run_executive_agent(company_name, triage_data),
                agent_operations.run_operations_agent(company_name, triage_data)
            )
            c1, c2, c3 = st.columns(3)
            with c1: st.write("**Légal**"); st.json(legal_analysis, expanded=False)
            with c2: st.write("**Exécutif**"); st.json(executive_analysis, expanded=False)
            with c3: st.write("**Opérations**"); st.json(operations_analysis, expanded=False)
            s234.update(label="✅ Agents 2, 3, 4 terminés", state="complete", expanded=False)

        # Agent 5
        with st.status("⚖️ Agent 5 : Evidence (Mock)...", expanded=True) as s5:
            evidence_validation = await agent_evidence.run_evidence_agent(
                company_name, triage_data, legal_analysis, executive_analysis, operations_analysis
            )
            st.json(evidence_validation, expanded=False)
            s5.update(label="✅ Agent 5 terminé", state="complete", expanded=False)

        # Agent 6
        with st.status("📊 Agent 6 : Orchestrateur...", expanded=True) as s6:
            final_report = await agent_orchestrator.run_orchestrator_agent(
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
            <p style="margin-top:10px; font-size:16px;"><em>Vérification de ta formule (85*0.35 + 40*0.2 + 90*0.3 + 5) = {round((85*0.35)+(40*0.2)+(90*0.3)+5)}</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("JSON Final Structuré")
        st.json(final_report)

    except Exception as e:
        st.error(f"❌ Erreur lors de l'exécution : {str(e)}")
        st.exception(e)

if run_btn:
    asyncio.run(run_test())
