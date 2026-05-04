"""
Code Execution Engine
Safely executes user-submitted code in a controlled subprocess with
timeout and output capture.
"""

import subprocess
import tempfile
import os
import time
import sys
from pathlib import Path
from models.schemas import ExecutionResult
from engines.model_router import get_task_model


# Maximum execution time in seconds
MAX_EXECUTION_TIME = 10

# Blocked imports / keywords for basic safety
BLOCKED_KEYWORDS = [
    "os.system", "subprocess", "shutil.rmtree",
    "os.remove", "os.rmdir", "os.unlink",
    "__import__", "eval(", "exec(",
    "open('/etc", "open('C:\\\\Windows",
]


def _basic_safety_check(code: str) -> str | None:
    """
    Performs a rudimentary safety check on the submitted code.
    Returns an error message string if unsafe, None otherwise.
    """
    for keyword in BLOCKED_KEYWORDS:
        if keyword in code:
            return f"Blocked: potentially unsafe operation detected ({keyword})"
    return None


def _fallback_cloud_execute(code: str, language: str) -> ExecutionResult:
    import json
    import time
    from openai import OpenAI
    import os

    start_time = time.perf_counter()
    api_key = os.environ.get("NVIDIA_API_KEY")

    if not api_key:
        return ExecutionResult(
            success=False, 
            stdout="[Execution Simulator Skipped]\nNVIDIA_API_KEY required for cloud simulated execution.", 
            stderr="", 
            return_code=-1, 
            execution_time_ms=0.0
        )

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        prompt = f"""You are a perfect execution environment for {language}.
I will provide you with a code snippet. You must act as the standard output terminal.
Do not provide any explanations, markdown, or chat text. 
Output ONLY the exact string that would be printed to stdout if this code were successfully compiled and executed.
If the code seems to have a syntax error, simply output 'SyntaxError'.

Code:
{code}"""

        completion = client.chat.completions.create(
            model=get_task_model("execution_fallback", "meta/llama-3.1-8b-instruct"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
        )
        
        stdout_simulated = completion.choices[0].message.content.strip()
        if stdout_simulated.startswith("```"):
            stdout_simulated = "\n".join(stdout_simulated.split("\n")[1:-1])

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        out_msg = f"[Executed via Deep LLM Simulator ({language} runtime missing)]\n" + stdout_simulated
        
        return ExecutionResult(
            success=True,
            stdout=out_msg[:50_000],
            stderr="",
            execution_time_ms=round(elapsed_ms, 2),
            return_code=0
        )
    except Exception as e:
        friendly_msg = f"Local compilation environment for '{language}' could not be located.\nAI Simulator fallback failed: {str(e)}."
        return ExecutionResult(
            success=False, 
            stdout="[Execution Skipped]\n" + friendly_msg, 
            stderr="", 
            return_code=0, 
            execution_time_ms=0.0
        )

def execute_code(code: str, language: str = "python") -> ExecutionResult:
    """
    Execute the submitted code in an isolated subprocess.
    Returns an ExecutionResult with stdout, stderr, timing, etc.
    """
    # Safety gate
    safety_error = _basic_safety_check(code)
    if safety_error:
        return ExecutionResult(success=False, stderr=safety_error, return_code=-1)

    # Determine file extension and execution command
    ext_map = {
        "python": ".py",
        "javascript": ".js",
        "php": ".php",
        "c": ".c",
        "cpp": ".cpp",
        "java": ".java"
    }

    if language not in ext_map:
        return ExecutionResult(success=False, stderr=f"Language '{language}' is not supported yet.", return_code=-1)

    tmp_dir = tempfile.mkdtemp(prefix="coderun_")
    safe_lang_filename = "Main.java" if language == "java" else f"user_code{ext_map[language]}"
    code_file = os.path.join(tmp_dir, safe_lang_filename)
    exe_file = os.path.join(tmp_dir, "out.exe" if os.name == "nt" else "a.out")

    try:
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        start_time = time.perf_counter()

        if language == "c":
            comp = subprocess.run(["gcc", code_file, "-o", exe_file], capture_output=True, text=True, cwd=tmp_dir)
            if comp.returncode != 0:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return ExecutionResult(success=False, stderr=f"Compilation Error:\n{comp.stderr}", execution_time_ms=round(elapsed_ms, 2), return_code=comp.returncode)
            cmd = [exe_file]
        elif language == "cpp":
            comp = subprocess.run(["g++", code_file, "-o", exe_file], capture_output=True, text=True, cwd=tmp_dir)
            if comp.returncode != 0:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return ExecutionResult(success=False, stderr=f"Compilation Error:\n{comp.stderr}", execution_time_ms=round(elapsed_ms, 2), return_code=comp.returncode)
            cmd = [exe_file]
        elif language == "python":
            cmd = [sys.executable, "-u", code_file]
        elif language == "javascript":
            cmd = ["node", code_file]
        elif language == "php":
            cmd = ["php", code_file]
        elif language == "java":
            cmd = ["java", code_file]
        else:
            cmd = [sys.executable, "-u", code_file]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_EXECUTION_TIME,
            cwd=tmp_dir,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ExecutionResult(
            success=(result.returncode == 0),
            stdout=result.stdout[:50_000],
            stderr=result.stderr[:50_000],
            execution_time_ms=round(elapsed_ms, 2),
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(success=False, stderr=f"Execution timed out after {MAX_EXECUTION_TIME} seconds.", return_code=-1, execution_time_ms=MAX_EXECUTION_TIME * 1000)
    except FileNotFoundError:
        return _fallback_cloud_execute(code, language)
    except Exception as exc:
        return ExecutionResult(success=False, stderr=f"Execution error: {str(exc)}", return_code=-1)
    finally:
        try:
            os.remove(code_file)
            if language in ("c", "cpp") and os.path.exists(exe_file):
                os.remove(exe_file)
            os.rmdir(tmp_dir)
        except OSError:
            pass
