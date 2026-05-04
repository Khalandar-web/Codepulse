"""
AI Manual Testing Simulator — Simulates exploratory QA tester behavior.
"""

import json
import os
from openai import OpenAI


def run_manual_test_simulation(code: str, language: str) -> dict:
    """Simulate a manual QA tester exploring the code."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"scenarios": [], "summary": "NVIDIA_API_KEY required."}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are an experienced Manual QA Tester for {language}.
Simulate exploratory testing of the code. Think like a real user would:
- Try unexpected inputs
- Test error messages
- Check edge cases a developer might miss
- Verify usability concerns

Generate exactly 3 manual test scenarios.
Return ONLY valid JSON:
{{
  "scenarios": [
    {{"name": "scenario_...", "description": "What the tester does", "expected": "What should happen", "actual": "What actually happens", "verdict": "pass/fail", "severity": "critical/high/medium/low"}}
  ],
  "summary": "Manual testing assessment"
}}
No markdown.

Code:
{code}"""
        comp = client.chat.completions.create(
            model="mistralai/mistral-large-2-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=2048,
        )
        res = comp.choices[0].message.content.strip()
        if res.startswith("```"): res = "\n".join(res.split("\n")[1:-1])
        if res.lower().startswith("json"): res = res[4:].strip()
        return json.loads(res)
    except Exception as e:
        return {"scenarios": [], "summary": f"Manual test error: {str(e)}"}
