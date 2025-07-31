"""Example of new CLI usage with refactored architecture."""

import asyncio
import argparse
from typing import List

from mcp_validation.config.settings import ConfigurationManager, load_config_from_env
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.reporting.console import ConsoleReporter
from mcp_validation.reporting.json_report import JSONReporter


async def main():
    """Enhanced CLI with configurable validation."""
    parser = argparse.ArgumentParser(
        description="Validate MCP server protocol compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration Examples:
  # Use default comprehensive profile
  mcp-validate -- npx @dynatrace-oss/dynatrace-mcp-server
  
  # Use specific profile
  mcp-validate --profile security_focused -- python server.py
  
  # Use custom config file
  mcp-validate --config ./my-config.json -- node server.js
  
  # Override specific validators
  mcp-validate --enable ping --disable security -- ./server
  
  # List available profiles and validators
  mcp-validate --list-profiles
  mcp-validate --list-validators

Environment Variables:
  MCP_VALIDATION_CONFIG    - Path to configuration file
  MCP_VALIDATION_PROFILE   - Active profile name
        """
    )
    
    # Command arguments
    parser.add_argument(
        'command',
        nargs='*',
        help='Command and arguments to run the MCP server'
    )
    
    # Configuration options
    parser.add_argument(
        '--config', 
        metavar='FILE',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--profile',
        metavar='NAME', 
        help='Validation profile to use'
    )
    
    # Environment variables
    parser.add_argument(
        '--env',
        action='append',
        default=[],
        metavar='KEY=VALUE',
        help='Set environment variable (can be used multiple times)'
    )
    
    # Validator control
    parser.add_argument(
        '--enable',
        action='append',
        default=[],
        metavar='VALIDATOR',
        help='Enable specific validator'
    )
    
    parser.add_argument(
        '--disable', 
        action='append',
        default=[],
        metavar='VALIDATOR',
        help='Disable specific validator'
    )
    
    # Information commands
    parser.add_argument(
        '--list-profiles',
        action='store_true',
        help='List available validation profiles'
    )
    
    parser.add_argument(
        '--list-validators',
        action='store_true', 
        help='List available validators'
    )
    
    # Output options
    parser.add_argument(
        '--json-report',
        metavar='FILENAME',
        help='Export detailed JSON report to specified file'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output including warnings'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        metavar='SECONDS',
        help='Global timeout override'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config_manager = ConfigurationManager(args.config)
    else:
        config_manager = load_config_from_env()
    
    # Handle information commands
    if args.list_profiles:
        print("Available validation profiles:")
        for profile_name in config_manager.list_profiles():
            profile = config_manager.profiles[profile_name]
            print(f"  {profile_name}: {profile.description}")
        return
    
    orchestrator = MCPValidationOrchestrator(config_manager)
    
    if args.list_validators:
        print("Available validators:")
        for validator_name in orchestrator.registry.list_validators():
            validator = orchestrator.registry.create_validator(validator_name)
            if validator:
                print(f"  {validator_name}: {validator.description}")
        return
    
    # Validate command arguments
    if not args.command:
        parser.error("Command arguments required for validation")
    
    # Apply command-line overrides
    if args.profile:
        config_manager.set_active_profile(args.profile)
    
    # Override validator enables/disables
    active_profile = config_manager.get_active_profile()
    for validator_name in args.enable:
        if validator_name in active_profile.validators:
            active_profile.validators[validator_name].enabled = True
    
    for validator_name in args.disable:
        if validator_name in active_profile.validators:
            active_profile.validators[validator_name].enabled = False
    
    # Override timeout
    if args.timeout:
        active_profile.global_timeout = args.timeout
    
    # Parse environment variables
    env_vars = {}
    for env_arg in args.env:
        if '=' not in env_arg:
            parser.error(f"Environment variable must be in KEY=VALUE format: {env_arg}")
        key, value = env_arg.split('=', 1)
        env_vars[key] = value
    
    # Display what we're testing
    print(f"Testing MCP server: {' '.join(args.command)}")
    print(f"Using profile: {active_profile.name}")
    if env_vars:
        print("Environment variables:")
        for key, value in env_vars.items():
            display_value = value if len(value) < 20 else f"{value[:10]}..."
            print(f"  {key}={display_value}")
    print()
    
    # Run validation
    try:
        session = await orchestrator.validate_server(
            command_args=args.command,
            env_vars=env_vars,
            profile_name=args.profile
        )
        
        # Display results
        console_reporter = ConsoleReporter(verbose=args.verbose)
        console_reporter.report_session(session)
        
        # Generate JSON report if requested
        if args.json_report:
            json_reporter = JSONReporter()
            json_reporter.save_report(session, args.json_report, args.command, env_vars)
        
        # Exit with appropriate code
        exit_code = 0 if session.overall_success else 1
        return exit_code
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)