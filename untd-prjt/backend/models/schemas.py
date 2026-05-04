"""
Pydantic models for request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ── Request Models ──────────────────────────────────────────────────────────

class CodeSubmission(BaseModel):
    """Model for code submitted by the user."""
    code: str = Field(..., description="The source code to analyze")
    language: str = Field(default="python", description="Programming language")
    analysis_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional flags to enable/disable specific analysis types"
    )


# ── Response Sub-Models ─────────────────────────────────────────────────────

class ExecutionResult(BaseModel):
    """Result of code execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    return_code: int = 0
    mode: str = "real"  # "real" or "ai"


class StaticAnalysisIssue(BaseModel):
    """A single static analysis finding."""
    severity: str  # "error", "warning", "info", "style"
    message: str
    line: Optional[int] = None
    rule: str = ""


class StaticAnalysisResult(BaseModel):
    """Full static analysis report."""
    score: float = 0.0  # 0-100
    issues: List[StaticAnalysisIssue] = []
    metrics: Dict[str, Any] = {}
    summary: str = ""


class TestCase(BaseModel):
    """A single test case result."""
    name: str
    category: str  # "unit", "edge_case", "BVA", "ECP", etc.
    passed: bool
    input_data: str = ""
    expected: str = ""
    actual: str = ""
    message: str = ""


class TestingResult(BaseModel):
    """Full automated testing report."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    test_cases: List[TestCase] = []
    coverage_summary: str = ""


# ── Advanced Testing Models ─────────────────────────────────────────────────

class WhiteBoxResult(BaseModel):
    """Combined white-box testing results."""
    unit: TestingResult = TestingResult()
    integration: TestingResult = TestingResult()
    control_flow: TestingResult = TestingResult()
    data_flow: TestingResult = TestingResult()
    total_tests: int = 0
    total_passed: int = 0
    summary: str = ""


class BlackBoxResult(BaseModel):
    """Combined black-box testing results."""
    bva: TestingResult = TestingResult()
    ecp: TestingResult = TestingResult()
    decision_table: TestingResult = TestingResult()
    state_transition: TestingResult = TestingResult()
    total_tests: int = 0
    total_passed: int = 0
    summary: str = ""


class SecurityResult(BaseModel):
    """Security scan results."""
    vulnerabilities: List[Dict[str, Any]] = []
    risk_level: str = "unknown"
    summary: str = ""


class RegressionResult(BaseModel):
    """Regression test comparison results."""
    has_previous: bool = False
    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    stable_count: int = 0
    summary: str = ""


class PerformanceResult(BaseModel):
    """Performance testing metrics."""
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    time_complexity_estimate: str = ""
    space_complexity_estimate: str = ""
    performance_grade: str = ""  # A, B, C, D, F


class AIInsight(BaseModel):
    """A single AI-generated insight."""
    category: str  # "logic", "optimization", "security", "style", "testing"
    title: str
    description: str
    suggestion: str = ""
    severity: str = "info"  # "critical", "warning", "info"


class AIAnalysisResult(BaseModel):
    """Full AI analysis report."""
    logic_analysis: str = ""
    inefficiencies: List[str] = []
    optimizations: List[str] = []
    manual_testing_simulation: str = ""
    insights: List[AIInsight] = []
    overall_assessment: str = ""
    ai_scores: Dict[str, int] = {}  # e.g. {"correctness": 8, "readability": 9, ...}


# ── Top-Level Response ──────────────────────────────────────────────────────

class AnalysisReport(BaseModel):
    """The complete analysis report returned to the user."""
    status: str = "success"  # "success", "error"
    error_message: Optional[str] = None
    execution: Optional[ExecutionResult] = None
    static_analysis: Optional[StaticAnalysisResult] = None
    testing: Optional[TestingResult] = None
    performance: Optional[PerformanceResult] = None
    ai_analysis: Optional[AIAnalysisResult] = None
    # Advanced testing
    white_box: Optional[WhiteBoxResult] = None
    black_box: Optional[BlackBoxResult] = None
    security: Optional[SecurityResult] = None
    regression: Optional[RegressionResult] = None
    summary: str = ""
    overall_score: float = 0.0  # 0-100
