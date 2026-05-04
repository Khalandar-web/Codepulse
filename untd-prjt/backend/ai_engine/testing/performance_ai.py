"""
AI Performance Testing — Predicts performance bottlenecks and optimization opportunities.
"""

import json
import os
from openai import OpenAI


def run_performance_analysis(code: str, language: str) -> dict:
    """AI-driven performance bottleneck detection and optimization suggestions."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"bottlenecks": [], "optimizations": [], "summary": "NVIDIA_API_KEY required."}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Performance Analysis Engine for {language}.
Analyze the code for performance issues:
- Identify algorithmic bottlenecks
- Detect unnecessary memory allocations
- Find redundant computations
- Suggest caching opportunities
- Identify I/O-bound vs CPU-bound patterns

Return ONLY valid JSON:
{{
  "bottlenecks": [
    {{"location": "line or function", "type": "algorithmic/memory/io", "description": "...", "impact": "high/medium/low"}}
  ],
  "optimizations": [
    {{"suggestion": "...", "expected_improvement": "...", "difficulty": "easy/medium/hard"}}
  ],
  "summary": "Performance assessment summary"
}}
No markdown.

Code:
{code}"""
        comp = client.chat.completions.create(
            model="mistralai/mistral-large-2-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=2048,
        )
        res = comp.choices[0].message.content.strip()
        if res.startswith("```"): res = "\n".join(res.split("\n")[1:-1])
        if res.lower().startswith("json"): res = res[4:].strip()
        return json.loads(res)
    except Exception as e:
        return {"bottlenecks": [], "optimizations": [], "summary": f"Performance analysis error: {str(e)}"}

if __name__ == "__main__":
    sample_code = "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr"
    print("Running performance AI on bubble sort algorithm...")
    result = run_performance_analysis(sample_code, "python")
    print(json.dumps(result, indent=2))
