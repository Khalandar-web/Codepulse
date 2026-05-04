"""
White-Box Unit Testing — AI-driven unit test generation and simulation.
Auto-generates test cases targeting individual functions/methods.
"""

import json
import os
from openai import OpenAI
from models.schemas import TestCase


def run_unit_tests(code: str, language: str) -> dict:
    """Generate and simulate unit tests for extracted functions."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a White-Box Unit Testing Engine for {language}.
Analyze the code and generate exactly 4 unit tests. Each test must:
- Target a single function or logical unit
- Provide specific inputs and validate the expected output
- Include edge cases for boundary parameters

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_func_basic", "category": "Unit", "passed": true, "input_data": "...", "actual": "...", "message": "..."}}
  ],
  "summary": "Brief summary of unit test coverage"
}}
No markdown blocks.

Code:
{code}"""
        comp = client.chat.completions.create(
            model="qwen/qwen2.5-coder-32b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=2048,
        )
        res = _clean_json(comp.choices[0].message.content.strip())
        data = json.loads(res)
        return data
    except Exception as e:
        return {"tests": [], "summary": f"Unit test error: {str(e)}", "error": True}


def _clean_json(text: str) -> str:
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text
