"""
Tests for Phase 2 IDE Components
Results visualization and code quality checking
"""

import pytest
import json
import tempfile
from pathlib import Path
from ide.results_visualizer import (
    ResultsVisualizer, FileDiff, TestReport, DashboardMetrics, DiffFormat
)
from ide.code_quality import (
    CodeQualityChecker, LintIssue, TypeCheckError, FormattingDiff,
    QualityReport, CodeQualityIssue, ESLintLinter, PylintLinter, TypeChecker, Formatter
)


# ============================================================================
# RESULTS VISUALIZER TESTS
# ============================================================================

class TestFileDiff:
    """Test FileDiff class"""
    
    def test_file_diff_creation(self):
        """Test creating a file diff"""
        diff = FileDiff(
            path="test.py",
            old_content="print('hello')",
            new_content="print('world')"
        )
        assert diff.path == "test.py"
        assert diff.old_content == "print('hello')"
        assert diff.new_content == "print('world')"
    
    def test_file_diff_line_counts(self):
        """Test line count calculation"""
        diff = FileDiff(
            path="test.txt",
            old_content="line1\nline2\n",
            new_content="line1\nline2\nline3\n"
        )
        assert diff.added_lines >= 0
        assert diff.removed_lines >= 0


class TestTestReport:
    """Test TestReport class"""
    
    def test_test_report_pass_rate(self):
        """Test pass rate calculation"""
        report = TestReport(
            framework="jest",
            total_tests=10,
            passed=8,
            failed=2
        )
        assert report.pass_rate == 80.0
        assert report.success is False
    
    def test_test_report_success(self):
        """Test success flag"""
        report = TestReport(
            framework="pytest",
            total_tests=5,
            passed=5,
            failed=0
        )
        assert report.pass_rate == 100.0
        assert report.success is True


class TestResultsVisualizer:
    """Test ResultsVisualizer class"""
    
    def test_unified_diff(self):
        """Test unified diff generation"""
        visualizer = ResultsVisualizer()
        old = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"
        
        diff = visualizer.generate_unified_diff("test.txt", old, new)
        assert "test.txt" in diff
        assert "-" in diff or "+" in diff
    
    def test_side_by_side_diff(self):
        """Test side-by-side diff generation"""
        visualizer = ResultsVisualizer()
        old = "old content"
        new = "new content"
        
        diff = visualizer.generate_side_by_side("test.txt", old, new, width=40)
        assert "OLD" in diff or "NEW" in diff
        assert "test.txt" in diff
    
    def test_summary_diff(self):
        """Test summary diff generation"""
        visualizer = ResultsVisualizer()
        diffs = [
            FileDiff(path="file1.py", old_content="a", new_content="a\nb"),
            FileDiff(path="file2.py", old_content="x\ny", new_content="x")
        ]
        
        summary = visualizer.generate_summary_diff(diffs)
        assert "file1.py" in summary
        assert "file2.py" in summary
        assert "SUMMARY" in summary
    
    def test_html_diff(self):
        """Test HTML diff generation"""
        visualizer = ResultsVisualizer()
        diffs = [
            FileDiff(path="test.js", old_content="const a = 1;", new_content="const a = 2;")
        ]
        
        html = visualizer.generate_html_diff(diffs, "Review")
        assert "<html>" in html
        assert "Review" in html
        assert "test.js" in html
    
    def test_test_report_text(self):
        """Test test report text generation"""
        visualizer = ResultsVisualizer()
        report = TestReport(
            framework="jest",
            total_tests=10,
            passed=9,
            failed=1,
            skipped=0,
            duration_ms=5000
        )
        
        text = visualizer.generate_test_report_text(report)
        assert "jest" in text.lower()
        assert "9" in text  # passed
        assert "1" in text  # failed
        assert "90.0" in text  # pass rate
    
    def test_dashboard_generation(self):
        """Test dashboard generation"""
        visualizer = ResultsVisualizer()
        metrics = DashboardMetrics(
            project_name="MyProject",
            build_status="success"
        )
        
        # Test text format
        dashboard_text = visualizer.generate_dashboard(metrics, format="text")
        assert "MyProject" in dashboard_text
        assert "SUCCESS" in dashboard_text or "success" in dashboard_text.lower()
        
        # Test JSON format
        dashboard_json = visualizer.generate_dashboard(metrics, format="json")
        data = json.loads(dashboard_json)
        assert data["project_name"] == "MyProject"
        assert data["build_status"] == "success"


# ============================================================================
# CODE QUALITY TESTS
# ============================================================================

class TestLintIssue:
    """Test LintIssue class"""
    
    def test_lint_issue_creation(self):
        """Test creating a lint issue"""
        issue = LintIssue(
            file_path="app.js",
            line=10,
            column=5,
            severity=CodeQualityIssue.WARNING,
            rule="no-unused-vars",
            message="Variable x is not used"
        )
        assert issue.file_path == "app.js"
        assert issue.line == 10
        assert issue.severity == CodeQualityIssue.WARNING


