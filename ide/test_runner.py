"""
Test Runner

Handles test discovery and execution:
- Test discovery (Jest, Vitest, Pytest, Cargo test, etc.)
- Test execution with selective filtering
- Result parsing (JSON, XML, plain text)
- Coverage reporting
- Failed test re-running
"""

import json
import logging
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestCase:
    """Represents a single test case"""

    def __init__(self, name: str, file: str, status: str = "unknown"):
        self.name = name
        self.file = file
        self.status = status  # passed, failed, skipped, unknown
        self.duration = 0.0
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "file": self.file,
            "status": self.status,
            "duration": self.duration,
            "error": self.error,
        }


class TestResult:
    """Result of test execution"""

    def __init__(
        self,
        success: bool,
        test_framework: str,
        total: int = 0,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        duration: float = 0,
        output: str = "",
    ):
        self.success = success
        self.test_framework = test_framework
        self.total = total
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.duration = duration
        self.output = output
        self.test_cases: List[TestCase] = []

    def add_test_case(self, test: TestCase):
        """Add test case to result"""
        self.test_cases.append(test)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "framework": self.test_framework,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration": self.duration,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "output": self.output[-2000:],  # Last 2000 chars
        }


class TestRunner:
    """Discover and execute tests"""

    def __init__(self, project_root: str):
        """Initialize test runner"""
        self.project_root = Path(project_root).resolve()
        self.test_framework = self._detect_test_framework()
        logger.info(f"Test framework detected: {self.test_framework}")

    def _detect_test_framework(self) -> str:
        """Detect test framework used"""
        # JavaScript/TypeScript
        if (self.project_root / "vitest.config.ts").exists() or (
            self.project_root / "vitest.config.js"
        ).exists():
            return "vitest"

        if (self.project_root / "jest.config.js").exists() or (
            self.project_root / "jest.config.json"
        ).exists():
            return "jest"

        if (self.project_root / "cypress.config.js").exists():
            return "cypress"

        # Python
        if (self.project_root / "pytest.ini").exists():
            return "pytest"

        if (self.project_root / "setup.cfg").exists():
            try:
                with open(self.project_root / "setup.cfg") as f:
                    if "[tool:pytest]" in f.read():
                        return "pytest"
            except Exception:
                pass

        # Rust
        if (self.project_root / "Cargo.toml").exists():
            return "cargo"

        return "unknown"

    def discover_tests(self) -> List[TestCase]:
        """Discover all tests in the project"""
        tests = []

        if self.test_framework == "jest" or self.test_framework == "vitest":
            tests = self._discover_jest_tests()
        elif self.test_framework == "pytest":
            tests = self._discover_pytest_tests()
        elif self.test_framework == "cargo":
            tests = self._discover_cargo_tests()

        logger.info(f"Discovered {len(tests)} tests")
        return tests

    def _discover_jest_tests(self) -> List[TestCase]:
        """Discover Jest/Vitest tests"""
        tests = []
        try:
            cmd = ["npm", "test", "--", "--listTests", "--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30,
            )

            if result.returncode == 0:
                try:
                    test_files = json.loads(result.stdout)
                    for file in test_files:
                        tests.append(TestCase(Path(file).name, file))
                except json.JSONDecodeError:
                    # Fallback: parse file paths from output
                    for line in result.stdout.split("\n"):
                        if line.strip() and (
                            line.endswith(".test.ts")
                            or line.endswith(".test.js")
                            or line.endswith(".spec.ts")
                            or line.endswith(".spec.js")
                        ):
                            tests.append(TestCase(Path(line).name, line))
        except Exception as e:
            logger.warning(f"Failed to discover Jest tests: {e}")

        return tests

    def _discover_pytest_tests(self) -> List[TestCase]:
        """Discover Pytest tests"""
        tests = []
        try:
            cmd = ["pytest", "--collect-only", "-q"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "::" in line:
                        # Format: "path/to/file.py::TestClass::test_method"
                        parts = line.split("::")
                        if len(parts) >= 2:
                            file = parts[0].strip()
                            test_name = "::".join(parts[1:])
                            tests.append(TestCase(test_name, file))
        except Exception as e:
            logger.warning(f"Failed to discover Pytest tests: {e}")

        return tests

    def _discover_cargo_tests(self) -> List[TestCase]:
        """Discover Cargo tests"""
        tests = []
        try:
            cmd = ["cargo", "test", "--", "--list"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=30,
            )

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if ": test" in line:
                        test_name = line.split(":")[0].strip()
                        tests.append(TestCase(test_name, ""))
        except Exception as e:
            logger.warning(f"Failed to discover Cargo tests: {e}")

        return tests

    def run_tests(self, filter: str = "", json_output: bool = True) -> TestResult:
        """
        Run tests.

        Args:
            filter: Test name filter (e.g., "LoginComponent" or "test_auth*")
            json_output: Try to get JSON output for better parsing

        Returns:
            TestResult with execution results
        """
        if self.test_framework == "jest" or self.test_framework == "vitest":
            return self._run_jest_tests(filter, json_output)
        elif self.test_framework == "pytest":
            return self._run_pytest_tests(filter, json_output)
        elif self.test_framework == "cargo":
            return self._run_cargo_tests(filter)
        else:
            return TestResult(
                success=False,
                test_framework="unknown",
                output="Unknown test framework",
            )

    def _run_jest_tests(self, filter: str = "", json_output: bool = True) -> TestResult:
        """Run Jest/Vitest tests"""
        cmd = ["npm", "test"]

        if filter:
            cmd.extend(["--", filter])

        if json_output:
            cmd.append("--json")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300,
            )

            # Try to parse JSON output
            if json_output:
                try:
                    output_json = json.loads(result.stdout)
                    return self._parse_jest_json(output_json, result)
                except json.JSONDecodeError:
                    pass

            # Fallback: parse text output
            return self._parse_jest_text(result)

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                test_framework=self.test_framework,
                output="Tests timed out after 5 minutes",
            )
        except Exception as e:
            return TestResult(
                success=False,
                test_framework=self.test_framework,
                output=str(e),
            )

    def _run_pytest_tests(self, filter: str = "", json_output: bool = True) -> TestResult:
        """Run Pytest tests"""
        cmd = ["pytest"]

        if filter:
            cmd.append(filter)

        if json_output:
            cmd.extend(["--json-report", "--json-report-file=/tmp/report.json"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300,
            )

            # Try to parse JSON report
            if json_output and Path("/tmp/report.json").exists():
                try:
                    with open("/tmp/report.json") as f:
                        output_json = json.load(f)
                        return self._parse_pytest_json(output_json)
                except Exception:
                    pass

            # Fallback: parse text output
            return self._parse_pytest_text(result)

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                test_framework="pytest",
                output="Tests timed out after 5 minutes",
            )
        except Exception as e:
            return TestResult(
                success=False,
                test_framework="pytest",
                output=str(e),
            )

    def _run_cargo_tests(self, filter: str = "") -> TestResult:
        """Run Cargo tests"""
        cmd = ["cargo", "test"]

        if filter:
            cmd.append(filter)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300,
            )

            return self._parse_cargo_text(result)

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                test_framework="cargo",
                output="Tests timed out after 5 minutes",
            )
        except Exception as e:
            return TestResult(
                success=False,
                test_framework="cargo",
                output=str(e),
            )

    def _parse_jest_json(self, output_json: Dict[str, Any], result) -> TestResult:
        """Parse Jest JSON output"""
        test_result = TestResult(
            success=result.returncode == 0,
            test_framework=self.test_framework,
            output=result.stdout + result.stderr,
        )

        # Extract summary
        summary = output_json.get("testResults", [])
        for test_file in summary:
            for assertion_result in test_file.get("assertionResults", []):
                status = "passed" if not assertion_result.get("failureMessages") else "failed"
                if assertion_result.get("status") == "skipped":
                    status = "skipped"

                test = TestCase(
                    name=assertion_result.get("fullName", ""),
                    file=test_file.get("name", ""),
                    status=status,
                )
                test.duration = assertion_result.get("duration", 0)
                if assertion_result.get("failureMessages"):
                    test.error = "\n".join(assertion_result["failureMessages"])

                test_result.add_test_case(test)

        # Extract stats
        stats = output_json.get("numTotalTests", 0)
        test_result.total = stats
        test_result.passed = output_json.get("numPassedTests", 0)
        test_result.failed = output_json.get("numFailedTests", 0)
        test_result.skipped = output_json.get("numPendingTests", 0)

        return test_result

    def _parse_jest_text(self, result) -> TestResult:
        """Parse Jest text output"""
        test_result = TestResult(
            success=result.returncode == 0,
            test_framework=self.test_framework,
            output=result.stdout + result.stderr,
        )

        # Simple parsing
        output = result.stdout + result.stderr
        if "failed" in output.lower():
            test_result.failed = 1
        if "passed" in output.lower():
            test_result.passed = 1

        return test_result

    def _parse_pytest_json(self, output_json: Dict[str, Any]) -> TestResult:
        """Parse Pytest JSON output"""
        test_result = TestResult(
            success=output_json.get("summary", {}).get("total_passed", 0) > 0,
            test_framework="pytest",
        )

        summary = output_json.get("summary", {})
        test_result.total = summary.get("total", 0)
        test_result.passed = summary.get("total_passed", 0)
        test_result.failed = summary.get("total_failed", 0)
        test_result.skipped = summary.get("total_skipped", 0)
        test_result.duration = summary.get("duration", 0)

        # Parse individual tests
        for test in output_json.get("tests", []):
            test_case = TestCase(
                name=test.get("nodeid", ""),
                file=test.get("file", ""),
                status=test.get("outcome", "unknown"),
            )
            test_case.duration = test.get("duration", 0)
            test_result.add_test_case(test_case)

        return test_result

    def _parse_pytest_text(self, result) -> TestResult:
        """Parse Pytest text output"""
        test_result = TestResult(
            success=result.returncode == 0,
            test_framework="pytest",
            output=result.stdout + result.stderr,
        )

        output = result.stdout + result.stderr
        # Very simple parsing
        for line in output.split("\n"):
            if " passed" in line:
                try:
                    num = int(line.split()[0])
                    test_result.passed = num
                except ValueError:
                    pass

        return test_result

    def _parse_cargo_text(self, result) -> TestResult:
        """Parse Cargo test output"""
        test_result = TestResult(
            success=result.returncode == 0,
            test_framework="cargo",
            output=result.stdout + result.stderr,
        )

        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if "test result: " in line:
                if "ok" in line:
                    test_result.success = True
                else:
                    test_result.success = False

        return test_result
