"""
AI-Powered Code Analysis & Testing Platform - Backend API
FastAPI application that orchestrates all analysis engines and serves the frontend.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parent / ".env")

from routers import auth
from ai_engine.testing.security import run_security_scan
from engines.ai_engine import analyze_with_ai
from engines.execution import execute_code
from engines.model_router import DEFAULT_PROFILE, get_profile_settings, normalize_profile
from engines.performance import measure_performance
from engines.project.loader import extract_project
from engines.project.process_manager import terminate_all, list_active, terminate_process
from engines.project.runner import run_project
from engines.static_analysis import analyze_code
from engines.testing import run_tests
from models.schemas import (
    AnalysisReport,
    BlackBoxResult,
    CodeSubmission,
    ExecutionResult,
    RegressionResult,
    SecurityResult,
    TestCase,
    TestingResult,
    WhiteBoxResult,
)
from testing_engine.regression.regression import run_regression_check


SUPPORTED_SOURCE_EXTENSIONS = (".js", ".py", ".php", ".html", ".css", ".json", ".jsx", ".ts", ".tsx")
SKIP_DIRS = {"node_modules", ".git", "venv", "__pycache__", ".next", "dist", "build"}
PRIORITY_FILES = {"package.json", "requirements.txt", "pyproject.toml", "tsconfig.json", "vite.config.js", "vite.config.ts"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("CodePulse AI Platform - Backend starting...")
    yield
    terminate_all()
    print("Shutting down. All project processes terminated.")


app = FastAPI(
    title="AI-Powered Code Analysis & Testing Platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


def _dict_to_testing_result(data: dict) -> TestingResult:
    """Convert raw dict from testing modules to TestingResult."""
    tests = []
    passed = 0
    for item in data.get("tests", []):
        status = bool(item.get("passed", False))
        if status:
            passed += 1
        tests.append(TestCase(
            name=str(item.get("name", "")),
            category=str(item.get("category", "")),
            passed=status,
            input_data=str(item.get("input_data", "")),
            expected=str(item.get("expected", "")),
            actual=str(item.get("actual", "")),
            message=str(item.get("message", "")),
        ))
    return TestingResult(
        total_tests=len(tests),
        passed=passed,
        failed=len(tests) - passed,
        test_cases=tests,
        coverage_summary=data.get("summary", ""),
    )


def _testing_result_to_dicts(result: TestingResult | None) -> list[dict]:
    if not result:
        return []
    return [test.model_dump() for test in result.test_cases]


def _merge_testing_results(*results: TestingResult | None) -> TestingResult | None:
    test_cases = []
    summaries = []
    for result in results:
        if not result:
            continue
        test_cases.extend(result.test_cases)
        if result.coverage_summary:
            summaries.append(result.coverage_summary)

    if not test_cases:
        return None

    passed = sum(1 for test in test_cases if test.passed)
    return TestingResult(
        total_tests=len(test_cases),
        passed=passed,
        failed=len(test_cases) - passed,
        test_cases=test_cases,
        coverage_summary=" | ".join(summaries),
    )


def _resolve_profile_options(raw_options: dict | None) -> tuple[str, dict]:
    options = raw_options or {}
    profile = normalize_profile(options.get("profile", DEFAULT_PROFILE))
    settings = get_profile_settings(profile)

    override_map = {
        "skip_execution": "include_execution",
        "skip_static_analysis": "include_static",
        "skip_security": "include_security",
        "skip_performance": "include_performance",
        "skip_ai": "include_ai",
        "skip_testing": ("include_whitebox", "include_blackbox", "include_legacy_testing", "include_regression"),
    }

    for option_name, setting_name in override_map.items():
        if options.get(option_name):
            if isinstance(setting_name, tuple):
                for item in setting_name:
                    settings[item] = False
            else:
                settings[setting_name] = False

    return profile, settings


def _collect_project_code(project_root: str, settings: dict) -> tuple[str, str]:
    candidates = []

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]
        for filename in files:
            extension = Path(filename).suffix.lower()
            if extension not in SUPPORTED_SOURCE_EXTENSIONS and filename not in PRIORITY_FILES:
                continue
            path = os.path.join(root, filename)
            rel_path = os.path.relpath(path, project_root)
            priority = 0 if filename in PRIORITY_FILES else 1
            candidates.append((priority, rel_path.lower(), path, rel_path))

    candidates.sort()
    snippets = []
    total_chars = 0
    language = "python"

    for _, _, path, rel_path in candidates[: settings.get("project_file_limit", 80)]:
        try:
            with open(path, "r", encoding="utf-8") as file_obj:
                content = file_obj.read()
        except Exception:
            continue

        if len(content) > 50000:
            continue

        if rel_path.endswith(("package.json", ".js", ".jsx", ".ts", ".tsx")):
            language = "javascript"

        block = f"--- {rel_path} ---\n{content}\n"
        if total_chars + len(block) > settings.get("project_char_limit", 140000):
            break
        snippets.append(block)
        total_chars += len(block)

    code = "\n".join(snippets).strip()
    if not code:
        code = "// Project is empty or contains no supported readable source files."

    return code, language


@app.post("/api/analyze")
async def analyze(submission: CodeSubmission):
    """Main analysis endpoint. Streams progress via Server-Sent Events (SSE)."""
    code = submission.code
    language = submission.language
    profile, settings = _resolve_profile_options(submission.analysis_options)

    is_project_analysis = False
    if language == "project" and code.startswith("PORT:"):
        is_project_analysis = True
        try:
            port = int(code.split(":", 1)[1])
            from engines.project.process_manager import _active_processes
            info = _active_processes.get(port)
            if not info:
                raise HTTPException(status_code=400, detail="Project server not found or has stopped.")

            code, language = _collect_project_code(info["cwd"], settings)

            # Auto-enable comprehensive testing for project analysis
            # Projects need full test coverage regardless of the selected profile
            settings["include_whitebox"] = True
            settings["include_blackbox"] = True
            settings["include_legacy_testing"] = True
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read project files: {str(exc)}")

    if not code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    async def event_generator():
        report = AnalysisReport(status="success")
        loop = asyncio.get_event_loop()

        try:
            yield f"data: {json.dumps({'event': 'stage', 'id': 'step-parallel', 'msg': f'Starting {profile} analysis profile with distributed model routing...'})}\n\n"
            queue = asyncio.Queue()

            async def worker(task_id, task_name, coro):
                if coro is None:
                    return None
                await queue.put({'event': 'stage', 'id': task_id, 'msg': f'Running {task_name}...'})
                try:
                    result = await coro
                    await queue.put({'event': 'stage_done', 'id': task_id, 'msg': f'{task_name} finished'})
                    return result
                except Exception as exc:
                    await queue.put({'event': 'error', 'id': task_id, 'msg': f'{task_name} error: {str(exc)}'})
                    return None

            async def run_exec():
                if not settings.get("include_execution"):
                    return None
                if is_project_analysis:
                    return ExecutionResult(
                        success=True,
                        stdout="[Project Server] App is running in the live environment and ready for analysis.",
                        stderr="",
                        execution_time_ms=0.0,
                    )
                return await loop.run_in_executor(None, execute_code, code, language)

            async def run_static():
                if not settings.get("include_static"):
                    return None
                return await loop.run_in_executor(None, analyze_code, code, language)

            async def run_whitebox():
                if not settings.get("include_whitebox"):
                    return None
                from testing_engine.white_box.suite import run_whitebox_suite
                whitebox_data = await loop.run_in_executor(None, run_whitebox_suite, code, language)
                result = WhiteBoxResult(
                    unit=_dict_to_testing_result(whitebox_data.get("unit", {})),
                    integration=_dict_to_testing_result(whitebox_data.get("integration", {})),
                    control_flow=_dict_to_testing_result(whitebox_data.get("control_flow", {})),
                    data_flow=_dict_to_testing_result(whitebox_data.get("data_flow", {})),
                )
                result.total_tests = sum(section.total_tests for section in [result.unit, result.integration, result.control_flow, result.data_flow])
                result.total_passed = sum(section.passed for section in [result.unit, result.integration, result.control_flow, result.data_flow])
                result.summary = f"White-box: {result.total_passed}/{result.total_tests} passed across unit, integration, control flow, and data flow testing."
                return result

            async def run_blackbox():
                if not settings.get("include_blackbox"):
                    return None
                from testing_engine.black_box.suite import run_blackbox_suite
                blackbox_data = await loop.run_in_executor(None, run_blackbox_suite, code, language)
                result = BlackBoxResult(
                    bva=_dict_to_testing_result(blackbox_data.get("bva", {})),
                    ecp=_dict_to_testing_result(blackbox_data.get("ecp", {})),
                    decision_table=_dict_to_testing_result(blackbox_data.get("decision_table", {})),
                    state_transition=_dict_to_testing_result(blackbox_data.get("state_transition", {})),
                )
                result.total_tests = sum(section.total_tests for section in [result.bva, result.ecp, result.decision_table, result.state_transition])
                result.total_passed = sum(section.passed for section in [result.bva, result.ecp, result.decision_table, result.state_transition])
                result.summary = f"Black-box: {result.total_passed}/{result.total_tests} passed across BVA, ECP, decision table, and state transition testing."
                return result

            async def run_legacy_test():
                if not settings.get("include_legacy_testing"):
                    return None
                return await loop.run_in_executor(None, run_tests, code, language)

            async def run_security():
                if not settings.get("include_security"):
                    return None
                security_data = await loop.run_in_executor(None, run_security_scan, code, language)
                return SecurityResult(
                    vulnerabilities=security_data.get("vulnerabilities", []),
                    risk_level=security_data.get("risk_level", "unknown"),
                    summary=security_data.get("summary", ""),
                )

            async def run_performance():
                if not settings.get("include_performance"):
                    return None
                return await loop.run_in_executor(None, measure_performance, code, language)

            async def run_ai():
                if not settings.get("include_ai"):
                    return None
                return await loop.run_in_executor(None, analyze_with_ai, code, language, profile)

            tasks = [
                worker("step-exec", "Code Execution", run_exec()),
                worker("step-static", "Static Analysis", run_static()),
                worker("step-whitebox", "White-Box Testing", run_whitebox()),
                worker("step-blackbox", "Black-Box Testing", run_blackbox()),
                worker("step-test", "Comprehensive Test Suite", run_legacy_test()),
                worker("step-security", "Security Scan", run_security()),
                worker("step-perf", "Performance Profile", run_performance()),
                worker("step-ai", "AI Context Synthesis", run_ai()),
            ]

            task_group = asyncio.gather(*tasks)

            while not task_group.done():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    pass

            while not queue.empty():
                message = queue.get_nowait()
                yield f"data: {json.dumps(message)}\n\n"

            results = task_group.result()
            report.execution = results[0]
            report.static_analysis = results[1]
            report.white_box = results[2]
            report.black_box = results[3]
            report.testing = results[4]
            report.security = results[5]
            report.performance = results[6]
            report.ai_analysis = results[7]

            if report.testing is None:
                merged_whitebox = None
                merged_blackbox = None
                if report.white_box:
                    merged_whitebox = _merge_testing_results(
                        report.white_box.unit,
                        report.white_box.integration,
                        report.white_box.control_flow,
                        report.white_box.data_flow,
                    )
                if report.black_box:
                    merged_blackbox = _merge_testing_results(
                        report.black_box.bva,
                        report.black_box.ecp,
                        report.black_box.decision_table,
                        report.black_box.state_transition,
                    )
                report.testing = _merge_testing_results(merged_whitebox, merged_blackbox)

            if settings.get("include_regression") and report.testing:
                regression_data = run_regression_check(code, language, _testing_result_to_dicts(report.testing))
                report.regression = RegressionResult(
                    has_previous=regression_data.get("has_previous", False),
                    regressions=regression_data.get("regressions", []),
                    improvements=regression_data.get("improvements", []),
                    stable_count=regression_data.get("stable_count", 0),
                    summary=regression_data.get("summary", ""),
                )

            scores = []
            if report.static_analysis:
                scores.append(report.static_analysis.score)
            if report.testing and report.testing.total_tests > 0:
                scores.append((report.testing.passed / report.testing.total_tests) * 100)
            if report.performance:
                grade_map = {"A": 95, "B": 80, "C": 65, "D": 45, "F": 20, "N/A": 50}
                scores.append(grade_map.get(report.performance.performance_grade, 50))

            report.overall_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0.0
            report.summary = (
                f"Analysis complete using the {profile} profile. Overall score: {report.overall_score}/100. "
                f"{'Code executed successfully.' if report.execution and report.execution.success else 'Code execution skipped or failed.'}"
            )

            yield f"data: {json.dumps({'event': 'complete', 'report': report.model_dump()})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'msg': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/project/upload")
async def upload_project(file: UploadFile = File(...)):
    """Upload a ZIP project for full-stack execution and analysis."""
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10GB.")

    result = await asyncio.to_thread(extract_project, contents, file.filename)
    if not result.get("success"):
        error_msg = result.get("error", "Extraction failed.")
        print(f"Project upload error (Extraction): {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    run_result = await asyncio.to_thread(run_project, result["project_root"])
    if not run_result.get("success"):
        error_msg = run_result.get("error", "Failed to start the project. Please check dependencies.")
        print(f"Project upload error (Runner): {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    run_result["file_count"] = result["file_count"]
    run_result["files"] = result["files"]
    return run_result


@app.get("/api/project/active")
async def get_active_projects():
    """List all running project processes."""
    return {"projects": list_active()}


@app.delete("/api/project/{port}")
async def stop_project(port: int):
    """Stop a running project by port."""
    return terminate_process(port)


@app.post("/api/project/restart/{port}")
async def restart_project(port: int):
    """Restart a running project by port."""
    from engines.project.process_manager import _active_processes, _project_history
    
    info = _active_processes.get(port)
    cwd = info["cwd"] if info else _project_history.get(port)
    
    if not cwd:
        raise HTTPException(status_code=400, detail="Project path not found. Please upload again.")

    if info:
        terminate_process(port)
    run_result = await asyncio.to_thread(run_project, cwd)
    if "file_count" not in run_result:
        run_result["file_count"] = sum(len(files) for _, _, files in os.walk(cwd))
    return run_result


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "code-analysis-platform", "version": "2.0.0"}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/favicon.ico")
    async def serve_favicon():
        favicon_path = FRONTEND_DIR / "assets" / "favicon.png"
        if favicon_path.exists():
            return FileResponse(favicon_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Favicon not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)
