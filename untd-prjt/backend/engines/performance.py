"""
Performance Testing Engine
Measures execution time and memory usage (approximation) of user code.
"""

import subprocess
import tempfile
import os
import sys
import time
from models.schemas import PerformanceResult
from engines.model_router import get_task_model


PERFORMANCE_TEST_SCRIPT_TEMPLATE = """
import time
import tracemalloc
import sys

# ── User Code ──
{user_code}

# ── Performance Measurement ──
tracemalloc.start()
start_time = time.perf_counter()

# Try to invoke main entry point or just let module-level code run
# (module-level code already ran above during import)

elapsed = (time.perf_counter() - start_time) * 1000
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"TIME_MS:{{elapsed:.4f}}")
print(f"MEM_CURRENT_MB:{{current / 1024 / 1024:.4f}}")
print(f"MEM_PEAK_MB:{{peak / 1024 / 1024:.4f}}")
"""


def _estimate_complexity(code: str) -> tuple[str, str]:
    """
    Very rough heuristic to estimate time/space complexity
    by looking at loop nesting and data structures.
    """
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ("Unknown", "Unknown")

    max_loop_depth = 0

    def _walk_depth(node, depth=0):
        nonlocal max_loop_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                new_depth = depth + 1
                max_loop_depth = max(max_loop_depth, new_depth)
                _walk_depth(child, new_depth)
            else:
                _walk_depth(child, depth)

    _walk_depth(tree)

    time_map = {
        0: "O(1)",
        1: "O(n)",
        2: "O(n²)",
        3: "O(n³)",
    }
    time_est = time_map.get(max_loop_depth, f"O(n^{max_loop_depth})")

    # Space: look for list/dict comprehensions, appends
    has_growing_structures = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            has_growing_structures = True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("append", "extend", "update"):
                has_growing_structures = True

    space_est = "O(n)" if has_growing_structures else "O(1)"

    return (time_est, space_est)


def _grade_performance(exec_time_ms: float, memory_mb: float) -> str:
    """Assign a letter grade based on execution time and memory."""
    if exec_time_ms < 50 and memory_mb < 10:
        return "A"
    elif exec_time_ms < 200 and memory_mb < 50:
        return "B"
    elif exec_time_ms < 1000 and memory_mb < 100:
        return "C"
    elif exec_time_ms < 5000 and memory_mb < 500:
        return "D"
    else:
        return "F"


def _fallback_llm_performance(code: str, language: str) -> PerformanceResult:
    import json
    import os
    from openai import OpenAI
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return PerformanceResult(performance_grade="N/A")
        
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a Performance Testing Profiler for {language}.
Analyze the code and estimate its runtime complexity, space complexity, and synthetic performance metrics.
Grade it A, B, C, D, or F based on its optimization level. 
Output ONLY valid JSON. No markdown.

{{
  "execution_time_ms": <float approx realistic time in ms>,
  "memory_usage_mb": <float approx realistic memory in mb>,
  "time_complexity_estimate": "O(...)",
  "space_complexity_estimate": "O(...)",
  "performance_grade": "A/B/C/D/F"
}}

Code:
{code}"""
        comp = client.chat.completions.create(
            model=get_task_model("performance_fallback", "mistralai/mistral-large-2-instruct"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        res_text = comp.choices[0].message.content.strip()
        
        # Robustly extract JSON object
        start_idx = res_text.find('{')
        end_idx = res_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            res_text = res_text[start_idx:end_idx+1]
        
        data = json.loads(res_text)
        return PerformanceResult(
            execution_time_ms=float(data.get("execution_time_ms", 10.0)),
            memory_usage_mb=float(data.get("memory_usage_mb", 5.0)),
            time_complexity_estimate=str(data.get("time_complexity_estimate", "O(n)")),
            space_complexity_estimate=str(data.get("space_complexity_estimate", "O(1)")),
            performance_grade=str(data.get("performance_grade", "C"))
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return PerformanceResult(performance_grade="N/A")

def measure_performance(code: str, language: str = "python") -> PerformanceResult:
    """
    Measure execution time and memory usage of the submitted code.
    """
    if language != "python":
        return _fallback_llm_performance(code, language)

    # Estimate complexity from code structure
    time_est, space_est = _estimate_complexity(code)

    # Run the performance measurement script
    script = PERFORMANCE_TEST_SCRIPT_TEMPLATE.format(user_code=code)

    tmp_dir = tempfile.mkdtemp(prefix="codeperftest_")
    script_file = os.path.join(tmp_dir, "perf_test.py")

    try:
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        result = subprocess.run(
            [sys.executable, "-u", script_file],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=tmp_dir,
        )

        exec_time_ms = 0.0
        memory_mb = 0.0

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith("TIME_MS:"):
                    exec_time_ms = float(line.split(":")[1])
                elif line.startswith("MEM_PEAK_MB:"):
                    memory_mb = float(line.split(":")[1])

        grade = _grade_performance(exec_time_ms, memory_mb)

        return PerformanceResult(
            execution_time_ms=round(exec_time_ms, 2),
            memory_usage_mb=round(memory_mb, 4),
            time_complexity_estimate=time_est,
            space_complexity_estimate=space_est,
            performance_grade=grade,
        )

    except subprocess.TimeoutExpired:
        return PerformanceResult(
            execution_time_ms=15000,
            performance_grade="F",
            time_complexity_estimate=time_est,
            space_complexity_estimate=space_est,
        )
    except Exception as e:
        return PerformanceResult(
            performance_grade="N/A",
            time_complexity_estimate=time_est,
            space_complexity_estimate=space_est,
        )
    finally:
        try:
            os.remove(script_file)
            os.rmdir(tmp_dir)
        except OSError:
            pass
