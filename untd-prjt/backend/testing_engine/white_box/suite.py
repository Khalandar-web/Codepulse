"""
White-Box Testing Suite
Consolidated prompt generation for ultra-fast performance.
"""

import json
import os
from openai import OpenAI
from engines.model_router import get_task_model

MODEL_NAME = get_task_model("whitebox", "ibm/granite-8b-code-instruct")

MAX_CODE_CHARS = 30000  # Truncate to avoid exceeding model context

def _truncate_code(code: str) -> str:
    """Truncate large project code to fit within LLM context limits."""
    if len(code) <= MAX_CODE_CHARS:
        return code
    # For multi-file projects, keep the first portion which has priority files
    truncated = code[:MAX_CODE_CHARS]
    # Try to cut at a file boundary
    last_boundary = truncated.rfind("\n--- ")
    if last_boundary > MAX_CODE_CHARS * 0.5:
        truncated = truncated[:last_boundary]
    return truncated + "\n\n# ... (remaining project files truncated for analysis) ..."

def run_whitebox_suite(code: str, language: str) -> dict:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"unit": {}, "integration": {}, "control_flow": {}, "data_flow": {}, "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        analysis_code = _truncate_code(code)
        is_project = "--- " in code and code.count("--- ") > 1
        context_hint = (
            "This is a MULTI-FILE PROJECT. Focus on the most important source files and their interactions."
            if is_project
            else "This is a single code snippet."
        )
        prompt = f"""You are a High-Speed White-Box Testing Engine for {language}.
{context_hint}
Analyze the code and generate test cases for ALL 4 white-box categories at once:
1. Unit Tests (4 tests) - test individual functions/methods
2. Integration Tests (4 tests) - test how modules/components work together
3. Control Flow Tests (4 tests) - test branches, loops, conditionals
4. Data Flow Tests (4 tests) - test variable definitions, uses, and data transformations

For each test, SIMULATE what would happen if you ran it. Determine pass/fail based on your analysis.

Return ONLY valid JSON:
{{
  "unit": {{
    "tests": [ {{"name":"...", "category":"Unit", "passed":true, "input_data":"...", "actual":"...", "expected":"...", "message":"..."}} ],
    "summary": "..."
  }},
  "integration": {{
    "tests": [ ... ],
    "summary": "..."
  }},
  "control_flow": {{
    "tests": [ ... ],
    "summary": "..."
  }},
  "data_flow": {{
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
        print("Whitebox Suite Error:", e)
        return {
            "unit": {"tests": [], "summary": "Error", "error": True},
            "integration": {"tests": [], "summary": "Error", "error": True},
            "control_flow": {"tests": [], "summary": "Error", "error": True},
            "data_flow": {"tests": [], "summary": "Error", "error": True},
        }

def _clean_json(text: str) -> str:
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text
