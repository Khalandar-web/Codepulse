"""
AI Analysis Engine
Routes different analysis jobs to the most suitable model and runs them in
parallel to keep end-to-end latency low.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import OpenAI

from engines.model_router import get_profile_settings, get_task_model
from models.schemas import AIAnalysisResult, AIInsight


NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _get_client() -> Optional[OpenAI]:
    """Create an OpenAI-compatible client for NVIDIA API."""
    if not NVIDIA_API_KEY:
        return None
    return OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)


def _call_ai(prompt: str, system_prompt: str = "", model_name: str = "") -> str:
    """Make a single AI API call and return the response text."""
    client = _get_client()
    if not client:
        return "[AI analysis unavailable - NVIDIA_API_KEY not set]"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model_name or get_task_model("ai_logic", "meta/llama-3.1-70b-instruct"),
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
        )
        msg = response.choices[0].message
        content = msg.content
        if not content and hasattr(msg, "reasoning_content"):
            content = msg.reasoning_content
        return content or ""
    except Exception as exc:
        print(f"[AI Engine Error]: {exc}")
        return f"[AI call failed: {str(exc)}]"


SYSTEM_PROMPT = """You are an expert code reviewer and software testing specialist.
You analyze code for correctness, performance, security, and best practices.
Always respond in clear, structured JSON as requested."""


def _build_logic_prompt(code: str, language: str) -> str:
    return f"""Analyze the following {language} code for logical correctness, potential bugs, and code quality.

```{language}
{code}
```

Respond ONLY with a JSON object (no markdown fences) with these keys:
- \"logic_analysis\": string - A detailed paragraph analyzing the correctness of the code logic.
- \"inefficiencies\": list of strings - Each string describes an inefficiency found.
- \"optimizations\": list of strings - Each string is a concrete optimization suggestion.
- \"insights\": list of objects, each with keys: \"category\" (one of \"logic\",\"optimization\",\"security\",\"style\",\"testing\"), \"title\" (short), \"description\" (detailed), \"suggestion\" (actionable), \"severity\" (one of \"critical\",\"warning\",\"info\").
"""


def _build_testing_prompt(code: str, language: str) -> str:
    return f"""You are simulating a manual QA tester reviewing this {language} code.

```{language}
{code}
```

Think like a human tester:
- Identify unusual or unexpected scenarios a user might encounter.
- Predict failure cases and edge cases a human tester would try.
- Suggest testing strategies and specific test scenarios.

Respond ONLY with a JSON object (no markdown fences) with these keys:
- \"manual_testing_simulation\": string - A detailed paragraph simulating what a human QA tester would report.
- \"unusual_scenarios\": list of strings - Scenarios found.
- \"failure_predictions\": list of strings - Predicted failure cases.
- \"test_strategies\": list of strings - Recommended strategies.
"""


def _build_assessment_prompt(code: str, language: str) -> str:
    return f"""Provide an overall assessment of this {language} code in 2-3 sentences.
Rate it on a scale of 1-10 for: correctness, readability, efficiency, and best practices.

```{language}
{code}
```

Respond ONLY with a JSON object (no markdown fences) with:
- \"overall_assessment\": string - 2-3 sentence summary.
- \"scores\": object with keys \"correctness\", \"readability\", \"efficiency\", \"best_practices\" each mapping to an integer 1-10.
"""


def analyze_with_ai(code: str, language: str = "python", profile: str = "fast") -> AIAnalysisResult:
    """Perform profile-aware AI analysis on the submitted code."""
    settings = get_profile_settings(profile)
    jobs = []

    if settings.get("ai_logic"):
        jobs.append(("logic", _build_logic_prompt(code, language), get_task_model("ai_logic")))
    if settings.get("ai_manual_testing"):
        jobs.append(("testing", _build_testing_prompt(code, language), get_task_model("ai_manual_testing")))
    if settings.get("ai_assessment"):
        jobs.append(("assessment", _build_assessment_prompt(code, language), get_task_model("ai_assessment")))

    responses: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(len(jobs), 1)) as executor:
        future_map = {
            executor.submit(_call_ai, prompt, SYSTEM_PROMPT, model_name): job_name
            for job_name, prompt, model_name in jobs
        }
        for future, job_name in future_map.items():
            responses[job_name] = future.result()

    result = AIAnalysisResult()

    logic_response = responses.get("logic", "")
    if logic_response:
        try:
            logic_data = json.loads(_clean_json(logic_response))
            result.logic_analysis = logic_data.get("logic_analysis", "")
            result.inefficiencies = logic_data.get("inefficiencies", [])
            result.optimizations = logic_data.get("optimizations", [])
            for ins in logic_data.get("insights", []):
                result.insights.append(AIInsight(
                    category=ins.get("category", "logic"),
                    title=ins.get("title", ""),
                    description=ins.get("description", ""),
                    suggestion=ins.get("suggestion", ""),
                    severity=ins.get("severity", "info"),
                ))
        except (json.JSONDecodeError, AttributeError):
            result.logic_analysis = logic_response

    testing_response = responses.get("testing", "")
    if testing_response:
        try:
            testing_data = json.loads(_clean_json(testing_response))
            result.manual_testing_simulation = testing_data.get("manual_testing_simulation", "")
            for scenario in testing_data.get("unusual_scenarios", []):
                result.insights.append(AIInsight(
                    category="testing",
                    title="Unusual Scenario",
                    description=scenario,
                    severity="warning",
                ))
            for failure in testing_data.get("failure_predictions", []):
                result.insights.append(AIInsight(
                    category="testing",
                    title="Predicted Failure",
                    description=failure,
                    severity="warning",
                ))
        except (json.JSONDecodeError, AttributeError):
            result.manual_testing_simulation = testing_response

    assessment_response = responses.get("assessment", "")
    if assessment_response:
        try:
            assessment_data = json.loads(_clean_json(assessment_response))
            result.overall_assessment = assessment_data.get("overall_assessment", "")
            raw_scores = assessment_data.get("scores", {})
            if isinstance(raw_scores, dict):
                result.ai_scores = {k: int(v) for k, v in raw_scores.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, AttributeError, ValueError):
            result.overall_assessment = assessment_response

    return result


def _clean_json(text: str) -> str:
    """Remove markdown code fences if present in AI response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    return text.strip()
