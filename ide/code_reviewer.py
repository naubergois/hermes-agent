"""
Code Reviewer for Hermes IDE - Phase 3
Security scanning, pattern validation, and best practices checking
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Issue categories"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    COMPLEXITY = "complexity"
    BEST_PRACTICES = "best_practices"
    TESTING = "testing"


@dataclass
class ReviewIssue:
    """Represents a code review issue"""
    file: str
    line: int
    column: int
    severity: Severity
    category: IssueCategory
    message: str
    suggestion: str
    code: str = ""  # Issue code identifier


@dataclass
class ReviewReport:
    """Represents a complete code review report"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_issues: int = 0
    critical_issues: int = 0
    security_issues: int = 0
    performance_issues: int = 0
    maintainability_issues: int = 0
    test_coverage: float = 0.0
    complexity_score: float = 0.0  # 0-10, 0=simple, 10=complex
    review_issues: List[ReviewIssue] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        """Return True if review passed all checks"""
        return self.critical_issues == 0 and self.test_coverage >= 80
    
    @property
    def grade(self) -> str:
        """Return code grade A-F"""
        score = (10 - (self.critical_issues * 2 + self.security_issues)) * 10
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class SecurityScanner:
    """
    Security vulnerability scanner (SAST)
    """
    
    # Security patterns to detect
    SECURITY_PATTERNS = {
        r"eval\s*\(": ("eval() usage", "Never use eval(). It's a security risk.", Severity.CRITICAL),
        r"exec\s*\(": ("exec() usage", "Never use exec(). Parse input explicitly.", Severity.CRITICAL),
        r"pickle\.loads": ("Insecure pickle", "Use json instead of pickle for untrusted data.", Severity.CRITICAL),
        r"os\.system": ("os.system() usage", "Use subprocess module instead.", Severity.WARNING),
        r"subprocess\.Popen.*shell=True": ("Shell injection risk", "Don't use shell=True with subprocess.", Severity.CRITICAL),
        r"SELECT.*FROM.*\+" or r"SQL.*\+" : ("SQL injection risk", "Use parameterized queries.", Severity.CRITICAL),
        r"password.*=.*['\"]": ("Hardcoded password", "Never hardcode passwords. Use env vars.", Severity.CRITICAL),
        r"api[_-]?key.*=.*['\"]": ("Hardcoded API key", "Never hardcode API keys. Use env vars.", Severity.CRITICAL),
        r"requests\..*verify=False": ("SSL verification disabled", "Always verify SSL certificates.", Severity.CRITICAL),
        r"crypto.*=.*DES\|RC4": ("Weak encryption", "Use AES or stronger algorithms.", Severity.CRITICAL),
        r"\.json\(\)" and r"\.loads\(.*user": ("Unvalidated JSON parsing", "Validate JSON schema before parsing.", Severity.WARNING),
        r"innerHTML\s*=": ("DOM XSS risk", "Use textContent or sanitize HTML.", Severity.CRITICAL),
        r"dangerouslySetInnerHTML": ("React XSS risk", "Sanitize HTML before using dangerouslySetInnerHTML.", Severity.WARNING),
    }
    
    @staticmethod
    def scan_file(file_path: str, content: str) -> List[ReviewIssue]:
        """
        Scan file for security issues
        
        Args:
            file_path: File path
            content: File content
        
        Returns:
            List of security issues found
        """
        issues = []
        lines = content.split('\n')
        
        # Check for hardcoded secrets
        for i, line in enumerate(lines, 1):
            # Hardcoded credentials
            if re.search(r'(password|api_key|secret|token)\s*=\s*["\'][\w\-]+["\']', line, re.IGNORECASE):
                if "env" not in line.lower() and "config" not in line.lower():
                    issues.append(ReviewIssue(
                        file=file_path,
                        line=i,
                        column=1,
                        severity=Severity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        message="Hardcoded secret detected",
                        suggestion="Move to environment variables or config file",
                        code="SEC-001"
                    ))
            
            # SQL injection patterns
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE)\s+.*\+\s*', line, re.IGNORECASE):
                if "parameterized" not in line.lower() and "?" not in line:
                    issues.append(ReviewIssue(
                        file=file_path,
                        line=i,
                        column=1,
                        severity=Severity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        message="Potential SQL injection",
                        suggestion="Use parameterized queries",
                        code="SEC-002"
                    ))
            
            # Dangerous functions
            if "eval(" in line or "exec(" in line:
                issues.append(ReviewIssue(
                    file=file_path,
                    line=i,
                    column=line.find("eval" if "eval(" in line else "exec"),
                    severity=Severity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    message=f"{'eval' if 'eval(' in line else 'exec'}() is dangerous",
                    suggestion="Parse input explicitly instead",
                    code="SEC-003"
                ))
            
            # Disabled SSL verification
            if "verify=False" in line or "check_certificate=False" in line:
                issues.append(ReviewIssue(
                    file=file_path,
                    line=i,
                    column=1,
                    severity=Severity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    message="SSL verification disabled",
                    suggestion="Always verify SSL certificates",
                    code="SEC-004"
                ))
        
        return issues


