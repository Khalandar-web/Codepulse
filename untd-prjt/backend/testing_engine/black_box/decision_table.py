"""
Black-Box Decision Table Testing — Tests combinations of conditions and actions.
"""

import json
import os
from openai import OpenAI


def run_decision_table_tests(code: str, language: str) -> dict:
    """Generate decision table tests covering condition/action combinations."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Black-Box Decision Table Testing Engine for {language}.
Analyze the code and identify all conditions that affect the output.
Generate exactly 3 decision table test cases. Each test must:
- Combine different TRUE/FALSE states of identified conditions
- Verify the correct action/output for each combination
- Cover at least one impossible/conflicting combination

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_decision_...", "category": "Decision Table", "passed": true, "input_data": "Condition1=T, Condition2=F", "actual": "...", "message": "Expected action for this combination"}}
  ],
  "decision_table": [["Condition", "Rule1", "Rule2", "Rule3"]],
  "summary": "Decision table coverage summary"
}}
No markdown.

Code:
{code}"""
        comp = client.chat.completions.create(
            model="mistralai/mixtral-8x22b-instruct-v0.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=2048,
        )
        res = comp.choices[0].message.content.strip()
        if res.startswith("```"): res = "\n".join(res.split("\n")[1:-1])
        if res.lower().startswith("json"): res = res[4:].strip()
        return json.loads(res)
    except Exception as e:
        return {"tests": [], "summary": f"Decision table test error: {str(e)}", "error": True}
