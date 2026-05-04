"""
Black-Box ECP Testing — Equivalence Class Partitioning.
Divides inputs into valid/invalid equivalence classes.
"""

import json
import os
from openai import OpenAI


def run_ecp_tests(code: str, language: str) -> dict:
    """Generate ECP tests partitioning input domain into equivalence classes."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Black-Box Equivalence Class Partitioning (ECP) Testing Engine for {language}.
Analyze the code and generate exactly 4 ECP test cases. Each test must:
- Identify distinct equivalence classes of the input domain
- Pick one representative value from each class
- Cover: valid positive class, valid negative class, zero/empty class, invalid class

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_ecp_...", "category": "ECP", "passed": true, "input_data": "...", "actual": "...", "message": "Which equivalence class this represents"}}
  ],
  "summary": "ECP coverage summary"
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
        return {"tests": [], "summary": f"ECP test error: {str(e)}", "error": True}
