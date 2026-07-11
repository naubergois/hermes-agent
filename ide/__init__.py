"""
Hermes IDE Module

Provides Language Server Protocol integration, workspace management,
build system support, test execution, and result persistence for
a complete IDE experience.
"""

__version__ = "0.1.0"

from .lsp_bridge import LSPBridge
from .workspace_manager import WorkspaceManager
from .build_manager import BuildManager
from .test_runner import TestRunner
from .error_parser import ErrorParser

__all__ = [
    "LSPBridge",
    "WorkspaceManager",
    "BuildManager",
    "TestRunner",
    "ErrorParser",
]
