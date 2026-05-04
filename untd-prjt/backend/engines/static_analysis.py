"""
Static Code Analysis Engine
Uses Python's AST module to analyze code structure, naming conventions,
complexity, and best practices.
"""

import ast
import re
import textwrap
from typing import List, Dict, Any
from models.schemas import StaticAnalysisResult, StaticAnalysisIssue
from engines.model_router import get_task_model


def _check_naming_conventions(tree: ast.AST, code_lines: List[str]) -> List[StaticAnalysisIssue]:
    """Check PEP-8 naming conventions."""
    issues: List[StaticAnalysisIssue] = []

    for node in ast.walk(tree):
        # Function names should be snake_case
        if isinstance(node, ast.FunctionDef):
            if not re.match(r'^[a-z_][a-z0-9_]*$', node.name) and node.name != '__init__':
                issues.append(StaticAnalysisIssue(
                    severity="style",
                    message=f"Function '{node.name}' should use snake_case naming.",
                    line=node.lineno,
                    rule="naming-convention"
                ))

        # Class names should be PascalCase
        if isinstance(node, ast.ClassDef):
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                issues.append(StaticAnalysisIssue(
                    severity="style",
                    message=f"Class '{node.name}' should use PascalCase naming.",
                    line=node.lineno,
                    rule="naming-convention"
                ))

        # Constants (module-level UPPER_CASE assignments)
        if isinstance(node, ast.Assign) and hasattr(node, 'lineno'):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # Heuristic: if all uppercase, it's likely a constant — fine
                    # If mixed at module level, flag it
                    pass

    return issues


def _calculate_cyclomatic_complexity(tree: ast.AST) -> Dict[str, int]:
    """Calculate cyclomatic complexity per function."""
    complexities = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1  # base complexity
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
                elif isinstance(child, (ast.Assert,)):
                    complexity += 1
            complexities[node.name] = complexity

    return complexities


