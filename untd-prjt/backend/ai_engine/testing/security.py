"""
AI Security Testing — Detects potential vulnerabilities (SQL injection, XSS, etc.)
"""

import json
import os
from openai import OpenAI
from engines.model_router import get_task_model


def run_security_scan(code: str, language: str) -> dict:
    """AI-powered security vulnerability detection."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"vulnerabilities": [], "risk_level": "unknown", "summary": "NVIDIA_API_KEY required."}

    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are an Application Security Testing Engine for {language}.
Analyze the code for security vulnerabilities:
- SQL Injection risks
- Cross-Site Scripting (XSS)
- Command Injection
- Path Traversal
- Hardcoded credentials/secrets
- Insecure data handling
- Buffer overflow risks (for C/C++)

Return ONLY valid JSON:
{{
  "vulnerabilities": [
    {{"type": "SQL Injection", "severity": "critical/high/medium/low", "line": null, "description": "...", "fix": "..."}}
  ],
  "risk_level": "critical/high/medium/low/safe",
  "summary": "Overall security assessment"
}}
No markdown.

Code:
{code}"""
        comp = client.chat.completions.create(
            model=get_task_model("security", "nvidia/llama-3.1-nemotron-70b-instruct"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=2048,
        )
        res = comp.choices[0].message.content.strip()
        if res.startswith("```"): res = "\n".join(res.split("\n")[1:-1])
        if res.lower().startswith("json"): res = res[4:].strip()
        return json.loads(res)
    except Exception as e:
        return {"vulnerabilities": [], "risk_level": "unknown", "summary": f"Security scan error: {str(e)}"}
