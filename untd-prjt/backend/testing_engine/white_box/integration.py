"""
White-Box Integration Testing — Tests interactions between modules/functions.
"""

import json
import os
from openai import OpenAI


def run_integration_tests(code: str, language: str) -> dict:
    """Generate integration tests analyzing cross-function interactions."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a White-Box Integration Testing Engine for {language}.
Analyze the code and generate exactly 3 integration tests. Each test must:
- Test how multiple functions/modules interact with each other
- Verify data flow between components
- Check that calling function A's output as function B's input produces correct results

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_integration_...", "category": "Integration", "passed": true, "input_data": "...", "actual": "...", "message": "..."}}
  ],
  "summary": "Brief integration coverage summary"
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
        return {"tests": [], "summary": f"Integration test error: {str(e)}", "error": True}
