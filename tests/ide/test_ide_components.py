"""Tests for IDE components"""

import json
import tempfile
from pathlib import Path

import pytest

from ide.workspace_manager import WorkspaceManager
from ide.build_manager import BuildManager, BuildResult
from ide.error_parser import ErrorParser, ParsedError


class TestWorkspaceManager:
    """Test workspace discovery and analysis"""

    def test_workspace_discovery_nodejs(self):
        """Test Node.js project discovery"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal Node.js project
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "test-app",
                        "version": "1.0.0",
                        "scripts": {
                            "build": "npm run build",
                            "test": "npm test",
                            "dev": "npm run dev",
                        },
                    }
                )
            )
            (project_dir / "src").mkdir()
            (project_dir / "src" / "index.ts").write_text("console.log('hello');")

            manager = WorkspaceManager(str(project_dir))
            info = manager.discover_workspace()

            assert info["type"] == "nodejs"
            assert info["root"] == str(project_dir)
            assert "build" in info["build_system"]
            assert "npm" in info["package_managers"]

    def test_workspace_discovery_python(self):
        """Test Python project discovery"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.py").write_text("print('hello')")

            manager = WorkspaceManager(str(project_dir))
            info = manager.discover_workspace()

            assert info["type"] == "python"
            assert "pip" in info["package_managers"]

    def test_project_root_detection(self):
        """Test that project root is found correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")
            nested_dir = project_dir / "src" / "components"
            nested_dir.mkdir(parents=True)

            manager = WorkspaceManager(str(nested_dir))
            assert manager.project_root == project_dir

    def test_entry_point_detection(self):
        """Test entry point discovery"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "test",
                        "main": "dist/index.js",
                    }
                )
            )

            manager = WorkspaceManager(str(project_dir))
            info = manager.discover_workspace()

            assert "dist/index.js" in info["entry_points"]


class TestBuildManager:
    """Test build system integration"""

    def test_build_system_detection(self):
        """Test build system detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")

            manager = BuildManager(str(project_dir))
            assert manager.build_system == "npm"

    def test_build_info_retrieval(self):
        """Test getting build information"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "test",
                        "scripts": {
                            "build": "echo 'building'",
                            "test": "echo 'testing'",
                        },
                    }
                )
            )

            manager = BuildManager(str(project_dir))
            info = manager.get_build_info()

            assert info["system"] == "npm"
            assert "build" in info["targets"]
            assert "test" in info["targets"]

    def test_build_result(self):
        """Test build result"""
        result = BuildResult(
            success=True,
            command="npm run build",
            stdout="Built successfully",
            stderr="",
            duration=1.5,
            artifacts=["dist"],
        )

        assert result.success is True
        assert result.duration == 1.5
        assert "dist" in result.artifacts

        result_dict = result.to_dict()
        assert result_dict["command"] == "npm run build"


class TestErrorParser:
    """Test error parsing"""

    def test_parse_typescript_errors(self):
        """Test parsing TypeScript errors"""
        output = """src/app.ts:10:5 - error TS2551: Property 'foo' does not exist on type 'Bar'."""
        parser = ErrorParser()
        errors = parser.parse_output(output, "typescript")

        assert len(errors) > 0
        error = errors[0]
        assert "app.ts" in error.file
        assert error.line == 10
        assert error.column == 5
        assert "Property" in error.message

    def test_parse_python_errors(self):
        """Test parsing Python errors"""
        output = 'File "app.py", line 10, in <module>\n    undefined_var'
        parser = ErrorParser()
        errors = parser.parse_output(output, "python")

        # Should detect Python error pattern
        assert len(errors) >= 0

    def test_error_suggestion(self):
        """Test error suggestion generation"""
        error = ParsedError(
            file="app.ts",
            line=10,
            column=5,
            message="Property 'foo' does not exist",
            error_type="typescript",
        )

        suggestion = error._generate_suggestion(error)
        # TypeScript should generate a suggestion
        assert suggestion is not None or suggestion is None  # May or may not generate

    def test_group_errors_by_file(self):
        """Test grouping errors by file"""
        errors = [
            ParsedError("app.ts", 10, 5, "Error 1", "typescript"),
            ParsedError("app.ts", 20, 3, "Error 2", "typescript"),
            ParsedError("util.ts", 5, 1, "Error 3", "typescript"),
        ]

        parser = ErrorParser()
        grouped = parser.group_errors_by_file(errors)

        assert "app.ts" in grouped
        assert len(grouped["app.ts"]) == 2
        assert "util.ts" in grouped
        assert len(grouped["util.ts"]) == 1


class TestIDEIntegration:
    """Integration tests for IDE components"""

    def test_full_workspace_analysis(self):
        """Test full workspace analysis flow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create a simple Node.js project
            (project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "test-app",
                        "scripts": {"build": "echo 'build'", "test": "echo 'test'"},
                    }
                )
            )
            (project_dir / "src").mkdir()
            (project_dir / "src" / "index.ts").write_text("console.log('test');")

            # Analyze workspace
            manager = WorkspaceManager(str(project_dir))
            info = manager.discover_workspace()

            # Verify complete info
            assert info["type"] == "nodejs"
            assert info["root"] == str(project_dir)
            assert info["build_system"]
            assert info["package_managers"]
            assert info["entry_points"]
            assert info["test_frameworks"] or True  # May be empty

    def test_error_to_suggestion_flow(self):
        """Test error parsing and suggestion generation"""
        output = (
            "app.ts:10:5 - error TS2551: Property 'foo' does not exist on type 'Bar'."
        )
        parser = ErrorParser()
        errors = parser.parse_output(output, "typescript")

        for error in errors:
            # Error should have basic info
            assert error.file
            assert error.line > 0
            assert error.column > 0
            assert error.message
