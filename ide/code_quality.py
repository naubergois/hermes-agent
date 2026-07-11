"""
Code Quality Tools for Hermes IDE
Linting, formatting, and type-checking integration
"""

import json
import subprocess
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum


class CodeQualityIssue(Enum):
    """Severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LintIssue:
    """Represents a linting issue"""
    file_path: str
    line: int
    column: int
    severity: CodeQualityIssue
    rule: str
    message: str
    fix_available: bool = False
    fix_text: Optional[str] = None


@dataclass
class TypeCheckError:
    """Represents a type checking error"""
    file_path: str
    line: int
    column: int
    message: str
    severity: CodeQualityIssue = CodeQualityIssue.ERROR
    error_code: Optional[str] = None


@dataclass
class FormattingDiff:
    """Represents formatting changes"""
    file_path: str
    old_content: str
    new_content: str
    lines_changed: int = 0
    bytes_changed: int = 0


@dataclass
class QualityReport:
    """Overall code quality report"""
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    lint_issues: List[LintIssue] = field(default_factory=list)
    type_errors: List[TypeCheckError] = field(default_factory=list)
    formatting_issues: List[FormattingDiff] = field(default_factory=list)
    
    @property
    def total_issues(self) -> int:
        """Total issues found"""
        return len(self.lint_issues) + len(self.type_errors)
    
    @property
    def critical_issues(self) -> int:
        """Count of errors (excluding warnings/info)"""
        errors = sum(1 for i in self.lint_issues if i.severity == CodeQualityIssue.ERROR)
        errors += len(self.type_errors)
        return errors
    
    @property
    def fixable_issues(self) -> int:
        """Count of auto-fixable issues"""
        return sum(1 for i in self.lint_issues if i.fix_available)


class Linter:
    """
    Abstract linter interface - subclass for specific linters
    """
    
    def lint(self, file_path: str) -> List[LintIssue]:
        """Lint a single file"""
        raise NotImplementedError
    
    def lint_directory(self, dir_path: str, pattern: str = None) -> List[LintIssue]:
        """Lint all files in directory"""
        raise NotImplementedError
    
    def fix_issues(self, file_path: str) -> bool:
        """Auto-fix issues in file"""
        raise NotImplementedError


class ESLintLinter(Linter):
    """ESLint integration for JavaScript/TypeScript"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
    
    def _find_eslint(self) -> Optional[str]:
        """Find eslint executable"""
        # Try local node_modules first
        local = Path(self.root_dir) / "node_modules" / ".bin" / "eslint"
        if local.exists():
            return str(local)
        
        # Try global
        try:
            result = subprocess.run(
                ["which", "eslint"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def lint(self, file_path: str) -> List[LintIssue]:
        """Lint JavaScript/TypeScript file"""
        eslint = self._find_eslint()
        if not eslint:
            return []
        
        try:
            result = subprocess.run(
                [eslint, file_path, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.root_dir
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            if not data or not data[0].get('messages'):
                return []
            
            issues = []
            for msg in data[0]['messages']:
                severity_map = {
                    1: CodeQualityIssue.WARNING,
                    2: CodeQualityIssue.ERROR
                }
                
                issue = LintIssue(
                    file_path=file_path,
                    line=msg.get('line', 0),
                    column=msg.get('column', 0),
                    severity=severity_map.get(msg.get('severity', 1), CodeQualityIssue.WARNING),
                    rule=msg.get('ruleId', 'unknown'),
                    message=msg.get('message', ''),
                    fix_available=bool(msg.get('fix')),
                    fix_text=msg.get('fix', {}).get('text') if msg.get('fix') else None
                )
                issues.append(issue)
            
            return issues
        
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def lint_directory(self, dir_path: str, pattern: str = None) -> List[LintIssue]:
        """Lint all JavaScript/TypeScript files"""
        eslint = self._find_eslint()
        if not eslint:
            return []
        
        try:
            args = [eslint, dir_path, "--format", "json"]
            if pattern:
                args.extend(["--ext", pattern])
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.root_dir
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for file_data in data:
                for msg in file_data.get('messages', []):
                    severity_map = {
                        1: CodeQualityIssue.WARNING,
                        2: CodeQualityIssue.ERROR
                    }
                    
                    issue = LintIssue(
                        file_path=file_data['filePath'],
                        line=msg.get('line', 0),
                        column=msg.get('column', 0),
                        severity=severity_map.get(msg.get('severity', 1), CodeQualityIssue.WARNING),
                        rule=msg.get('ruleId', 'unknown'),
                        message=msg.get('message', ''),
                        fix_available=bool(msg.get('fix')),
                        fix_text=msg.get('fix', {}).get('text') if msg.get('fix') else None
                    )
                    issues.append(issue)
            
            return issues
        
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def fix_issues(self, file_path: str) -> bool:
        """Auto-fix ESLint issues"""
        eslint = self._find_eslint()
        if not eslint:
            return False
        
        try:
            result = subprocess.run(
                [eslint, file_path, "--fix"],
                capture_output=True,
                timeout=10,
                cwd=self.root_dir
            )
            return result.returncode == 0
        except:
            return False


class PylintLinter(Linter):
    """Pylint integration for Python"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
    
    def _has_pylint(self) -> bool:
        """Check if pylint is available"""
        try:
            subprocess.run(
                ["pylint", "--version"],
                capture_output=True,
                timeout=2
            )
            return True
        except:
            return False
    
    def lint(self, file_path: str) -> List[LintIssue]:
        """Lint Python file with pylint"""
        if not self._has_pylint():
            return []
        
        try:
            result = subprocess.run(
                ["pylint", file_path, "--output-format=json", "--disable=all", "--enable=E,W"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.root_dir
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for msg in data:
                severity_map = {
                    'warning': CodeQualityIssue.WARNING,
                    'error': CodeQualityIssue.ERROR,
                    'info': CodeQualityIssue.INFO
                }
                
                issue = LintIssue(
                    file_path=file_path,
                    line=msg.get('line', 0),
                    column=msg.get('column', 0),
                    severity=severity_map.get(msg.get('type', 'warning'), CodeQualityIssue.WARNING),
                    rule=msg.get('symbol', 'unknown'),
                    message=msg.get('message', ''),
                    fix_available=False
                )
                issues.append(issue)
            
            return issues
        
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def lint_directory(self, dir_path: str, pattern: str = None) -> List[LintIssue]:
        """Lint all Python files"""
        if not self._has_pylint():
            return []
        
        try:
            result = subprocess.run(
                ["pylint", dir_path, "--output-format=json", "--disable=all", "--enable=E,W"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.root_dir
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            severity_map = {
                'warning': CodeQualityIssue.WARNING,
                'error': CodeQualityIssue.ERROR,
                'info': CodeQualityIssue.INFO
            }
            
            for msg in data:
                issue = LintIssue(
                    file_path=msg.get('path', ''),
                    line=msg.get('line', 0),
                    column=msg.get('column', 0),
                    severity=severity_map.get(msg.get('type', 'warning'), CodeQualityIssue.WARNING),
                    rule=msg.get('symbol', 'unknown'),
                    message=msg.get('message', ''),
                    fix_available=False
                )
                issues.append(issue)
            
            return issues
        
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def fix_issues(self, file_path: str) -> bool:
        """Pylint doesn't auto-fix"""
        return False


class TypeChecker:
    """Type checking integration"""
    
    def check_typescript(self, file_path: str, root_dir: str = ".") -> List[TypeCheckError]:
        """Check TypeScript types"""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--json", file_path],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=root_dir
            )
            
            if not result.stderr:
                return []
            
            data = json.loads(result.stderr)
            errors = []
            
            for diag in data.get('diagnostics', []):
                error = TypeCheckError(
                    file_path=diag.get('file', file_path),
                    line=diag.get('start', 0),
                    column=diag.get('start', 0),
                    message=diag.get('message', ''),
                    error_code=str(diag.get('code', ''))
                )
                errors.append(error)
            
            return errors
        except:
            return []
    
    def check_python(self, file_path: str, root_dir: str = ".") -> List[TypeCheckError]:
        """Check Python types with pyright"""
        try:
            result = subprocess.run(
                ["pyright", file_path, "--outputjson"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=root_dir
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            errors = []
            
            for diag in data.get('generalDiagnostics', []):
                # Extract line/column from range
                range_data = diag.get('range', {})
                start = range_data.get('start', {})
                
                error = TypeCheckError(
                    file_path=diag.get('file', file_path),
                    line=start.get('line', 0),
                    column=start.get('character', 0),
                    message=diag.get('message', ''),
                    error_code=diag.get('rule', '')
                )
                errors.append(error)
            
            return errors
        except:
            return []


class Formatter:
    """Code formatter integration"""
    
    @staticmethod
    def format_with_prettier(file_path: str, root_dir: str = ".") -> Optional[FormattingDiff]:
        """Format JavaScript/TypeScript with Prettier"""
        try:
            # Read original
            with open(file_path, 'r') as f:
                original = f.read()
            
            # Run prettier
            result = subprocess.run(
                ["npx", "prettier", "--write", file_path],
                capture_output=True,
                timeout=10,
                cwd=root_dir
            )
            
            # Read formatted
            with open(file_path, 'r') as f:
                formatted = f.read()
            
            if original == formatted:
                return None
            
            return FormattingDiff(
                file_path=file_path,
                old_content=original,
                new_content=formatted,
                lines_changed=len(formatted.split('\n')) - len(original.split('\n')),
                bytes_changed=len(formatted) - len(original)
            )
        except:
            return None
    
    @staticmethod
    def format_with_black(file_path: str, root_dir: str = ".") -> Optional[FormattingDiff]:
        """Format Python with Black"""
        try:
            # Read original
            with open(file_path, 'r') as f:
                original = f.read()
            
            # Run black
            result = subprocess.run(
                ["black", file_path],
                capture_output=True,
                timeout=10,
                cwd=root_dir
            )
            
            # Read formatted
            with open(file_path, 'r') as f:
                formatted = f.read()
            
            if original == formatted:
                return None
            
            return FormattingDiff(
                file_path=file_path,
                old_content=original,
                new_content=formatted,
                lines_changed=len(formatted.split('\n')) - len(original.split('\n')),
                bytes_changed=len(formatted) - len(original)
            )
        except:
            return None


class CodeQualityChecker:
    """
    Main code quality checker orchestrating linting, type-checking, and formatting
    """
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.eslint = ESLintLinter(root_dir)
        self.pylint = PylintLinter(root_dir)
        self.type_checker = TypeChecker()
        self.formatter = Formatter()
    
    def check_file(self, file_path: str) -> QualityReport:
        """Run all checks on a single file"""
        report = QualityReport()
        
        file_ext = Path(file_path).suffix
        
        # Lint
        if file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            report.lint_issues.extend(self.eslint.lint(file_path))
            report.type_errors.extend(self.type_checker.check_typescript(file_path, self.root_dir))
        elif file_ext == '.py':
            report.lint_issues.extend(self.pylint.lint(file_path))
            report.type_errors.extend(self.type_checker.check_python(file_path, self.root_dir))
        
        return report
    
    def check_directory(self, dir_path: str, pattern: str = None) -> QualityReport:
        """Run all checks on all files in directory"""
        report = QualityReport()
        
        # Find all code files
        if Path(dir_path).exists():
            for ext in ['.js', '.jsx', '.ts', '.tsx']:
                report.lint_issues.extend(self.eslint.lint_directory(dir_path, f"*{ext}"))
            
            report.lint_issues.extend(self.pylint.lint_directory(dir_path, '.py'))
        
        return report
    
    def format_file(self, file_path: str) -> Optional[FormattingDiff]:
        """Format a single file"""
        file_ext = Path(file_path).suffix
        
        if file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            return self.formatter.format_with_prettier(file_path, self.root_dir)
        elif file_ext == '.py':
            return self.formatter.format_with_black(file_path, self.root_dir)
        
        return None
    
    def auto_fix(self, file_path: str) -> bool:
        """Auto-fix issues in file"""
        file_ext = Path(file_path).suffix
        
        if file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            return self.eslint.fix_issues(file_path)
        
        return False
    
    def generate_report(self, report: QualityReport, format: str = "text") -> str:
        """Generate quality report in requested format"""
        if format == "json":
            return json.dumps({
                'timestamp': report.timestamp,
                'total_issues': report.total_issues,
                'critical_issues': report.critical_issues,
                'fixable_issues': report.fixable_issues,
                'lint_issues': [
                    {
                        'file': i.file_path,
                        'line': i.line,
                        'column': i.column,
                        'severity': i.severity.value,
                        'rule': i.rule,
                        'message': i.message,
                        'fixable': i.fix_available
                    } for i in report.lint_issues
                ],
                'type_errors': [
                    {
                        'file': e.file_path,
                        'line': e.line,
                        'column': e.column,
                        'message': e.message,
                        'code': e.error_code
                    } for e in report.type_errors
                ]
            }, indent=2)
        
        # Text format
        output = [
            "\n📊 CODE QUALITY REPORT",
            "=" * 70,
            f"Total Issues:     {report.total_issues}",
            f"Critical Issues:  {report.critical_issues}",
            f"Fixable Issues:   {report.fixable_issues}",
            ""
        ]
        
        if report.lint_issues:
            output.append("LINTING ISSUES:")
            output.append("-" * 70)
            for issue in sorted(report.lint_issues, key=lambda x: (x.file_path, x.line)):
                severity_emoji = {
                    CodeQualityIssue.ERROR: "❌",
                    CodeQualityIssue.WARNING: "⚠️",
                    CodeQualityIssue.INFO: "ℹ️"
                }
                emoji = severity_emoji.get(issue.severity, "")
                fix_marker = "🔧" if issue.fix_available else ""
                output.append(f"{emoji} {issue.file_path}:{issue.line}:{issue.column}")
                output.append(f"   [{issue.rule}] {issue.message} {fix_marker}")
        
        if report.type_errors:
            output.append("\nTYPE ERRORS:")
            output.append("-" * 70)
            for error in sorted(report.type_errors, key=lambda x: (x.file_path, x.line)):
                output.append(f"❌ {error.file_path}:{error.line}:{error.column}")
                output.append(f"   {error.message}")
        
        return '\n'.join(output)
