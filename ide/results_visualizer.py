"""
Results Visualization for Hermes IDE
Provides rich diffs, test reports, and dashboards
"""

import json
import difflib
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
from enum import Enum


class DiffFormat(Enum):
    """Supported diff formats"""
    UNIFIED = "unified"  # Standard unified diff (git-style)
    SIDE_BY_SIDE = "side_by_side"  # Two-column view
    SUMMARY = "summary"  # Just added/removed/changed counts
    HTML = "html"  # HTML markup for web display


@dataclass
class FileDiff:
    """Represents diff of a single file"""
    path: str
    old_content: str
    new_content: str
    added_lines: int = 0
    removed_lines: int = 0
    changed_lines: int = 0
    
    def __post_init__(self):
        """Calculate line counts"""
        old_lines = self.old_content.split('\n') if self.old_content else []
        new_lines = self.new_content.split('\n') if self.new_content else []
        
        # Use difflib to get accurate counts
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        
        for line in diff:
            if line.startswith('+ ') and not line.startswith('+++'):
                self.added_lines += 1
            elif line.startswith('- ') and not line.startswith('---'):
                self.removed_lines += 1
        
        self.changed_lines = min(self.added_lines, self.removed_lines)


@dataclass
class TestReport:
    """Detailed test execution report"""
    framework: str  # jest, pytest, vitest, etc
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    failures: List[Dict[str, Any]] = field(default_factory=list)
    coverage: Optional[Dict[str, float]] = None  # {file: coverage%}
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100
    
    @property
    def success(self) -> bool:
        """Return True if all tests passed"""
        return self.failed == 0 and self.total_tests > 0


@dataclass
class DashboardMetrics:
    """Metrics for a build/test dashboard"""
    project_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    build_status: str = "pending"  # pending, success, failed
    build_duration_ms: float = 0.0
    test_results: Optional[TestReport] = None
    changed_files: List[FileDiff] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)  # Build/test errors
    
    @property
    def total_changes(self) -> int:
        """Total files changed"""
        return len(self.changed_files)
    
    @property
    def total_lines_changed(self) -> int:
        """Total lines added/removed"""
        return sum(f.added_lines + f.removed_lines for f in self.changed_files)


