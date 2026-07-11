"""
Base class and utilities for gateway extensions.

This module provides the foundation for breaking up GatewayRunner's
responsibilities into separate, focused modules. Each extension handles
a specific domain (voice, telegram topics, etc.) and receives access to
shared runner state via dependency injection.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class GatewayExtension(ABC):
    """Base class for gateway functionality extensions.
    
    Extensions are initialized with a reference to the parent GatewayRunner,
    allowing them to:
    - Access shared state (adapters, session_store, etc.)
    - Make async calls via the runner's event loop
    - Register callbacks or watchers
    
    This pattern enables breaking up the monolithic GatewayRunner into
    focused, testable modules without circular imports.
    """
    
    def __init__(self, runner: "GatewayRunner") -> None:
        """Initialize extension with runner context.
        
        Args:
            runner: The parent GatewayRunner instance providing shared state.
        """
        self.runner = runner
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize extension state.
        
        Called once during GatewayRunner startup. Use for loading
        persistent state, registering callbacks, etc.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up extension resources.
        
        Called during GatewayRunner shutdown. Use for persisting state,
        closing connections, etc.
        """
        pass
    
    def _check_adapter_capability(
        self, platform: Any, capability: str
    ) -> bool:
        """Check if an adapter supports a specific capability.
        
        Args:
            platform: Platform enum value
            capability: Method/attribute name to check
            
        Returns:
            True if adapter has the capability, False otherwise.
        """
        adapter = self.runner.adapters.get(platform)
        return hasattr(adapter, capability) if adapter else False
    
    def _get_adapter(self, platform: Any) -> Optional[Any]:
        """Get adapter for platform, if it exists."""
        return self.runner.adapters.get(platform)
    
    def _get_session_store(self) -> Any:
        """Get the runner's session store."""
        return self.runner.session_store
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from runner's loaded config."""
        if hasattr(self.runner, "config") and isinstance(self.runner.config, dict):
            return self.runner.config.get(key, default)
        return default


class CommandExtension(GatewayExtension):
    """Base class for extensions that handle slash commands.
    
    Subclasses should implement command handlers that are registered
    with the parent runner during initialize().
    """
    
    async def initialize(self) -> None:
        """Default: no-op. Subclasses override to register handlers."""
        pass
    
    async def shutdown(self) -> None:
        """Default: no-op. Subclasses override to clean up."""
        pass
    
    def register_command_handler(
        self,
        command_name: str,
        handler: callable,
        gateway_only: bool = False,
    ) -> None:
        """Register a slash command handler with the runner.
        
        This is a placeholder for future integration. Currently this is
        documented as a pattern; actual wiring happens in GatewayRunner.
        
        Args:
            command_name: Name of the command (without /)
            handler: Async callable(event: MessageEvent) -> str
            gateway_only: If True, command is only available in gateway
        """
        # Future: wire into runner's command dispatch
        pass


class WatcherExtension(GatewayExtension):
    """Base class for extensions that run async watchers (like cron).
    
    Watchers are long-lived coroutines that run during gateway lifetime.
    """
    
    async def initialize(self) -> None:
        """Default: schedule all registered watchers."""
        pass
    
    async def shutdown(self) -> None:
        """Default: cancel all registered watchers."""
        pass
    
    async def register_watcher(
        self,
        coro,
        name: str = "watcher",
    ) -> None:
        """Register an async watcher to run during gateway lifetime.
        
        This is a placeholder; actual scheduling is done by GatewayRunner.
        
        Args:
            coro: Async coroutine to schedule
            name: Friendly name for logging
        """
        # Future: wire into runner's task scheduling
        pass