class ComplexityAnalyzer:
    """
    Analyze code complexity
    """
    
    @staticmethod
    def calculate_cyclomatic_complexity(content: str) -> float:
        """
        Calculate cyclomatic complexity
        
        Args:
            content: File content
        
        Returns:
            Complexity score (0-10)
        """
        # Count decision points
        decisions = 0
        decisions += len(re.findall(r'\bif\b', content))
        decisions += len(re.findall(r'\belse\b', content))
        decisions += len(re.findall(r'\belif\b', content))
        decisions += len(re.findall(r'\bfor\b', content))
        decisions += len(re.findall(r'\bwhile\b', content))
        decisions += len(re.findall(r'\bcatch\b', content))
        decisions += len(re.findall(r'\?.*:', content))  # Ternary
        
        # Normalize to 0-10 scale
        complexity = min(10, decisions / 5)
        return complexity
    
    @staticmethod
    def calculate_lines_of_code(content: str) -> int:
        """Count lines of code"""
        lines = content.split('\n')
        # Filter out empty lines and comments
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        return len(code_lines)


class PatternValidator:
    """
    Validate code against project patterns and best practices
    """
    
    PATTERNS = {
        "naming_convention_function": (r'^[a-z_][a-z0-9_]*$', "Function names should be snake_case"),
        "naming_convention_class": (r'^[A-Z][a-zA-Z0-9]*$', "Class names should be PascalCase"),
        "naming_convention_constant": (r'^[A-Z_][A-Z0-9_]*$', "Constants should be UPPER_SNAKE_CASE"),
        "documentation_function": (r'def\s+\w+.*:\s*"""', "Functions should have docstrings"),
        "documentation_class": (r'class\s+\w+.*:\s*"""', "Classes should have docstrings"),
    }
    
    @staticmethod
    def validate_python_conventions(content: str, file_path: str) -> List[ReviewIssue]:
        """
        Validate Python code conventions
        
        Args:
            content: File content
            file_path: File path
        
        Returns:
            List of convention violations
        """
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check function naming
            func_match = re.match(r'^\s*def\s+(\w+)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                    if not func_name.startswith('__'):  # Ignore dunder methods
                        issues.append(ReviewIssue(
                            file=file_path,
                            line=i,
                            column=1,
                            severity=Severity.WARNING,
                            category=IssueCategory.BEST_PRACTICES,
                            message=f"Function '{func_name}' violates naming convention",
                            suggestion="Use snake_case for function names",
                            code="STYLE-001"
                        ))
            
            # Check class naming
            class_match = re.match(r'^\s*class\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(1)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                    issues.append(ReviewIssue(
                        file=file_path,
                        line=i,
                        column=1,
                        severity=Severity.WARNING,
                        category=IssueCategory.BEST_PRACTICES,
                        message=f"Class '{class_name}' violates naming convention",
                        suggestion="Use PascalCase for class names",
                        code="STYLE-002"
                    ))
        
        return issues


