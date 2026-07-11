"""
Phase 2 IDE Tools - Results Visualization and Code Quality
Exposes Phase 2 IDE features as agent-callable tools
"""

import json
from ide.results_visualizer import ResultsVisualizer, FileDiff, TestReport, DashboardMetrics, DiffFormat
from ide.code_quality import CodeQualityChecker, QualityReport
from tools.registry import registry


# ============================================================================
# RESULTS VISUALIZATION TOOLS
# ============================================================================

def visualize_diff(old_file: str, new_file: str, format: str = "unified", task_id: str = None) -> str:
    """
    Visualize diff between two versions of code
    
    Args:
        old_file: Path to or content of old file
        new_file: Path to or content of new file
        format: "unified", "side_by_side", "summary", or "html"
    
    Returns:
        Formatted diff
    """
    try:
        # Handle file paths vs content
        if old_file.startswith('/') or old_file.startswith('.'):
            try:
                with open(old_file, 'r') as f:
                    old_content = f.read()
            except:
                old_content = old_file
        else:
            old_content = old_file
        
        if new_file.startswith('/') or new_file.startswith('.'):
            try:
                with open(new_file, 'r') as f:
                    new_content = f.read()
            except:
                new_content = new_file
        else:
            new_content = new_file
        
        visualizer = ResultsVisualizer()
        
        # Map format string to enum
        format_map = {
            "unified": DiffFormat.UNIFIED,
            "side_by_side": DiffFormat.SIDE_BY_SIDE,
            "summary": DiffFormat.SUMMARY,
            "html": DiffFormat.HTML
        }
        
        diff_format = format_map.get(format.lower(), DiffFormat.UNIFIED)
        
        # Create FileDiff
        file_diff = FileDiff(
            path="comparison",
            old_content=old_content,
            new_content=new_content
        )
        
        result = visualizer.export_diff([file_diff], diff_format)
        return json.dumps({"success": True, "diff": result})
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def generate_test_report(framework: str, total: int, passed: int, failed: int, 
                        skipped: int = 0, duration_ms: float = 0, task_id: str = None) -> str:
    """
    Generate formatted test report
    
    Args:
        framework: Test framework (jest, pytest, vitest, cargo)
        total: Total tests
        passed: Tests passed
        failed: Tests failed
        skipped: Tests skipped
        duration_ms: Duration in milliseconds
    
    Returns:
        Formatted test report
    """
    try:
        report = TestReport(
            framework=framework,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms
        )
        
        visualizer = ResultsVisualizer()
        result = visualizer.generate_test_report_text(report)
        
        return json.dumps({
            "success": True,
            "report": result,
            "pass_rate": report.pass_rate,
            "success": report.success
        })
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def create_build_dashboard(project_name: str, build_status: str, build_duration_ms: float = 0,
                          files_changed: int = 0, test_pass_rate: float = 0, format: str = "text",
                          task_id: str = None) -> str:
    """
    Create build/test dashboard
    
    Args:
        project_name: Name of project
        build_status: "success", "failed", or "pending"
        build_duration_ms: Build time in milliseconds
        files_changed: Number of files changed
        test_pass_rate: Test pass rate (0-100)
        format: "text", "json", or "html"
    
    Returns:
        Formatted dashboard
    """
    try:
        metrics = DashboardMetrics(
            project_name=project_name,
            build_status=build_status,
            build_duration_ms=build_duration_ms
        )
        
        # Add test results if provided
        if test_pass_rate > 0:
            total = 100
            passed = int(total * test_pass_rate / 100)
            metrics.test_results = TestReport(
                framework="unknown",
                total_tests=total,
                passed=passed,
                failed=total - passed
            )
        
        visualizer = ResultsVisualizer()
        dashboard = visualizer.generate_dashboard(metrics, format)
        
        return json.dumps({"success": True, "dashboard": dashboard})
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# CODE QUALITY TOOLS
# ============================================================================