class ResultsVisualizer:
    """
    Visualizes build and test results in multiple formats
    """
    
    def __init__(self):
        self.diffs: Dict[str, FileDiff] = {}
        self.test_reports: List[TestReport] = []
        self.dashboards: List[DashboardMetrics] = []
    
    def generate_unified_diff(self, file_path: str, old_content: str, new_content: str) -> str:
        """
        Generate unified diff (git-style) between old and new content
        
        Returns:
            Unified diff as string
        """
        old_lines = old_content.splitlines(keepends=True) if old_content else []
        new_lines = new_content.splitlines(keepends=True) if new_content else []
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{file_path} (old)",
            tofile=f"{file_path} (new)",
            lineterm=''
        )
        
        return '\n'.join(diff)
    
    def generate_side_by_side(self, file_path: str, old_content: str, new_content: str, 
                             width: int = 80) -> str:
        """
        Generate side-by-side diff view
        
        Args:
            file_path: Path to file
            old_content: Original content
            new_content: New content
            width: Column width for each side
        
        Returns:
            Side-by-side diff as string
        """
        old_lines = (old_content or "").splitlines()
        new_lines = (new_content or "").splitlines()
        
        # Pad to same length
        max_lines = max(len(old_lines), len(new_lines))
        old_lines.extend([''] * (max_lines - len(old_lines)))
        new_lines.extend([''] * (max_lines - len(new_lines)))
        
        output = [f"\n{file_path}"]
        output.append("=" * (width * 2 + 3))
        output.append(f"{'OLD':<{width}} | {'NEW':<{width}}")
        output.append("-" * (width * 2 + 3))
        
        for old, new in zip(old_lines, new_lines):
            # Mark changes
            old_marker = "! " if old != new else "  "
            new_marker = "! " if old != new else "  "
            
            old_part = (old[:width-2] if len(old) > width-2 else old).ljust(width)
            new_part = (new[:width-2] if len(new) > width-2 else new).ljust(width)
            
            output.append(f"{old_marker}{old_part} | {new_marker}{new_part}")
        
        return '\n'.join(output)
    
    def generate_summary_diff(self, file_diffs: List[FileDiff]) -> str:
        """
        Generate summary of all changes
        
        Returns:
            Summary as string
        """
        total_added = sum(d.added_lines for d in file_diffs)
        total_removed = sum(d.removed_lines for d in file_diffs)
        total_changed = sum(d.changed_lines for d in file_diffs)
        
        output = [
            "\n📊 CHANGE SUMMARY",
            "=" * 50,
            f"Files changed: {len(file_diffs)}",
            f"Lines added:   +{total_added}",
            f"Lines removed: -{total_removed}",
            f"Lines changed: {total_changed}",
            "",
            "Per-file breakdown:",
            "-" * 50
        ]
        
        for diff in sorted(file_diffs, key=lambda d: d.added_lines + d.removed_lines, reverse=True):
            output.append(
                f"{diff.path:<40} +{diff.added_lines:>4} -{diff.removed_lines:>4}"
            )
        
        return '\n'.join(output)
    
    def generate_html_diff(self, file_diffs: List[FileDiff], title: str = "Code Review") -> str:
        """
        Generate HTML diff view for web display
        
        Returns:
            HTML as string
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{title}</title>",
            "<style>",
            """
            body { font-family: monospace; background: #f5f5f5; }
            .diff { background: white; margin: 20px; padding: 20px; border-radius: 5px; }
            .file-header { font-weight: bold; background: #e0e0e0; padding: 10px; margin: 10px 0; }
            .added { background: #c8e6c9; }
            .removed { background: #ffcdd2; }
            .line-num { color: #666; margin-right: 10px; }
            .stats { margin: 20px; }
            .stat { display: inline-block; margin-right: 20px; }
            .added-count { color: #2e7d32; font-weight: bold; }
            .removed-count { color: #c62828; font-weight: bold; }
            """,
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
        ]
        
        # Add summary stats
        total_added = sum(d.added_lines for d in file_diffs)
        total_removed = sum(d.removed_lines for d in file_diffs)
        
        html_parts.append("<div class='stats'>")
        html_parts.append(f"<div class='stat'>Files: {len(file_diffs)}</div>")
        html_parts.append(f"<div class='stat added-count'>+{total_added} additions</div>")
        html_parts.append(f"<div class='stat removed-count'>-{total_removed} deletions</div>")
        html_parts.append("</div>")
        
        # Add diffs
        for diff in file_diffs:
            html_parts.append(f"<div class='diff'>")
            html_parts.append(f"<div class='file-header'>{diff.path}</div>")
            
            old_lines = (diff.old_content or "").splitlines()
            new_lines = (diff.new_content or "").splitlines()
            
            matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    for line in old_lines[i1:i2]:
                        html_parts.append(f"<div>{line}</div>")
                elif tag == 'delete':
                    for line in old_lines[i1:i2]:
                        html_parts.append(f"<div class='removed'>- {line}</div>")
                elif tag == 'insert':
                    for line in new_lines[j1:j2]:
                        html_parts.append(f"<div class='added'>+ {line}</div>")
                elif tag == 'replace':
                    for line in old_lines[i1:i2]:
                        html_parts.append(f"<div class='removed'>- {line}</div>")
                    for line in new_lines[j1:j2]:
                        html_parts.append(f"<div class='added'>+ {line}</div>")
            
            html_parts.append("</div>")
        
        html_parts.extend([
            "</body>",
            "</html>"
        ])
        
        return '\n'.join(html_parts)
    
    def generate_test_report_text(self, report: TestReport) -> str:
        """
        Generate human-readable test report
        
        Returns:
            Report as string
        """
        status_emoji = "✅" if report.success else "❌"
        
        output = [
            f"\n{status_emoji} TEST REPORT - {report.framework.upper()}",
            "=" * 60,
            f"Total Tests:  {report.total_tests}",
            f"Passed:       {report.passed} ✓",
            f"Failed:       {report.failed} ✗",
            f"Skipped:      {report.skipped} ⊘",
            f"Pass Rate:    {report.pass_rate:.1f}%",
            f"Duration:     {report.duration_ms:.0f}ms",
            ""
        ]
        
        if report.failures:
            output.append("FAILURES:")
            output.append("-" * 60)
            for failure in report.failures:
                output.append(f"\n❌ {failure.get('name', 'Unknown')}")
                output.append(f"   {failure.get('message', 'No message')}")
                if failure.get('stack'):
                    for line in failure['stack'].split('\n')[:3]:  # First 3 lines only
                        output.append(f"   {line}")
        
        if report.coverage:
            output.append("\nCOVERAGE:")
            output.append("-" * 60)
            for file_path, coverage in sorted(report.coverage.items()):
                output.append(f"{file_path:<50} {coverage:>6.1f}%")
        
        return '\n'.join(output)
    
    def generate_dashboard(self, metrics: DashboardMetrics, format: str = "text") -> str:
        """
        Generate build/test dashboard
        
        Args:
            metrics: Dashboard metrics
            format: "text", "json", or "html"
        
        Returns:
            Dashboard as string in requested format
        """
        if format == "json":
            return json.dumps(asdict(metrics), indent=2, default=str)
        
        elif format == "html":
            html = [
                "<!DOCTYPE html>",
                "<html>",
                "<head>",
                f"<title>{metrics.project_name} - Build Dashboard</title>",
                "<style>",
                """
                body { font-family: sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
                .dashboard { max-width: 1200px; margin: 0 auto; }
                .header { background: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
                .metric { background: white; padding: 20px; border-radius: 5px; text-align: center; }
                .metric-value { font-size: 32px; font-weight: bold; }
                .metric-label { color: #666; margin-top: 10px; }
                .success { border-left: 4px solid #4caf50; }
                .failed { border-left: 4px solid #f44336; }
                .pending { border-left: 4px solid #ff9800; }
                h1 { margin: 0 0 10px 0; }
                .timestamp { color: #999; font-size: 12px; }
                """,
                "</style>",
                "</head>",
                "<body>",
                "<div class='dashboard'>",
                f"<div class='header'>",
                f"<h1>{metrics.project_name}</h1>",
                f"<div class='timestamp'>{metrics.timestamp}</div>",
                f"</div>",
            ]
            
            # Status
            status_class = "success" if metrics.build_status == "success" else "failed" if metrics.build_status == "failed" else "pending"
            
            html.append("<div class='metrics'>")
            html.append(f"<div class='metric {status_class}'>")
            html.append(f"<div class='metric-value'>{metrics.build_status.upper()}</div>")
            html.append(f"<div class='metric-label'>Build Status</div>")
            html.append(f"</div>")
            
            html.append(f"<div class='metric'>")
            html.append(f"<div class='metric-value'>{metrics.total_changes}</div>")
            html.append(f"<div class='metric-label'>Files Changed</div>")
            html.append(f"</div>")
            
            html.append(f"<div class='metric'>")
            html.append(f"<div class='metric-value'>{metrics.total_lines_changed}</div>")
            html.append(f"<div class='metric-label'>Lines Changed</div>")
            html.append(f"</div>")
            
            if metrics.test_results:
                html.append(f"<div class='metric'>")
                html.append(f"<div class='metric-value'>{metrics.test_results.pass_rate:.0f}%</div>")
                html.append(f"<div class='metric-label'>Tests Pass Rate</div>")
                html.append(f"</div>")
            
            html.append("</div>")
            html.append("</div>")
            html.extend([
                "</body>",
                "</html>"
            ])
            
            return '\n'.join(html)
        
        else:  # text format
            status_emoji = "✅" if metrics.build_status == "success" else "❌" if metrics.build_status == "failed" else "⏳"
            
            output = [
                f"\n{status_emoji} BUILD DASHBOARD - {metrics.project_name}",
                "=" * 70,
                f"Timestamp:     {metrics.timestamp}",
                f"Build Status:  {metrics.build_status.upper()}",
                f"Build Time:    {metrics.build_duration_ms:.0f}ms",
                f"Files Changed: {metrics.total_changes}",
                f"Lines Changed: {metrics.total_lines_changed}",
            ]
            
            if metrics.test_results:
                output.append("")
                output.append("TEST RESULTS:")
                output.append("-" * 70)
                output.append(f"Total Tests:   {metrics.test_results.total_tests}")
                output.append(f"Passed:        {metrics.test_results.passed}")
                output.append(f"Failed:        {metrics.test_results.failed}")
                output.append(f"Pass Rate:     {metrics.test_results.pass_rate:.1f}%")
            
            if metrics.errors:
                output.append("")
                output.append("ERRORS:")
                output.append("-" * 70)
                for error in metrics.errors:
                    output.append(f"  ❌ {error.get('message', 'Unknown error')}")
            
            return '\n'.join(output)
    
    def export_diff(self, file_diffs: List[FileDiff], format: DiffFormat = DiffFormat.UNIFIED) -> str:
        """
        Export diffs in requested format
        
        Args:
            file_diffs: List of FileDiff objects
            format: Output format
        
        Returns:
            Formatted diff as string
        """
        if format == DiffFormat.UNIFIED:
            output = []
            for diff in file_diffs:
                output.append(self.generate_unified_diff(diff.path, diff.old_content, diff.new_content))
            return '\n'.join(output)
        
        elif format == DiffFormat.SIDE_BY_SIDE:
            output = []
            for diff in file_diffs:
                output.append(self.generate_side_by_side(diff.path, diff.old_content, diff.new_content))
            return '\n'.join(output)
        
        elif format == DiffFormat.SUMMARY:
            return self.generate_summary_diff(file_diffs)
        
        elif format == DiffFormat.HTML:
            return self.generate_html_diff(file_diffs)
        
        else:
            return self.generate_unified_diff(file_diffs[0].path, 
                                             file_diffs[0].old_content,
                                             file_diffs[0].new_content)
