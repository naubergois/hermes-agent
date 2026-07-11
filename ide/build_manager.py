"""
Build Manager

Handles build system integration:
- Automatic build command detection
- Build execution with progress tracking
- Artifact management
- Incremental builds
- Build error detection and reporting
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BuildResult:
    """Result of a build"""

    def __init__(
        self,
        success: bool,
        command: str,
        stdout: str,
        stderr: str,
        duration: float,
        artifacts: List[str] = None,
    ):
        self.success = success
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.artifacts = artifacts or []
        self.errors = self._parse_errors()

    def _parse_errors(self) -> List[Dict[str, Any]]:
        """Parse build errors from output"""
        errors = []
        output = self.stderr + self.stdout

        # TypeScript errors
        for line in output.split("\n"):
            if " error TS" in line:
                errors.append({
                    "type": "typescript",
                    "message": line.strip(),
                })
            # Python errors
            elif " error: " in line.lower():
                errors.append({
                    "type": "python",
                    "message": line.strip(),
                })
            # Generic errors
            elif line.strip().startswith("error:"):
                errors.append({
                    "type": "generic",
                    "message": line.strip(),
                })

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "command": self.command,
            "duration": self.duration,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "stdout": self.stdout[-1000:],  # Last 1000 chars
            "stderr": self.stderr[-1000:],  # Last 1000 chars
        }


class BuildManager:
    """Manage project builds"""

    def __init__(self, project_root: str):
        """Initialize build manager"""
        self.project_root = Path(project_root).resolve()
        self.build_system = self._detect_build_system()
        logger.info(f"Build system: {self.build_system}")

    def _detect_build_system(self) -> str:
        """Detect the build system"""
        if (self.project_root / "package.json").exists():
            return "npm"
        elif (self.project_root / "pyproject.toml").exists():
            return "pip"
        elif (self.project_root / "setup.py").exists():
            return "pip"
        elif (self.project_root / "Cargo.toml").exists():
            return "cargo"
        elif (self.project_root / "go.mod").exists():
            return "go"
        elif (self.project_root / "Makefile").exists():
            return "make"
        else:
            return "unknown"

    def build(self, target: str = "build") -> BuildResult:
        """
        Execute build command.

        Args:
            target: Build target (build, dev, test, etc.)

        Returns:
            BuildResult with success status and artifacts
        """
        command = self._get_build_command(target)
        if not command:
            return BuildResult(
                success=False,
                command="",
                stdout="",
                stderr=f"Unknown build target: {target}",
                duration=0,
            )

        logger.info(f"Running build: {command}")
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=300,  # 5 minute timeout
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            # Find artifacts
            artifacts = self._find_artifacts(target)

            return BuildResult(
                success=success,
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                artifacts=artifacts,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                command=command,
                stdout="",
                stderr="Build timed out after 5 minutes",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                command=command,
                stdout="",
                stderr=str(e),
                duration=duration,
            )

    def _get_build_command(self, target: str) -> Optional[str]:
        """Get build command for target"""
        target = target.lower()

        if self.build_system == "npm":
            commands = {
                "build": "npm run build",
                "dev": "npm run dev",
                "test": "npm test",
                "lint": "npm run lint",
                "format": "npm run format",
                "clean": "npm run clean",
            }
            return commands.get(target)

        elif self.build_system == "pip":
            commands = {
                "build": "pip install -e .",
                "dev": "pip install -e '.[dev]'",
                "test": "pytest",
                "lint": "pylint .",
                "format": "black .",
                "clean": "rm -rf build dist *.egg-info",
            }
            return commands.get(target)

        elif self.build_system == "cargo":
            commands = {
                "build": "cargo build",
                "dev": "cargo build",
                "test": "cargo test",
                "lint": "cargo clippy",
                "format": "cargo fmt",
                "clean": "cargo clean",
                "release": "cargo build --release",
            }
            return commands.get(target)

        elif self.build_system == "go":
            commands = {
                "build": "go build -o app",
                "dev": "go build",
                "test": "go test ./...",
                "lint": "golangci-lint run",
                "format": "gofmt -w .",
                "clean": "go clean",
            }
            return commands.get(target)

        elif self.build_system == "make":
            commands = {
                "build": "make build",
                "dev": "make dev",
                "test": "make test",
                "clean": "make clean",
            }
            return commands.get(target)

        return None

    def _find_artifacts(self, target: str) -> List[str]:
        """Find build artifacts"""
        artifacts = []

        if self.build_system == "npm":
            artifact_dirs = ["dist", "build", "out", ".next"]
            for artifact_dir in artifact_dirs:
                if (self.project_root / artifact_dir).exists():
                    artifacts.append(artifact_dir)

        elif self.build_system == "pip":
            artifact_dirs = ["dist", "build"]
            for artifact_dir in artifact_dirs:
                if (self.project_root / artifact_dir).exists():
                    artifacts.append(artifact_dir)

        elif self.build_system == "cargo":
            target_dir = self.project_root / "target"
            if target_dir.exists():
                artifacts.append(str(target_dir))

        return artifacts

    def get_build_info(self) -> Dict[str, Any]:
        """Get build system information"""
        return {
            "system": self.build_system,
            "root": str(self.project_root),
            "targets": self._get_available_targets(),
            "artifacts": self._find_artifacts("build"),
        }

    def _get_available_targets(self) -> List[str]:
        """Get available build targets"""
        targets = []

        if self.build_system == "npm":
            try:
                with open(self.project_root / "package.json") as f:
                    pkg = json.load(f)
                    if "scripts" in pkg:
                        targets = list(pkg["scripts"].keys())
            except Exception:
                pass

        elif self.build_system == "cargo":
            targets = ["build", "test", "release", "clean"]

        else:
            targets = ["build", "test", "clean"]

        return targets

    def clean(self) -> BuildResult:
        """Clean build artifacts"""
        return self.build("clean")

    def test(self) -> BuildResult:
        """Run tests"""
        return self.build("test")

    def lint(self) -> BuildResult:
        """Run linter"""
        return self.build("lint")

    def format_code(self) -> BuildResult:
        """Format code"""
        return self.build("format")