def check_code_quality(file_path: str = None, directory: str = None, task_id: str = None) -> str:
    """
    Check code quality (linting, type-checking)
    
    Args:
        file_path: Check single file
        directory: Check entire directory
    
    Returns:
        Quality report with issues found
    """
    try:
        checker = CodeQualityChecker(".")
        
        if file_path:
            report = checker.check_file(file_path)
        elif directory:
            report = checker.check_directory(directory)
        else:
            return json.dumps({"success": False, "error": "Must provide file_path or directory"})
        
        return json.dumps({
            "success": True,
            "total_issues": report.total_issues,
            "critical_issues": report.critical_issues,
            "fixable_issues": report.fixable_issues,
            "report": checker.generate_report(report, "text")
        })
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def lint_code(file_path: str = None, fix: bool = False, task_id: str = None) -> str:
    """
    Lint code and optionally auto-fix issues
    
    Args:
        file_path: File to lint
        fix: Auto-fix issues if available
    
    Returns:
        Linting results
    """
    try:
        checker = CodeQualityChecker(".")
        
        if not file_path:
            return json.dumps({"success": False, "error": "Must provide file_path"})
        
        report = checker.check_file(file_path)
        
        if fix:
            fixed = checker.auto_fix(file_path)
            # Re-check after fix
            report = checker.check_file(file_path)
        
        return json.dumps({
            "success": True,
            "issues_found": report.total_issues,
            "fixed": report.fixable_issues if fix else 0,
            "report": checker.generate_report(report, "text")
        })
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def format_code(file_path: str, task_id: str = None) -> str:
    """
    Format code using Prettier or Black
    
    Args:
        file_path: File to format
    
    Returns:
        Formatting changes applied
    """
    try:
        checker = CodeQualityChecker(".")
        diff = checker.format_file(file_path)
        
        if not diff:
            return json.dumps({"success": True, "formatted": False, "message": "Already formatted"})
        
        return json.dumps({
            "success": True,
            "formatted": True,
            "lines_changed": diff.lines_changed,
            "bytes_changed": diff.bytes_changed
        })
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def check_types(file_path: str, language: str = None, task_id: str = None) -> str:
    """
    Check types in file (TypeScript or Python)
    
    Args:
        file_path: File to check
        language: "typescript" or "python" (auto-detected if not provided)
    
    Returns:
        Type errors found
    """
    try:
        from pathlib import Path
        
        checker = CodeQualityChecker(".")
        
        if not language:
            ext = Path(file_path).suffix
            if ext in ['.ts', '.tsx']:
                language = 'typescript'
            elif ext == '.py':
                language = 'python'
        
        if language == 'typescript':
            errors = checker.type_checker.check_typescript(file_path)
        elif language == 'python':
            errors = checker.type_checker.check_python(file_path)
        else:
            return json.dumps({"success": False, "error": f"Unsupported language: {language}"})
        
        return json.dumps({
            "success": True,
            "errors": len(errors),
            "details": [
                {
                    "line": e.line,
                    "column": e.column,
                    "message": e.message,
                    "code": e.error_code
                } for e in errors
            ]
        })
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

# Results Visualization Tools
registry.register(
    name="visualize_diff",
    toolset="ide",
    schema={
        "name": "visualize_diff",
        "description": "Visualize code differences with unified, side-by-side, or HTML format",
        "parameters": {
            "type": "object",
            "properties": {
                "old_file": {"type": "string", "description": "Old file path or content"},
                "new_file": {"type": "string", "description": "New file path or content"},
                "format": {
                    "type": "string",
                    "enum": ["unified", "side_by_side", "summary", "html"],
                    "description": "Diff format (default: unified)"
                }
            },
            "required": ["old_file", "new_file"]
        }
    },
    handler=lambda args, **kw: visualize_diff(
        old_file=args.get("old_file"),
        new_file=args.get("new_file"),
        format=args.get("format", "unified"),
        task_id=kw.get("task_id")
    )
)

