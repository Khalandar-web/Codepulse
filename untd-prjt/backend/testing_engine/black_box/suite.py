"""
Black-Box Testing Suite
Consolidated prompt generation for ultra-fast performance.
"""

import json
import os
from openai import OpenAI
from engines.model_router import get_task_model

MODEL_NAME = get_task_model("blackbox", "ibm/granite-8b-code-instruct")

MAX_CODE_CHARS = 30000

def _truncate_code(code: str) -> str:
    """Truncate large project code to fit within LLM context limits."""
    if len(code) <= MAX_CODE_CHARS:
        return code
    truncated = code[:MAX_CODE_CHARS]
    last_boundary = truncated.rfind("\n--- ")
    if last_boundary > MAX_CODE_CHARS * 0.5:
        truncated = truncated[:last_boundary]
    return truncated + "\n\n# ... (remaining project files truncated for analysis) ..."

def run_blackbox_suite(code: str, language: str) -> dict:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"bva": {}, "ecp": {}, "decision_table": {}, "state_transition": {}, "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        analysis_code = _truncate_code(code)
        is_project = "--- " in code and code.count("--- ") > 1
        context_hint = (
            "This is a MULTI-FILE PROJECT. Focus on testing the application's external behavior and interfaces."
            if is_project
            else "This is a single code snippet."
        )
        prompt = f"""You are a High-Speed Black-Box Testing Engine for {language}.
{context_hint}
Analyze the code and generate test cases for ALL 4 black-box categories at once:
1. Boundary Value Analysis (BVA) (4 tests) - test edge/boundary values of inputs
2. Equivalence Class Partitioning (ECP) (4 tests) - test representative values from input partitions
3. Decision Table Testing (4 tests) - test combinations of conditions and actions
4. State Transition Testing (4 tests) - test state changes and transitions

For each test, SIMULATE what would happen if you ran it. Determine pass/fail based on your analysis.

Return ONLY valid JSON:
{{
  "bva": {{
    "tests": [ {{"name":"...", "category":"BVA", "passed":true, "input_data":"...", "actual":"...", "expected":"...", "message":"..."}} ],
    "summary": "..."
  }},
  "ecp": {{
    "tests": [ ... ],
    "summary": "..."
  }},
  "decision_table": {{
    "tests": [ ... ],
    "summary": "..."
  }},
  "state_transition": {{
    "tests": [ ... ],
    "summary": "..."
  }}
}}
No markdown. No explanation. Raw JSON only.
Code:
{analysis_code}"""
        
        comp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=4096,
        )
        res = _clean_json(comp.choices[0].message.content.strip())
        data = json.loads(res)
        return data
    except Exception as e:
        print("Blackbox Suite Error:", e)
        return {
            "bva": {"tests": [], "summary": "Error", "error": True},
            "ecp": {"tests": [], "summary": "Error", "error": True},
            "decision_table": {"tests": [], "summary": "Error", "error": True},
            "state_transition": {"tests": [], "summary": "Error", "error": True},
        }

def _clean_json(text: str) -> str:
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text