def _check_code_structure(tree: ast.AST, code: str) -> List[StaticAnalysisIssue]:
    """Check code structure issues."""
    issues: List[StaticAnalysisIssue] = []
    code_lines = code.split('\n')

    # Check for overly long lines
    for i, line in enumerate(code_lines, 1):
        if len(line) > 120:
            issues.append(StaticAnalysisIssue(
                severity="style",
                message=f"Line exceeds 120 characters ({len(line)} chars).",
                line=i,
                rule="line-length"
            ))

    # Check for functions that are too long
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, 'end_lineno', None)
            if end_line and (end_line - node.lineno) > 50:
                issues.append(StaticAnalysisIssue(
                    severity="warning",
                    message=f"Function '{node.name}' is too long ({end_line - node.lineno} lines). Consider refactoring.",
                    line=node.lineno,
                    rule="function-length"
                ))

    # Check for missing docstrings on functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, (ast.Constant,))):
                issues.append(StaticAnalysisIssue(
                    severity="info",
                    message=f"Function '{node.name}' is missing a docstring.",
                    line=node.lineno,
                    rule="missing-docstring"
                ))

    # Check for bare except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append(StaticAnalysisIssue(
                    severity="warning",
                    message="Bare 'except' clause detected. Catch specific exceptions instead.",
                    line=node.lineno,
                    rule="bare-except"
                ))

    # Check for unused imports (basic)
    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names.append((name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names.append((name, node.lineno))

    for name, lineno in imported_names:
        # Very basic check: see if the name appears elsewhere in the code
        # (excluding the import line itself)
        usages = sum(1 for line in code_lines if name in line)
        if usages <= 1:
            issues.append(StaticAnalysisIssue(
                severity="warning",
                message=f"Import '{name}' appears to be unused.",
                line=lineno,
                rule="unused-import"
            ))

    return issues


def _check_best_practices(tree: ast.AST, code: str) -> List[StaticAnalysisIssue]:
    """Check for common best practice violations."""
    issues: List[StaticAnalysisIssue] = []

    # Check for global variables
    global_assigns = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            global_assigns += 1

    if global_assigns > 5:
        issues.append(StaticAnalysisIssue(
            severity="warning",
            message=f"Too many module-level variables ({global_assigns}). Consider encapsulation.",
            rule="too-many-globals"
        ))

    # Check for magic numbers
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in (0, 1, -1, 2, True, False, None):
                parent_check = True
                if parent_check and hasattr(node, 'lineno'):
                    # Heuristic: flag numbers > 10 outside assignments to constants
                    if isinstance(node.value, int) and abs(node.value) > 10:
                        issues.append(StaticAnalysisIssue(
                            severity="info",
                            message=f"Magic number {node.value} detected. Consider using a named constant.",
                            line=node.lineno,
                            rule="magic-number"
                        ))

    # Check for deeply nested code
    def _max_depth(node, current=0):
        max_d = current
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                max_d = max(max_d, _max_depth(child, current + 1))
            else:
                max_d = max(max_d, _max_depth(child, current))
        return max_d

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            depth = _max_depth(node)
            if depth > 4:
                issues.append(StaticAnalysisIssue(
                    severity="warning",
                    message=f"Function '{node.name}' has deeply nested code (depth {depth}). Consider refactoring.",
                    line=node.lineno,
                    rule="deep-nesting"
                ))

    return issues


def _fallback_llm_static_analysis(code: str, language: str) -> StaticAnalysisResult:
    import json
    import os
    from openai import OpenAI
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return StaticAnalysisResult(
            score=0,
            summary=f"NVIDIA_API_KEY is required to natively mock static analysis for '{language}'.",
        )
    
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        prompt = f"""You are a strict Static Code Analyzer for {language}.
Analyze the provided code and return EXACTLY a JSON structure matching this format. Do not use markdown blocks.
{{
  "score": <0-100 float base score logic/style>,
  "issues": [
    {{"severity": "warning/error/style", "message": "Describe issue", "line": <integer line num>, "rule": "rule-name"}}
  ],
  "metrics": {{
    "total_lines": <int>,
    "lines_of_code": <int>,
    "num_functions": <int>,
    "num_classes": <int>,
    "num_imports": <int>,
    "avg_complexity": <float average cyclomatic complexity>
  }}
}}

Code:
{code}"""
        comp = client.chat.completions.create(
            model=get_task_model("static_fallback", "qwen/qwen2.5-coder-32b-instruct"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=1024,
        )
        res_text = comp.choices[0].message.content.strip()
        if res_text.startswith("```"):
            res_text = "\n".join(res_text.split("\n")[1:-1])
        if res_text.lower().startswith("json"):
            res_text = res_text[4:].strip()
            
        data = json.loads(res_text)
        
        issues = []
        for i in data.get("issues", []):
            issues.append(StaticAnalysisIssue(
                severity=str(i.get("severity", "info")),
                message=str(i.get("message", "Issue")),
                line=i.get("line"),
                rule=str(i.get("rule", "ai-rule"))
            ))
            
        return StaticAnalysisResult(
            score=float(data.get("score", 70.0)),
            issues=issues,
            metrics=data.get("metrics", {}),
            summary=f"LLM statically analyzed {language} and found {len(issues)} code-smell/syntax issues."
        )
    except Exception as e:
        return StaticAnalysisResult(score=0, summary=f"LLM Static Analysis error: {str(e)}")

def analyze_code(code: str, language: str = "python") -> StaticAnalysisResult:
    """
    Perform static analysis on the submitted code.
    Returns a StaticAnalysisResult with issues, metrics, and a score.
    """
    if language != "python":
        return _fallback_llm_static_analysis(code, language)

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return StaticAnalysisResult(
            score=0,
            issues=[StaticAnalysisIssue(
                severity="error",
                message=f"Syntax Error: {e.msg}",
                line=e.lineno,
                rule="syntax-error"
            )],
            summary="Code contains syntax errors and cannot be analyzed further.",
        )

    code_lines = code.split('\n')
    all_issues: List[StaticAnalysisIssue] = []

    # Run all checks
    all_issues.extend(_check_naming_conventions(tree, code_lines))
    all_issues.extend(_check_code_structure(tree, code))
    all_issues.extend(_check_best_practices(tree, code))

    # Calculate complexity metrics
    complexities = _calculate_cyclomatic_complexity(tree)

    # Count various code metrics
    num_functions = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    num_classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    num_imports = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))
    loc = len([l for l in code_lines if l.strip() and not l.strip().startswith('#')])
    total_lines = len(code_lines)

    metrics = {
        "total_lines": total_lines,
        "lines_of_code": loc,
        "num_functions": num_functions,
        "num_classes": num_classes,
        "num_imports": num_imports,
        "cyclomatic_complexity": complexities,
        "avg_complexity": round(sum(complexities.values()) / max(len(complexities), 1), 2),
    }

    # Calculate score (start at 100, deduct for issues)
    score = 100.0
    for issue in all_issues:
        if issue.severity == "error":
            score -= 15
        elif issue.severity == "warning":
            score -= 5
        elif issue.severity == "style":
            score -= 2
        elif issue.severity == "info":
            score -= 1

    score = max(0, min(100, score))

    # Build summary
    error_count = sum(1 for i in all_issues if i.severity == "error")
    warning_count = sum(1 for i in all_issues if i.severity == "warning")
    style_count = sum(1 for i in all_issues if i.severity in ("style", "info"))

    summary = (
        f"Analysis complete: {error_count} error(s), {warning_count} warning(s), "
        f"{style_count} style issue(s). Code quality score: {score:.0f}/100."
    )

    return StaticAnalysisResult(
        score=score,
        issues=all_issues,
        metrics=metrics,
        summary=summary,
    )