registry.register(
    name="generate_test_report",
    toolset="ide",
    schema={
        "name": "generate_test_report",
        "description": "Generate formatted test execution report with metrics",
        "parameters": {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "enum": ["jest", "pytest", "vitest", "cargo", "cypress"],
                    "description": "Test framework"
                },
                "total": {"type": "integer", "description": "Total test count"},
                "passed": {"type": "integer", "description": "Passed tests"},
                "failed": {"type": "integer", "description": "Failed tests"},
                "skipped": {"type": "integer", "description": "Skipped tests"},
                "duration_ms": {"type": "number", "description": "Test duration in milliseconds"}
            },
            "required": ["framework", "total", "passed", "failed"]
        }
    },
    handler=lambda args, **kw: generate_test_report(
        framework=args.get("framework"),
        total=args.get("total", 0),
        passed=args.get("passed", 0),
        failed=args.get("failed", 0),
        skipped=args.get("skipped", 0),
        duration_ms=args.get("duration_ms", 0),
        task_id=kw.get("task_id")
    )
)

registry.register(
    name="create_build_dashboard",
    toolset="ide",
    schema={
        "name": "create_build_dashboard",
        "description": "Create build/test execution dashboard with metrics and results",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "Project name"},
                "build_status": {
                    "type": "string",
                    "enum": ["success", "failed", "pending"],
                    "description": "Build status"
                },
                "build_duration_ms": {"type": "number", "description": "Build duration"},
                "files_changed": {"type": "integer", "description": "Number of files changed"},
                "test_pass_rate": {"type": "number", "description": "Test pass rate (0-100)"},
                "format": {
                    "type": "string",
                    "enum": ["text", "json", "html"],
                    "description": "Dashboard format"
                }
            },
            "required": ["project_name", "build_status"]
        }
    },
    handler=lambda args, **kw: create_build_dashboard(
        project_name=args.get("project_name"),
        build_status=args.get("build_status"),
        build_duration_ms=args.get("build_duration_ms", 0),
        files_changed=args.get("files_changed", 0),
        test_pass_rate=args.get("test_pass_rate", 0),
        format=args.get("format", "text"),
        task_id=kw.get("task_id")
    )
)

# Code Quality Tools
registry.register(
    name="check_code_quality",
    toolset="ide",
    schema={
        "name": "check_code_quality",
        "description": "Check code quality including linting and type-checking",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Single file to check"},
                "directory": {"type": "string", "description": "Directory to scan"}
            }
        }
    },
    handler=lambda args, **kw: check_code_quality(
        file_path=args.get("file_path"),
        directory=args.get("directory"),
        task_id=kw.get("task_id")
    )
)

registry.register(
    name="lint_code",
    toolset="ide",
    schema={
        "name": "lint_code",
        "description": "Lint code and optionally auto-fix issues",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to lint"},
                "fix": {"type": "boolean", "description": "Auto-fix issues"}
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: lint_code(
        file_path=args.get("file_path"),
        fix=args.get("fix", False),
        task_id=kw.get("task_id")
    )
)

registry.register(
    name="format_code",
    toolset="ide",
    schema={
        "name": "format_code",
        "description": "Format code using Prettier (JS/TS) or Black (Python)",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to format"}
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: format_code(
        file_path=args.get("file_path"),
        task_id=kw.get("task_id")
    )
)

registry.register(
    name="check_types",
    toolset="ide",
    schema={
        "name": "check_types",
        "description": "Check types in TypeScript or Python code",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to check"},
                "language": {
                    "type": "string",
                    "enum": ["typescript", "python"],
                    "description": "Language (auto-detected if not provided)"
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: check_types(
        file_path=args.get("file_path"),
        language=args.get("language"),
        task_id=kw.get("task_id")
    )
)
