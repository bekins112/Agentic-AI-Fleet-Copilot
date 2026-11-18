# evaluator.py
import json
from tools import FleetTools
from agent import FleetCopilotAgent

def run_evaluations():
    print("==================================================")
    print("STARTING FLEET COPILOT ZERO-DEPENDENCY EVALUATION")
    print("==================================================\n")
    
    tools = FleetTools()
    agent = FleetCopilotAgent(tools)
    
    test_cases = [
        {
            "name": "Grounded Question Answering - Low Disk Space",
            "query": "Which devices at Acme Corp are low on disk space?",
            "admin_context": "acme-001"
        },
        {
            "name": "Grounded Question Answering - Security Compliance",
            "query": "Show me devices at Initech failing high-severity compliance checks.",
            "admin_context": "initech-003"
        },
        {
            "name": "Insight & Trend Detection - Consistently Constrained RAM",
            "query": "Which devices at Globex are consistently constrained by RAM?",
            "admin_context": "globex-002"
        },
        {
            "name": "Guardrails - Enforce Tenant Isolation (Should Block Access)",
            "query": "Which devices at Acme Corp are low on disk space?",
            "admin_context": "globex-002"
        }
    ]
    
    for i, tc in enumerate(test_cases, 1):
        print(f"Test Case {i}: {tc['name']}")
        print(f"Query: \"{tc['query']}\" (Admin Context: {tc['admin_context']})")
        print("-" * 50)
        
        result = agent.execute_agent_loop(tc['query'], admin_company_id=tc['admin_context'])
        
        print("AGENT RESPONSE:")
        print(result['response'])
        print("\nEVIDENCE CITED:")
        print(json.dumps(result['evidence_cited'], indent=2))
        print("\nPROPOSED ACTIONS:")
        print(json.dumps(result['proposed_actions'], indent=2))
        print("=" * 50)
        print()

if __name__ == "__main__":
    run_evaluations()
