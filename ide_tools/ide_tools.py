"""
IDE Tools for Hermes Agent

Exposes LSP, Workspace, Build, and Test functionality as tools
that the agent can call directly.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from tools.registry import registry
from ide.lsp_bridge import LSPBridge
from ide.workspace_manager import WorkspaceManager
from ide.build_manager import BuildManager
from ide.test_runner import TestRunner
from ide.error_parser import ErrorParser

logger = logging.getLogger(__name__)

# Tool implementations

def analyze_workspace(start_path: str = ".", **kwargs) -> str:
    """Analyze project workspace structure and build system"""
    try:
        manager = WorkspaceManager(start_path)
        result = manager.discover_workspace()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def find_definition(file_path: str, line: int, column: int, **kwargs) -> str:
    """Find symbol definition (like Ctrl+F12 in VS Code)"""
    try:
        bridge = LSPBridge(".", language="auto")
        result = bridge.find_definition(file_path, line, column)
        return json.dumps({"definition": result}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def find_references(file_path: str, line: int, column: int, **kwargs) -> str:
    """Find all references to a symbol"""
    try:
        bridge = LSPBridge(".", language="auto")
        results = bridge.find_references(file_path, line, column)
        return json.dumps({"references": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_symbols(query: str, **kwargs) -> str:
    """Search for symbols by name across the codebase"""
    try:
        bridge = LSPBridge(".", language="auto")
        results = bridge.symbol_search(query)
        return json.dumps({"symbols": results}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def build_project(target: str = "build", **kwargs) -> str:
    """Build the project"""
    try:
        manager = BuildManager(".")
        result = manager.build(target)
        return json.dumps(result.to_dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_tests(filter: str = "", **kwargs) -> str:
    """Run project tests with optional filter"""
    try:
        runner = TestRunner(".")
        result = runner.run_tests(filter)
        return json.dumps(result.to_dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def discover_tests(**kwargs) -> str:
    """Discover all tests in the project"""
    try:
        runner = TestRunner(".")
        tests = runner.discover_tests()
        return json.dumps([t.to_dict() for t in tests], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def parse_errors(output: str, error_type: str = "generic", **kwargs) -> str:
    """Parse build/test errors from output"""
    try:
        parser = ErrorParser(".")
        errors = parser.parse_output(output, error_type)
        return json.dumps([e.to_dict() for e in errors], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_build_info(**kwargs) -> str:
    """Get build system information"""
    try:
        manager = BuildManager(".")
        info = manager.get_build_info()
        return json.dumps(info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def lint_code(**kwargs) -> str:
    """Run linter on the project"""
    try:
        manager = BuildManager(".")
        result = manager.lint()
        return json.dumps(result.to_dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def format_code(**kwargs) -> str:
    """Format code in the project"""
    try:
        manager = BuildManager(".")
        result = manager.format_code()
        return json.dumps(result.to_dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Tool registration

registry.register(
    name="analyze_workspace",
    toolset="ide",
    schema={
        "name": "analyze_workspace",
        "description": "Analyze and understand project structure, build system, entry points, and test frameworks",
        "parameters": {
            "type": "object",
            "properties": {
                "start_path": {
                    "type": "string",
                    "description": "Path to start analysis from (default: current directory)",
                },
            },
        },
    },
    handler=lambda args, **kw: analyze_workspace(args.get("start_path", "."), **kw),
)

registry.register(
    name="find_definition",
    toolset="ide",
    schema={
        "name": "find_definition",
        "description": "Find where a symbol is defined (like Ctrl+F12 in VS Code)",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "line": {"type": "integer", "description": "Line number (1-indexed)"},
                "column": {"type": "integer", "description": "Column number (1-indexed)"},
            },
            "required": ["file_path", "line", "column"],
        },
    },
    handler=lambda args, **kw: find_definition(
        args.get("file_path"), args.get("line"), args.get("column"), **kw
    ),
)

registry.register(
    name="find_references",
    toolset="ide",
    schema={
        "name": "find_references",
        "description": "Find all references to a symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to file"},
                "line": {"type": "integer", "description": "Line number (1-indexed)"},
                "column": {"type": "integer", "description": "Column number (1-indexed)"},
            },
            "required": ["file_path", "line", "column"],
        },
    },
    handler=lambda args, **kw: find_references(
        args.get("file_path"), args.get("line"), args.get("column"), **kw
    ),
)

registry.register(
    name="search_symbols",
    toolset="ide",
    schema={
        "name": "search_symbols",
        "description": "Search for symbols by name across the codebase",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Symbol name to search for"},
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: search_symbols(args.get("query"), **kw),
)

registry.register(
    name="build_project",
    toolset="ide",
    schema={
        "name": "build_project",
        "description": "Build the project and return build results",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Build target (build, dev, release, etc.)",
                },
            },
        },
    },
    handler=lambda args, **kw: build_project(args.get("target", "build"), **kw),
)

registry.register(
    name="run_tests",
    toolset="ide",
    schema={
        "name": "run_tests",
        "description": "Run project tests with optional filter",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Test filter (e.g., 'LoginComponent' or 'test_auth*')",
                },
            },
        },
    },
    handler=lambda args, **kw: run_tests(args.get("filter", ""), **kw),
)

registry.register(
    name="discover_tests",
    toolset="ide",
    schema={
        "name": "discover_tests",
        "description": "Discover all tests in the project",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: discover_tests(**kw),
)

registry.register(
    name="parse_errors",
    toolset="ide",
    schema={
        "name": "parse_errors",
        "description": "Parse build/test errors from output string",
        "parameters": {
            "type": "object",
            "properties": {
                "output": {"type": "string", "description": "Error output to parse"},
                "error_type": {
                    "type": "string",
                    "description": "Error type (typescript, python, rust, go, generic)",
                },
            },
            "required": ["output"],
        },
    },
    handler=lambda args, **kw: parse_errors(
        args.get("output"), args.get("error_type", "generic"), **kw
    ),
)

registry.register(
    name="get_build_info",
    toolset="ide",
    schema={
        "name": "get_build_info",
        "description": "Get information about the build system",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: get_build_info(**kw),
)

registry.register(
    name="lint_code",
    toolset="ide",
    schema={
        "name": "lint_code",
        "description": "Run linter on the project code",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: lint_code(**kw),
)

registry.register(
    name="format_code",
    toolset="ide",
    schema={
        "name": "format_code",
        "description": "Format code in the project",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **kw: format_code(**kw),
)