class CodeReviewer:
    """
    Main code reviewer orchestrating all checks
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.security_scanner = SecurityScanner()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.pattern_validator = PatternValidator()
    
    def review_file(self, file_path: str, test_coverage: float = 0.0) -> ReviewReport:
        """
        Review a single file
        
        Args:
            file_path: File to review
            test_coverage: Test coverage percentage
        
        Returns:
            ReviewReport with findings
        """
        try:
            content = Path(file_path).read_text()
        except:
            content = file_path  # Assume it's content, not path
        
        report = ReviewReport()
        report.test_coverage = test_coverage
        
        # Run security scan
        security_issues = self.security_scanner.scan_file(file_path, content)
        report.review_issues.extend(security_issues)
        report.security_issues = len(security_issues)
        
        # Analyze complexity
        report.complexity_score = self.complexity_analyzer.calculate_cyclomatic_complexity(content)
        
        # Validate patterns
        if file_path.endswith('.py'):
            pattern_issues = self.pattern_validator.validate_python_conventions(content, file_path)
            report.review_issues.extend(pattern_issues)
        
        # Count issues by severity
        for issue in report.review_issues:
            report.total_issues += 1
            if issue.severity == Severity.CRITICAL:
                report.critical_issues += 1
            if issue.category == IssueCategory.PERFORMANCE:
                report.performance_issues += 1
            if issue.category == IssueCategory.MAINTAINABILITY:
                report.maintainability_issues += 1
        
        return report
    
    def generate_report(self, report: ReviewReport, format: str = "text") -> str:
        """
        Generate review report
        
        Args:
            report: ReviewReport
            format: "text" or "json"
        
        Returns:
            Formatted report
        """
        if format == "json":
            return json.dumps({
                "timestamp": report.timestamp,
                "passed": report.passed,
                "grade": report.grade,
                "total_issues": report.total_issues,
                "critical_issues": report.critical_issues,
                "security_issues": report.security_issues,
                "test_coverage": report.test_coverage,
                "complexity_score": report.complexity_score,
                "issues": [
                    {
                        "file": i.file,
                        "line": i.line,
                        "severity": i.severity.value,
                        "category": i.category.value,
                        "message": i.message,
                        "suggestion": i.suggestion,
                        "code": i.code
                    } for i in report.review_issues
                ]
            }, indent=2)
        
        # Text format
        output = [
            "\n📋 CODE REVIEW REPORT",
            "=" * 70,
            f"Grade: {report.grade} {'✅' if report.passed else '❌'}",
            f"Timestamp: {report.timestamp}",
            "",
            "SUMMARY:",
            "-" * 70,
            f"Total Issues:        {report.total_issues}",
            f"Critical Issues:     {report.critical_issues}",
            f"Security Issues:     {report.security_issues}",
            f"Performance Issues:  {report.performance_issues}",
            f"Maintainability:     {report.maintainability_issues}",
            f"Test Coverage:       {report.test_coverage:.1f}%",
            f"Complexity Score:    {report.complexity_score:.1f}/10",
            f"Overall Status:      {'✅ PASSED' if report.passed else '❌ FAILED'}",
            ""
        ]
        
        if report.review_issues:
            output.append("ISSUES:")
            output.append("-" * 70)
            
            # Sort by severity
            sorted_issues = sorted(report.review_issues, 
                                  key=lambda x: (x.severity.value != Severity.CRITICAL,
                                                x.line))
            
            for issue in sorted_issues:
                emoji = {
                    Severity.CRITICAL: "🔴",
                    Severity.ERROR: "🟠",
                    Severity.WARNING: "🟡",
                    Severity.INFO: "🔵"
                }[issue.severity]
                
                output.append(f"{emoji} {issue.file}:{issue.line}:{issue.column}")
                output.append(f"   [{issue.code}] {issue.message}")
                output.append(f"   Suggestion: {issue.suggestion}")
        
        return '\n'.join(output)
