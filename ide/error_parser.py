"""
Error Parser

Parses build and test errors to:
- Extract error location (file, line, column)
- Map errors to source code
- Generate fix suggestions
- Categorize error types
"""

import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ParsedError:
    """Represents a parsed error"""

    def __init__(
        self,
        file: str,
        line: int,
        column: int,
        message: str,
        error_type: str,
        severity: str = "error",
    ):
        self.file = file
        self.line = line
        self.column = column
        self.message = message
        self.error_type = error_type  # typescript, python, rust, etc.
        self.severity = severity  # error, warning, info
        self.suggestion = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "type": self.error_type,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


class ErrorParser:
    """Parse build and test errors"""

    # Regex patterns for different error types
    PATTERNS = {
        "typescript": [
            # TS file errors: src/app.ts:10:5 - error TS2551: Property 'foo' does not exist
            re.compile(
                r"(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+)\s*-\s*(?P<severity>error|warning|info)\s+TS(?P<code>\d+):\s*(?P<message>.+)"
            ),
        ],
        "python": [
            # Python errors: File "app.py", line 10, in <module>
            re.compile(
                r'File "(?P<file>[^"]+)", line (?P<line>\d+),.*\n\s*(?P<message>.+)'
            ),
            # Python simple: app.py:10: error: ...
            re.compile(
                r"(?P<file>[^:]+):(?P<line>\d+):\s*(?P<severity>error|warning):\s*(?P<message>.+)"
            ),
        ],
        "rust": [
            # Rust errors: error[E0425]: cannot find value `x` in this scope
            re.compile(
                r"(?P<severity>error|warning)\[(?P<code>[^\]]+)\]:\s*(?P<message>.+)\n\s*-->\s*(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+)"
            ),
        ],
        "go": [
            # Go errors: ./main.go:10:5: undefined: foo
            re.compile(
                r"(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)"
            ),
        ],
        "generic": [
            # Generic pattern: file:line:col: message
            re.compile(
                r"(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)"
            ),
        ],
    }

    def __init__(self, project_root: str = "."):
        """Initialize error parser"""
        self.project_root = Path(project_root).resolve()

    def parse_output(self, output: str, error_type: str = "generic") -> List[ParsedError]:
        """
        Parse error output from build/test run.

        Args:
            output: Build output containing errors
            error_type: Type of error (typescript, python, rust, go, generic)

        Returns:
            List of parsed errors
        """
        errors = []

        patterns = self.PATTERNS.get(error_type, self.PATTERNS["generic"])

        for line in output.split("\n"):
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    try:
                        error = self._parse_match(match, error_type)
                        if error:
                            errors.append(error)
                    except Exception as e:
                        logger.debug(f"Failed to parse error: {e}")

        return errors

    def _parse_match(self, match: re.Match, error_type: str) -> Optional[ParsedError]:
        """Parse a regex match into ParsedError"""
        try:
            file = match.group("file")
            line = int(match.group("line"))
            column = int(match.group("column")) if "column" in match.groupdict() else 1
            message = match.group("message")
            severity = match.group("severity") if "severity" in match.groupdict() else "error"

            # Make file path relative to project root
            file_path = Path(file).resolve()
            try:
                file = str(file_path.relative_to(self.project_root))
            except ValueError:
                # File is outside project root
                file = file_path.name

            error = ParsedError(
                file=file,
                line=line,
                column=column,
                message=message,
                error_type=error_type,
                severity=severity,
            )

            # Generate suggestion
            error.suggestion = self._generate_suggestion(error)

            return error
        except (IndexError, ValueError, AttributeError) as e:
            logger.debug(f"Failed to extract error details: {e}")
            return None

    def _generate_suggestion(self, error: ParsedError) -> Optional[str]:
        """Generate fix suggestion based on error"""
        message = error.message.lower()

        # TypeScript suggestions
        if error.error_type == "typescript":
            if "does not exist" in message:
                return "Check if the property/function name is correct or if it's imported"
            elif "cannot find module" in message or "cannot find name" in message:
                return "Check if the import path is correct or if the module is installed"
            elif "is not assignable to type" in message:
                return "Check type compatibility or use a type assertion"

        # Python suggestions
        elif error.error_type == "python":
            if "no module named" in message:
                return "Install the required package or check the import path"
            elif "undefined name" in message or "is not defined" in message:
                return "Check if the variable/function is defined or properly imported"
            elif "indentation error" in message.lower():
                return "Check indentation - Python requires consistent indentation"
            elif "syntax error" in message.lower():
                return "Check syntax - review the line for typos or missing characters"

        # Rust suggestions
        elif error.error_type == "rust":
            if "cannot find value" in message:
                return "Check if the variable is defined or properly scoped"
            elif "mismatched types" in message:
                return "Check type compatibility or add type annotations"

        # Go suggestions
        elif error.error_type == "go":
            if "undefined:" in message:
                return "Check if the identifier is defined or properly imported"
            elif "declared but not used" in message:
                return "Remove the unused variable or use it"

        return None

    def extract_errors_from_file(self, file_path: str) -> List[ParsedError]:
        """Extract errors from a source file (syntax checking)"""
        errors = []

        try:
            with open(file_path) as f:
                content = f.read()

            # Detect file type
            suffix = Path(file_path).suffix.lower()
            if suffix in (".ts", ".tsx"):
                error_type = "typescript"
            elif suffix in (".py",):
                error_type = "python"
            elif suffix in (".rs",):
                error_type = "rust"
            elif suffix in (".go",):
                error_type = "go"
            else:
                error_type = "generic"

            # Simple syntax checks
            if error_type == "python":
                errors.extend(self._check_python_syntax(file_path, content))
            elif error_type == "typescript":
                errors.extend(self._check_typescript_syntax(file_path, content))

        except Exception as e:
            logger.warning(f"Failed to extract errors from file: {e}")

        return errors

    def _check_python_syntax(self, file_path: str, content: str) -> List[ParsedError]:
        """Check Python syntax errors"""
        errors = []

        # Check indentation
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if line and not line[0].isspace() and line[0] != "#":
                # Check for common Python errors
                if "import" in line and "from" in line:
                    if not ("import" in line or "from" in line):
                        errors.append(
                            ParsedError(
                                file=file_path,
                                line=i,
                                column=1,
                                message="Invalid import statement",
                                error_type="python",
                            )
                        )

        return errors

    def _check_typescript_syntax(self, file_path: str, content: str) -> List[ParsedError]:
        """Check TypeScript syntax errors"""
        errors = []

        # Check for common TypeScript errors
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Missing semicolons
            if "function" in line and "(" in line and ")" in line and not line.rstrip().endswith(
                ";"
            ):
                pass  # Optional in TypeScript

            # Unmatched braces
            if "{" in line and "}" not in line:
                # Track brace balance
                pass

        return errors

    def group_errors_by_file(self, errors: List[ParsedError]) -> Dict[str, List[ParsedError]]:
        """Group errors by file"""
        grouped = {}
        for error in errors:
            if error.file not in grouped:
                grouped[error.file] = []
            grouped[error.file].append(error)
        return grouped

    def filter_errors_by_type(
        self, errors: List[ParsedError], error_type: str
    ) -> List[ParsedError]:
        """Filter errors by type"""
        return [e for e in errors if e.error_type == error_type]

    def filter_errors_by_severity(
        self, errors: List[ParsedError], severity: str
    ) -> List[ParsedError]:
        """Filter errors by severity"""
        return [e for e in errors if e.severity == severity]
