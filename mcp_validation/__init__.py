"""MCP validation framework.

This package provides both a modern plugin-based validation framework
and backward compatibility with the original validation API.
"""

import asyncio
from typing import List, Dict, Any, Optional

# New modular architecture
from .core.validator import MCPValidationOrchestrator, ValidatorRegistry
from .core.result import ValidationSession, MCPValidationResult, ValidatorResult, ValidationContext
from .core.transport import JSONRPCTransport
from .config.settings import ConfigurationManager, ValidationProfile, ValidatorConfig, load_config_from_env
from .validators.base import BaseValidator
from .reporting.console import ConsoleReporter
from .reporting.json_report import JSONReporter
from .cli.main import main as cli_main

# Backward compatibility imports
from .legacy import MCPServerValidator, validate_mcp_server_command, generate_json_report, save_json_report

__version__ = "2.0.0"

# New API exports
__all__ = [
    # Core components
    'MCPValidationOrchestrator',
    'ValidatorRegistry',
    'ValidationSession',
    'MCPValidationResult',
    'ValidatorResult',
    'ValidationContext',
    'JSONRPCTransport',
    
    # Configuration
    'ConfigurationManager',
    'ValidationProfile', 
    'ValidatorConfig',
    'load_config_from_env',
    
    # Validators
    'BaseValidator',
    
    # Reporting
    'ConsoleReporter',
    'JSONReporter',
    
    # CLI
    'cli_main',
    
    # Legacy compatibility
    'MCPServerValidator',
    'validate_mcp_server_command',
    'generate_json_report',
    'save_json_report',
]


# Convenience function for simple validation
async def validate_server(
    command_args: List[str], 
    env_vars: Optional[Dict[str, str]] = None,
    profile_name: Optional[str] = None,
    config_file: Optional[str] = None
) -> ValidationSession:
    """
    Simple validation function using the new architecture.
    
    Args:
        command_args: Command and arguments to execute the MCP server
        env_vars: Optional environment variables
        profile_name: Validation profile to use (defaults to 'comprehensive')
        config_file: Path to configuration file
    
    Returns:
        ValidationSession with results
    """
    if config_file:
        config_manager = ConfigurationManager(config_file)
    else:
        config_manager = load_config_from_env()
    
    if profile_name:
        config_manager.set_active_profile(profile_name)
    
    orchestrator = MCPValidationOrchestrator(config_manager)
    return await orchestrator.validate_server(command_args, env_vars, profile_name)