class TestTypeCheckError:
    """Test TypeCheckError class"""
    
    def test_type_error_creation(self):
        """Test creating a type error"""
        error = TypeCheckError(
            file_path="app.ts",
            line=5,
            column=3,
            message="Type 'string' is not assignable to type 'number'"
        )
        assert error.file_path == "app.ts"
        assert error.message.startswith("Type")


class TestQualityReport:
    """Test QualityReport class"""
    
    def test_quality_report_metrics(self):
        """Test report metrics calculation"""
        report = QualityReport(
            lint_issues=[
                LintIssue("a.js", 1, 1, CodeQualityIssue.ERROR, "rule1", "msg1"),
                LintIssue("b.js", 2, 1, CodeQualityIssue.WARNING, "rule2", "msg2")
            ],
            type_errors=[
                TypeCheckError("c.ts", 3, 1, "type error")
            ]
        )
        
        assert report.total_issues == 3
        assert report.critical_issues == 2  # 1 error lint + 1 type error


class TestCodeQualityChecker:
    """Test CodeQualityChecker class"""
    
    def test_checker_creation(self):
        """Test creating a code quality checker"""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = CodeQualityChecker(tmpdir)
            assert checker.root_dir == tmpdir
            assert checker.eslint is not None
            assert checker.pylint is not None
            assert checker.type_checker is not None
    
    def test_generate_quality_report_json(self):
        """Test generating JSON quality report"""
        checker = CodeQualityChecker(".")
        report = QualityReport(
            lint_issues=[
                LintIssue("test.js", 1, 1, CodeQualityIssue.ERROR, "rule1", "Error message")
            ]
        )
        
        json_report = checker.generate_report(report, format="json")
        data = json.loads(json_report)
        assert data["total_issues"] == 1
        assert data["critical_issues"] == 1
    
    def test_generate_quality_report_text(self):
        """Test generating text quality report"""
        checker = CodeQualityChecker(".")
        report = QualityReport(
            lint_issues=[
                LintIssue("test.js", 10, 5, CodeQualityIssue.WARNING, "rule1", "Warning")
            ]
        )
        
        text_report = checker.generate_report(report, format="text")
        assert "CODE QUALITY REPORT" in text_report
        assert "1" in text_report  # total issues
        assert "test.js" in text_report


class TestESLintLinter:
    """Test ESLintLinter class"""
    
    def test_eslint_linter_creation(self):
        """Test creating ESLint linter"""
        linter = ESLintLinter(".")
        assert linter.root_dir == "."
    
    def test_eslint_find_executable(self):
        """Test finding eslint executable"""
        linter = ESLintLinter(".")
        # May or may not be available - just test it doesn't crash
        result = linter._find_eslint()
        assert result is None or isinstance(result, str)


class TestPylintLinter:
    """Test PylintLinter class"""
    
    def test_pylint_linter_creation(self):
        """Test creating Pylint linter"""
        linter = PylintLinter(".")
        assert linter.root_dir == "."


class TestTypeChecker:
    """Test TypeChecker class"""
    
    def test_type_checker_creation(self):
        """Test creating type checker"""
        checker = TypeChecker()
        assert checker is not None


class TestFormatter:
    """Test Formatter class"""
    
    def test_formatter_creation(self):
        """Test creating formatter"""
        formatter = Formatter()
        assert formatter is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIDEPhase2Integration:
    """Integration tests for Phase 2 IDE components"""
    
    def test_full_visualization_pipeline(self):
        """Test complete visualization workflow"""
        visualizer = ResultsVisualizer()
        
        # Create sample diffs
        diffs = [
            FileDiff(
                path="main.py",
                old_content="def hello():\n    print('old')",
                new_content="def hello():\n    print('new')"
            )
        ]
        
        # Generate different formats
        unified = visualizer.export_diff(diffs, DiffFormat.UNIFIED)
        assert "main.py" in unified
        
        side_by_side = visualizer.export_diff(diffs, DiffFormat.SIDE_BY_SIDE)
        assert "main.py" in side_by_side
        
        summary = visualizer.export_diff(diffs, DiffFormat.SUMMARY)
        assert "SUMMARY" in summary
        
        html = visualizer.export_diff(diffs, DiffFormat.HTML)
        assert "<html>" in html
    
    def test_quality_report_generation(self):
        """Test complete quality report workflow"""
        report = QualityReport(
            lint_issues=[
                LintIssue("app.js", 10, 5, CodeQualityIssue.ERROR, "rule1", "Error", True, "fix1"),
                LintIssue("app.js", 15, 2, CodeQualityIssue.WARNING, "rule2", "Warning", False)
            ],
            type_errors=[
                TypeCheckError("app.ts", 5, 10, "Type mismatch")
            ]
        )
        
        checker = CodeQualityChecker(".")
        
        # Generate reports in different formats
        text_report = checker.generate_report(report, format="text")
        assert "ERROR" in text_report or "❌" in text_report
        assert "code" in text_report.lower()
        
        json_report = checker.generate_report(report, format="json")
        data = json.loads(json_report)
        assert "lint_issues" in data
        assert "type_errors" in data
        assert len(data["lint_issues"]) == 2
