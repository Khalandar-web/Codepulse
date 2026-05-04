"""
White-Box Data Flow Testing — Detects unused, undefined, or misused variables.
"""

import json
import os
from openai import OpenAI


def run_data_flow_tests(code: str, language: str) -> dict:
    """Analyze variable definitions, uses, and kills to find data flow anomalies."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a White-Box Data Flow Testing Engine for {language}.
Analyze the code for data flow anomalies:
- Variables defined but never used (du anomaly)
- Variables used before definition (ud anomaly)
- Variables redefined without being used (dd anomaly)
- Variables that may hold stale/incorrect values

Generate exactly 3 test scenarios that expose these anomalies.
Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_dataflow_...", "category": "Data Flow", "passed": true, "input_data": "...", "actual": "...", "message": "..."}}
  ],
  "anomalies": ["description of each anomaly found"],
  "summary": "Data flow analysis summary"
}}
No markdown.

Code:
{code}"""
        comp = client.chat.completions.create(
            model="qwen/qwen2.5-coder-32b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=2048,
        )
        res = comp.choices[0].message.content.strip()
        if res.startswith("```"): res = "\n".join(res.split("\n")[1:-1])
        if res.lower().startswith("json"): res = res[4:].strip()
        return json.loads(res)
    except Exception as e:
        return {"tests": [], "summary": f"Data flow test error: {str(e)}", "error": True}
