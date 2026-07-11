"""
Workspace Manager

Auto-discovers and analyzes project structure:
- Project root and type (Node.js, Python, Rust, Go, etc.)
- Build system and available commands
- Package managers
- Programming languages used
- Entry points
- Test frameworks
- Directory structure
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Discover and analyze project structure"""

    # Project markers to find root
    PROJECT_MARKERS = [
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        ".git",
    ]

    # Build system detection
    BUILD_SYSTEM_MAP = {
        "package.json": "nodejs",
        "pyproject.toml": "python",
        "setup.py": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "Makefile": "make",
    }

    def __init__(self, start_path: str = "."):
        """Initialize workspace manager"""
        self.start_path = Path(start_path).resolve()
        self.project_root = self._find_project_root()
        logger.info(f"Workspace root: {self.project_root}")

    def _find_project_root(self) -> Path:
        """Traverse up until we find a project marker"""
        current = self.start_path
        while current != current.parent:
            if any((current / marker).exists() for marker in self.PROJECT_MARKERS):
                return current
            current = current.parent
        return self.start_path

    def discover_workspace(self) -> Dict[str, Any]:
        """
        Discover complete workspace information.

        Returns:
            Dictionary with project metadata
        """
        return {
            "root": str(self.project_root),
            "type": self._detect_project_type(),
            "build_system": self._detect_build_system(),
            "package_managers": self._detect_package_managers(),
            "languages": self._detect_languages(),
            "entry_points": self._find_entry_points(),
            "test_frameworks": self._detect_test_frameworks(),
            "structure": self._analyze_structure(),
        }

    def _detect_project_type(self) -> str:
        """Detect project type (nodejs, python, rust, go, etc.)"""
        if (self.project_root / "package.json").exists():
            return "nodejs"
        elif (self.project_root / "pyproject.toml").exists():
            return "python"
        elif (self.project_root / "setup.py").exists():
            return "python"
        elif (self.project_root / "Cargo.toml").exists():
            return "rust"
        elif (self.project_root / "go.mod").exists():
            return "go"
        elif (self.project_root / "pom.xml").exists():
            return "maven"
        elif (self.project_root / "build.gradle").exists():
            return "gradle"
        else:
            return "unknown"

    def _detect_build_system(self) -> Dict[str, str]:
        """Detect build commands available"""
        build_commands = {}

        # Node.js
        if (self.project_root / "package.json").exists():
            try:
                with open(self.project_root / "package.json") as f:
                    pkg = json.load(f)
                    if "scripts" in pkg:
                        scripts = pkg["scripts"]
                        build_commands["build"] = scripts.get("build", "npm run build")
                        build_commands["dev"] = scripts.get("dev", "npm run dev")
                        build_commands["test"] = scripts.get("test", "npm test")
                        build_commands["start"] = scripts.get("start", "npm start")
                        build_commands["lint"] = scripts.get("lint", "npm run lint")
                        build_commands["format"] = scripts.get("format", "npm run format")
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")
                build_commands = {
                    "build": "npm run build",
                    "test": "npm test",
                    "dev": "npm run dev",
                }

        # Python
        elif (self.project_root / "pyproject.toml").exists():
            build_commands = {
                "build": "pip install -e .",
                "test": "pytest",
                "dev": "pip install -e '.[dev]'",
                "format": "black .",
                "lint": "pylint .",
            }

        # Rust
        elif (self.project_root / "Cargo.toml").exists():
            build_commands = {
                "build": "cargo build",
                "test": "cargo test",
                "dev": "cargo build",
                "format": "cargo fmt",
                "lint": "cargo clippy",
            }

        # Go
        elif (self.project_root / "go.mod").exists():
            build_commands = {
                "build": "go build",
                "test": "go test ./...",
                "format": "gofmt -w .",
                "lint": "golangci-lint run",
            }

        return build_commands

    def _detect_package_managers(self) -> List[str]:
        """Detect package managers used"""
        managers = []
        
        if (self.project_root / "package.json").exists():
            managers.append("npm")
            if (self.project_root / "pnpm-lock.yaml").exists():
                managers.append("pnpm")
            elif (self.project_root / "yarn.lock").exists():
                managers.append("yarn")
        
        if (self.project_root / "pyproject.toml").exists():
            managers.append("pip")
            if (self.project_root / "poetry.lock").exists():
                managers.append("poetry")
            elif (self.project_root / "Pipfile").exists():
                managers.append("pipenv")
        
        if (self.project_root / "Cargo.lock").exists():
            managers.append("cargo")
        
        if (self.project_root / "go.sum").exists():
            managers.append("go")

        return managers

    def _detect_languages(self) -> List[str]:
        """Detect programming languages used"""
        languages = set()

        # Check for file extensions
        extensions = {}
        for path in self.project_root.rglob("*"):
            if path.is_file() and not path.name.startswith("."):
                ext = path.suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1

        # Map extensions to languages
        ext_to_lang = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".py": "python",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".cpp": "cpp",
            ".c": "c",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".m": "objective-c",
            ".scala": "scala",
        }

        for ext, lang in ext_to_lang.items():
            if ext in extensions and extensions[ext] > 5:  # Threshold
                languages.add(lang)

        return sorted(list(languages))

    def _find_entry_points(self) -> List[str]:
        """Find likely entry points"""
        entry_points = []

        # Node.js
        if (self.project_root / "package.json").exists():
            try:
                with open(self.project_root / "package.json") as f:
                    pkg = json.load(f)
                    if "main" in pkg:
                        entry_points.append(pkg["main"])
                    if "bin" in pkg:
                        if isinstance(pkg["bin"], dict):
                            entry_points.extend(pkg["bin"].values())
                        elif isinstance(pkg["bin"], str):
                            entry_points.append(pkg["bin"])
            except Exception:
                pass

            # Check common locations
            for path in [
                "src/index.ts",
                "src/index.js",
                "src/main.tsx",
                "src/main.ts",
                "index.js",
                "index.ts",
            ]:
                if (self.project_root / path).exists():
                    entry_points.append(path)

        # Python
        if (self.project_root / "pyproject.toml").exists():
            try:
                with open(self.project_root / "pyproject.toml") as f:
                    content = f.read()
                    # Simple TOML parse for entry-points
                    if "[project.scripts]" in content or "[tool.poetry.scripts]" in content:
                        entry_points.append("pyproject.toml")
            except Exception:
                pass

            # Check common locations
            for path in ["src/main.py", "main.py", "app.py", "cli.py"]:
                if (self.project_root / path).exists():
                    entry_points.append(path)

        return entry_points

    def _detect_test_frameworks(self) -> List[str]:
        """Detect test frameworks"""
        frameworks = []

        # JavaScript/TypeScript
        if (self.project_root / "jest.config.js").exists():
            frameworks.append("jest")
        if (self.project_root / "jest.config.json").exists():
            frameworks.append("jest")
        if (self.project_root / "vitest.config.ts").exists():
            frameworks.append("vitest")
        if (self.project_root / "vitest.config.js").exists():
            frameworks.append("vitest")
        if (self.project_root / "cypress.config.js").exists():
            frameworks.append("cypress")
        if (self.project_root / "playwright.config.ts").exists():
            frameworks.append("playwright")

        # Python
        if (self.project_root / "pytest.ini").exists():
            frameworks.append("pytest")
        if (self.project_root / "setup.cfg").exists():
            frameworks.append("pytest")
        if (self.project_root / "tox.ini").exists():
            frameworks.append("tox")

        # Rust
        if (self.project_root / "Cargo.toml").exists():
            frameworks.append("cargo test")

        return frameworks

    def _analyze_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze directory structure"""
        ignored_dirs = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".tox",
            "target",
            ".next",
            "out",
            "__pycache__",
            ".mypy_cache",
            ".parcel-cache",
            ".turbo",
            "coverage",
        }

        ignored_files = {
            ".DS_Store",
            "*.log",
            ".env",
            ".env.local",
        }

        def scan(path: Path, depth: int = 0) -> Dict[str, Any]:
            if depth > max_depth:
                return {}

            result = {}
            try:
                for item in sorted(path.iterdir()):
                    # Skip hidden files except important ones
                    if item.name.startswith("."):
                        if item.name not in {".github", ".env.example"}:
                            continue

                    if item.name in ignored_dirs:
                        continue

                    if item.is_dir():
                        result[item.name] = scan(item, depth + 1)
                    else:
                        result[item.name] = "file"
            except PermissionError:
                pass

            return result

        return scan(self.project_root)

    def get_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific configuration file"""
        configs = {
            "package.json": self.project_root / "package.json",
            "pyproject.toml": self.project_root / "pyproject.toml",
            "tsconfig.json": self.project_root / "tsconfig.json",
            "cargo.toml": self.project_root / "Cargo.toml",
            "go.mod": self.project_root / "go.mod",
        }

        config_path = configs.get(name.lower())
        if config_path and config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to parse {name}: {e}")
                return None
        return None
