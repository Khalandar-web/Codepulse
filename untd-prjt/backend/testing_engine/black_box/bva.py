"""
Black-Box BVA Testing — Boundary Value Analysis.
Tests extreme edges of input ranges.
"""

import json
import os
from openai import OpenAI


def run_bva_tests(code: str, language: str) -> dict:
    """Generate BVA tests targeting min, max, and boundary-edge inputs."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Black-Box Boundary Value Analysis (BVA) Testing Engine for {language}.
Analyze the code and generate exactly 4 BVA test cases. Each test must:
- Test the MINIMUM valid input boundary
- Test the MAXIMUM valid input boundary
- Test just BELOW the minimum (invalid)
- Test just ABOVE the maximum (invalid)

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_bva_...", "category": "BVA", "passed": true, "input_data": "...", "actual": "...", "message": "Why this boundary matters"}}
  ],
  "summary": "BVA coverage summary"
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
        return {"tests": [], "summary": f"BVA test error: {str(e)}", "error": True}
