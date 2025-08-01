"""Enhanced CLI interface for MCP validation."""

import argparse
import asyncio
import sys
from typing import Dict, List

from ..config.settings import ConfigurationManager, load_config_from_env
from ..core.validator import MCPValidationOrchestrator
from ..reporting.console import ConsoleReporter, print_profile_info, print_validator_info
from ..reporting.json_report import JSONReporter


def parse_env_args(env_args: List[str]) -> Dict[str, str]:
    """Parse environment variable arguments in KEY=VALUE format."""
    env_vars = {}
    for env_arg in env_args:
        if "=" not in env_arg:
            raise ValueError(f"Environment variable must be in KEY=VALUE format: {env_arg}")
        key, value = env_arg.split("=", 1)
        env_vars[key] = value
    return env_vars


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the enhanced argument parser."""
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
        """,
    )

    # Command arguments
    parser.add_argument("command", nargs="*", help="Command and arguments to run the MCP server")

    # Configuration options
    parser.add_argument("--config", metavar="FILE", help="Configuration file path")

    parser.add_argument("--profile", metavar="NAME", help="Validation profile to use")

    # Environment variables
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set environment variable (can be used multiple times)",
    )

    # Validator control
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        metavar="VALIDATOR",
        help="Enable specific validator",
    )

    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="VALIDATOR",
        help="Disable specific validator",
    )

    # Information commands
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available validation profiles"
    )

    parser.add_argument("--list-validators", action="store_true", help="List available validators")

    # Output options
    parser.add_argument(
        "--json-report", metavar="FILENAME", help="Export detailed JSON report to specified file"
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed output including warnings"
    )

    parser.add_argument("--timeout", type=float, metavar="SECONDS", help="Global timeout override")

    # Security options
    parser.add_argument(
        "--skip-mcp-scan", action="store_true", help="Skip mcp-scan security analysis"
    )

    return parser


async def main():
    """Enhanced CLI entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        # Load configuration
        if args.config:
            config_manager = ConfigurationManager(args.config)
        else:
            config_manager = load_config_from_env()

        # Handle information commands
        if args.list_profiles:
            print_profile_info(config_manager)
            return 0

        orchestrator = MCPValidationOrchestrator(config_manager)

        if args.list_validators:
            print_validator_info(orchestrator)
            return 0

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
            else:
                print(f"Warning: Unknown validator '{validator_name}' - ignoring")

        for validator_name in args.disable:
            if validator_name in active_profile.validators:
                active_profile.validators[validator_name].enabled = False
            else:
                print(f"Warning: Unknown validator '{validator_name}' - ignoring")

        # Disable security if --skip-mcp-scan is used
        if args.skip_mcp_scan and "security" in active_profile.validators:
            active_profile.validators["security"].enabled = False

        # Override timeout
        if args.timeout:
            active_profile.global_timeout = args.timeout

        # Parse environment variables
        env_vars = parse_env_args(args.env) if args.env else None

        # Display what we're testing
        print(f"Testing MCP server: {' '.join(args.command)}")
        print(f"Using profile: {active_profile.name}")
        if env_vars:
            print("Environment variables:")
            for key, value in env_vars.items():
                # Mask potential secrets in output
                display_value = value if len(value) < 20 else f"{value[:10]}..."
                print(f"  {key}={display_value}")
        print()

        # Run validation
        session = await orchestrator.validate_server(
            command_args=args.command, env_vars=env_vars, profile_name=args.profile
        )

        # Display results
        console_reporter = ConsoleReporter(verbose=args.verbose)
        console_reporter.report_session(session)

        # Generate JSON report if requested
        if args.json_report:
            json_reporter = JSONReporter()
            json_reporter.save_report(session, args.json_report, args.command, env_vars)

        # Exit with appropriate code
        return 0 if session.overall_success else 1

    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cli_main():
    """Synchronous entry point for CLI script."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
