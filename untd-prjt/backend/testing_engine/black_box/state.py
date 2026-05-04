"""
Black-Box State Transition Testing — Tests valid and invalid state transitions.
"""

import json
import os
from openai import OpenAI


def run_state_transition_tests(code: str, language: str) -> dict:
    """Generate state transition tests verifying valid/invalid state changes."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"tests": [], "summary": "NVIDIA_API_KEY required.", "error": True}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Black-Box State Transition Testing Engine for {language}.
Analyze the code and identify any stateful behavior (objects, flags, modes, counters).
Generate exactly 3 state transition test cases. Each test must:
- Define the initial state
- Apply an event/action
- Verify the resulting state is correct
- Include one invalid transition that should be rejected or cause an error

Return ONLY valid JSON:
{{
  "tests": [
    {{"name": "test_state_...", "category": "State Transition", "passed": true, "input_data": "initial_state -> event", "actual": "resulting_state", "message": "Transition description"}}
  ],
  "state_diagram": "Brief textual description of states and transitions",
  "summary": "State transition coverage summary"
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
        return {"tests": [], "summary": f"State transition test error: {str(e)}", "error": True}
