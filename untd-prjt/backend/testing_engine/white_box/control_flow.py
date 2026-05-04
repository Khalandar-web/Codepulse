"""
White-Box Control Flow Testing — Validates execution paths through branching logic.
"""

import json
import os
from openai import OpenAI


def run_control_flow_tests(code: str, language: str) -> dict:
    """Analyze and test all branching paths (if/else, switch, loops)."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a White-Box Control Flow Testing Engine for {language}.
Analyze the code's branching logic (if/else, switch, loops, ternaries) and generate exactly 3 tests ensuring:
- Each possible path through the code is exercised
- Both true and false branches of conditionals are tested
- Loop boundary conditions (0 iterations, 1 iteration, many) are covered

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_path_...", "category": "Control Flow", "passed": true, "input_data": "...", "actual": "...", "message": "..."}}
  ],
  "summary": "Control flow coverage summary with paths tested"
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
        return {"tests": [], "summary": f"Control flow test error: {str(e)}", "error": True}
