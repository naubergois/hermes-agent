"""
Language Server Protocol (LSP) Bridge

Integrates with language servers (TypeScript, Pyright, etc.) to provide:
- Symbol definition lookup (go-to-definition)
- Reference finding (find all uses)
- Type information (hover)
- Symbol search

This enables the agent to understand code structure without pattern matching.
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LSPError(Exception):
    """LSP communication error"""
    pass


class LSPBridge:
    """Connect to Language Servers via LSP protocol"""

    def __init__(self, project_root: str, language: str = "auto"):
        """
        Initialize LSP bridge.

        Args:
            project_root: Root directory of the project
            language: Language code ("typescript", "python", "auto")
        """
        self.project_root = Path(project_root).resolve()
        self.language = language if language != "auto" else self._detect_language()
        self.process: Optional[subprocess.Popen] = None
        self.message_id = 0
        self._init_id = None
        
        logger.info(f"Initializing LSP bridge for {self.language} at {self.project_root}")
        self._start_server()

    def _detect_language(self) -> str:
        """Auto-detect language based on project files"""
        if (self.project_root / "package.json").exists():
            return "typescript"  # or "javascript"
        elif (self.project_root / "pyproject.toml").exists():
            return "python"
        elif (self.project_root / "Cargo.toml").exists():
            return "rust"
        else:
            return "typescript"  # default

    def _start_server(self):
        """Start the appropriate language server"""
        if self.language in ("typescript", "javascript"):
            self._start_typescript_server()
        elif self.language == "python":
            self._start_python_server()
        else:
            raise LSPError(f"Unsupported language: {self.language}")

    def _start_typescript_server(self):
        """Start TypeScript Language Server"""
        try:
            # Try to use installed typescript-language-server
            cmd = [
                "node",
                "-e",
                "require('typescript-language-server/lib/cli').run()",
            ]
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root),
                text=False,
            )
            self._initialize_server()
            logger.info("TypeScript LSP server started")
        except FileNotFoundError:
            logger.warning("TypeScript LSP server not found, using fallback")
            self._use_fallback_typescript_search()

    def _start_python_server(self):
        """Start Python Language Server (Pyright)"""
        try:
            # Try to use pyright
            cmd = ["pyright", "--outputjson"]
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root),
                text=False,
            )
            self._initialize_server()
            logger.info("Python LSP server (Pyright) started")
        except FileNotFoundError:
            logger.warning("Pyright not found, using fallback")
            self._use_fallback_python_search()

    def _initialize_server(self):
        """Send LSP initialize request"""
        self._init_id = self._next_id()
        init_request = {
            "jsonrpc": "2.0",
            "id": self._init_id,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootPath": str(self.project_root),
                "rootUri": self.project_root.as_uri(),
                "capabilities": {
                    "textDocument": {
                        "synchronization": {"didSave": True},
                    }
                },
            },
        }
        try:
            self._send_request(init_request)
        except Exception as e:
            logger.warning(f"Failed to initialize LSP: {e}")

    def _next_id(self) -> int:
        """Get next message ID"""
        self.message_id += 1
        return self.message_id

    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to LSP server"""
        if not self.process:
            raise LSPError("LSP server not running")

        # Serialize request
        content = json.dumps(request)
        message = f"Content-Length: {len(content)}\r\n\r\n{content}"

        # Send to server
        try:
            self.process.stdin.write(message.encode())
            self.process.stdin.flush()
        except (BrokenPipeError, AttributeError) as e:
            raise LSPError(f"Failed to send request: {e}")

        # Read response
        try:
            response_headers = {}
            while True:
                line = self.process.stdout.readline().decode().strip()
                if not line:
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    response_headers[key.strip()] = value.strip()

            content_length = int(response_headers.get("Content-Length", 0))
            if content_length > 0:
                response_body = self.process.stdout.read(content_length).decode()
                return json.loads(response_body)
            return {}
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
            return {}

    def find_definition(
        self, file_path: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find where a symbol is defined (like Ctrl+F12 in VS Code).

        Args:
            file_path: Path to file containing the symbol
            line: Line number (1-indexed)
            column: Column number (1-indexed)

        Returns:
            Definition location or None if not found
        """
        if not self.process:
            return self._fallback_find_definition(file_path, line, column)

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": self._to_uri(file_path)},
                "position": {"line": line - 1, "character": column - 1},
            },
        }

        try:
            response = self._send_request(request)
            if "result" in response and response["result"]:
                result = response["result"]
                if isinstance(result, list):
                    result = result[0]
                return {
                    "file": self._from_uri(result["uri"]),
                    "line": result["range"]["start"]["line"] + 1,
                    "column": result["range"]["start"]["character"] + 1,
                }
            return None
        except Exception as e:
            logger.warning(f"LSP find_definition failed: {e}")
            return self._fallback_find_definition(file_path, line, column)

    def find_references(
        self, file_path: str, line: int, column: int
    ) -> List[Dict[str, Any]]:
        """
        Find all references to a symbol.

        Args:
            file_path: Path to file containing the symbol
            line: Line number (1-indexed)
            column: Column number (1-indexed)

        Returns:
            List of reference locations
        """
        if not self.process:
            return self._fallback_find_references(file_path, line, column)

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "textDocument/references",
            "params": {
                "textDocument": {"uri": self._to_uri(file_path)},
                "position": {"line": line - 1, "character": column - 1},
                "context": {"includeDeclaration": True},
            },
        }

        try:
            response = self._send_request(request)
            results = []
            if "result" in response and response["result"]:
                for ref in response["result"]:
                    results.append(
                        {
                            "file": self._from_uri(ref["uri"]),
                            "line": ref["range"]["start"]["line"] + 1,
                            "column": ref["range"]["start"]["character"] + 1,
                            "text": f"Line {ref['range']['start']['line'] + 1}",
                        }
                    )
            return results
        except Exception as e:
            logger.warning(f"LSP find_references failed: {e}")
            return self._fallback_find_references(file_path, line, column)

    def hover_info(
        self, file_path: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get type information on hover.

        Args:
            file_path: Path to file
            line: Line number (1-indexed)
            column: Column number (1-indexed)

        Returns:
            Hover information (type, documentation) or None
        """
        if not self.process:
            return None

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": self._to_uri(file_path)},
                "position": {"line": line - 1, "character": column - 1},
            },
        }

        try:
            response = self._send_request(request)
            if "result" in response and response["result"]:
                result = response["result"]
                contents = result.get("contents", {})
                if isinstance(contents, str):
                    return {"value": contents}
                elif isinstance(contents, dict):
                    return {"value": contents.get("value", "")}
            return None
        except Exception as e:
            logger.warning(f"LSP hover_info failed: {e}")
            return None

    def symbol_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols by name.

        Args:
            query: Symbol name to search for

        Returns:
            List of matching symbols
        """
        if not self.process:
            return self._fallback_symbol_search(query)

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "workspace/symbol",
            "params": {"query": query},
        }

        try:
            response = self._send_request(request)
            results = []
            if "result" in response and response["result"]:
                for symbol in response["result"]:
                    results.append(
                        {
                            "name": symbol.get("name"),
                            "kind": symbol.get("kind"),
                            "file": self._from_uri(symbol["location"]["uri"]),
                            "line": symbol["location"]["range"]["start"]["line"] + 1,
                            "column": symbol["location"]["range"]["start"]["character"] + 1,
                        }
                    )
            return results
        except Exception as e:
            logger.warning(f"LSP symbol_search failed: {e}")
            return self._fallback_symbol_search(query)

    def _fallback_find_definition(
        self, file_path: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """Fallback to regex search for definition"""
        logger.debug(f"Using fallback for find_definition in {file_path}:{line}:{column}")
        # This would use grep/ripgrep as fallback
        return None

    def _fallback_find_references(
        self, file_path: str, line: int, column: int
    ) -> List[Dict[str, Any]]:
        """Fallback to regex search for references"""
        logger.debug(f"Using fallback for find_references in {file_path}:{line}:{column}")
        return []

    def _fallback_symbol_search(self, query: str) -> List[Dict[str, Any]]:
        """Fallback to grep search"""
        logger.debug(f"Using fallback for symbol_search: {query}")
        return []

    def _use_fallback_typescript_search(self):
        """Mark that we're using fallback mode"""
        self.process = None

    def _use_fallback_python_search(self):
        """Mark that we're using fallback mode"""
        self.process = None

    def _to_uri(self, file_path: str) -> str:
        """Convert file path to URI"""
        return Path(file_path).resolve().as_uri()

    def _from_uri(self, uri: str) -> str:
        """Convert URI to file path"""
        if uri.startswith("file://"):
            return uri[7:]
        return uri

    def shutdown(self):
        """Shutdown the language server"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Failed to shutdown LSP server: {e}")
            finally:
                self.process = None

    def __del__(self):
        """Cleanup on deletion"""
        self.shutdown()
