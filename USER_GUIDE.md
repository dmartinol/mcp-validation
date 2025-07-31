# MCP Validation Framework - User Guide

A modern, plugin-based validation framework for MCP (Model Context Protocol) servers. Provides comprehensive testing of protocol compliance, capabilities, and security.

## Features

### 🏗️ Modular Architecture
- **Plugin-based validators**: Each validation type is a separate, configurable plugin
- **Flexible configuration**: Multiple validation profiles with customizable parameters
- **Dependency management**: Validators can depend on each other and run in optimal order
- **Transport abstraction**: Clean separation between communication and validation logic

### ⚙️ Configuration System
- **Validation profiles**: Pre-configured validation suites for different use cases
- **Runtime configuration**: Override settings via CLI, environment, or config files
- **Extensible validators**: Easy to add custom validation logic

### 📊 Enhanced Reporting
- **Structured results**: Clear separation of different validation aspects
- **Multiple output formats**: Console and JSON reporting with detailed breakdown
- **Progress tracking**: Real-time feedback during validation execution

## Quick Start

### Basic Usage

```bash
# Validate an MCP server
mcp-validate -- npx @dynatrace-oss/dynatrace-mcp-server

# With environment variables
mcp-validate --env DT_ENVIRONMENT=https://example.apps.dynatrace.com -- npx server

# With custom timeout
mcp-validate --timeout 60 -- python my_server.py
```

### Validation Profiles

```bash
# Use a specific validation profile
mcp-validate --profile basic -- python server.py
mcp-validate --profile security_focused -- node server.js
mcp-validate --profile comprehensive -- ./my-server
```

### Validator Control

```bash
# Enable/disable specific validators
mcp-validate --enable ping --disable security -- python server.py
mcp-validate --disable errors -- ./server  # Skip error compliance testing
```

### Configuration Files

```bash
# Use a custom configuration file
mcp-validate --config ./my-validation-config.json -- python server.py

# Set config via environment
export MCP_VALIDATION_CONFIG=./config.json
export MCP_VALIDATION_PROFILE=development
mcp-validate -- python server.py
```

### Information Commands

```bash
# List available profiles
mcp-validate --list-profiles

# List available validators
mcp-validate --list-validators
```

## Built-in Validation Profiles

### `basic`
- **Purpose**: Quick protocol compliance check
- **Validators**: protocol, capabilities
- **Use case**: Development and CI/CD pipelines

### `comprehensive` (default)
- **Purpose**: Complete validation with all features
- **Validators**: protocol, capabilities, ping, errors, security
- **Use case**: Thorough testing before release

### `security_focused`
- **Purpose**: Security-first validation
- **Validators**: protocol, errors (strict), security (required)
- **Use case**: Security audits and compliance

### `development`
- **Purpose**: Developer-friendly validation
- **Validators**: protocol, capabilities, ping, errors
- **Features**: Detailed feedback, continues on failure
- **Use case**: Local development and debugging

## Built-in Validators

### `protocol` (Required)
- **Purpose**: Basic MCP protocol compliance
- **Tests**: Initialize handshake, protocol version, server info
- **Dependencies**: None (foundation validator)

### `capabilities`
- **Purpose**: Test advertised server capabilities
- **Tests**: tools/list, prompts/list, resources/list
- **Dependencies**: protocol

### `ping`
- **Purpose**: Test optional ping functionality
- **Tests**: Ping request/response, response time measurement
- **Dependencies**: protocol

### `errors`
- **Purpose**: JSON-RPC error compliance testing
- **Tests**: Invalid method handling, malformed request handling
- **Dependencies**: protocol

### `security`
- **Purpose**: Security analysis using mcp-scan
- **Tests**: Vulnerability scanning, tool analysis
- **Dependencies**: protocol

## Configuration

### Configuration File Format

Create a `.mcp-validation.json` file:

```json
{
  "active_profile": "custom",
  "profiles": {
    "custom": {
      "description": "My custom validation profile",
      "global_timeout": 30.0,
      "continue_on_failure": true,
      "validators": {
        "protocol": {
          "enabled": true,
          "required": true
        },
        "ping": {
          "enabled": true,
          "required": false,
          "parameters": {
            "max_response_time_ms": 500
          }
        },
        "security": {
          "enabled": true,
          "required": false,
          "parameters": {
            "run_mcp_scan": true,
            "vulnerability_threshold": "medium",
            "save_scan_results": true
          }
        }
      }
    }
  }
}
```

### Environment Variables

```bash
export MCP_VALIDATION_CONFIG=./config.json    # Path to configuration file
export MCP_VALIDATION_PROFILE=development     # Active profile name
```

### Validator Parameters

Each validator supports custom parameters:

#### Protocol Validator
- `strict_version_check`: Enforce exact protocol version match
- `validate_client_info`: Validate client information format

#### Capabilities Validator
- `max_items_to_list`: Limit number of items to retrieve in list operations
- `test_all_capabilities`: Test all advertised capabilities

#### Ping Validator
- `max_response_time_ms`: Maximum acceptable response time

#### Error Validator
- `test_malformed_requests`: Test malformed JSON handling
- `test_invalid_methods`: Test invalid method handling
- `strict_error_codes`: Require exact JSON-RPC error codes

#### Security Validator
- `run_mcp_scan`: Enable mcp-scan analysis
- `vulnerability_threshold`: Minimum severity level to report
- `save_scan_results`: Save detailed scan results to file

## Programmatic API

### Simple Validation

```python
from mcp_validation import validate_server

async def main():
    session = await validate_server(["python", "my_server.py"])
    
    if session.overall_success:
        print("✅ Server is MCP compliant!")
    else:
        print("❌ Validation failed:")
        for error in session.errors:
            print(f"  - {error}")

import asyncio
asyncio.run(main())
```

### Advanced Usage

```python
from mcp_validation import (
    MCPValidationOrchestrator, 
    ConfigurationManager,
    ConsoleReporter,
    JSONReporter
)

async def advanced_validation():
    # Load custom configuration
    config_manager = ConfigurationManager("./config.json")
    config_manager.set_active_profile("development")
    
    # Create orchestrator
    orchestrator = MCPValidationOrchestrator(config_manager)
    
    # Run validation
    session = await orchestrator.validate_server(
        ["python", "server.py"],
        env_vars={"DEBUG": "1"}
    )
    
    # Generate reports
    console_reporter = ConsoleReporter(verbose=True)
    console_reporter.report_session(session)
    
    json_reporter = JSONReporter()
    json_reporter.save_report(session, "report.json", ["python", "server.py"])

asyncio.run(advanced_validation())
```

### Custom Validators

```python
from mcp_validation import BaseValidator, ValidationContext, ValidatorResult
from mcp_validation import MCPValidationOrchestrator, ConfigurationManager

class PerformanceValidator(BaseValidator):
    @property
    def name(self) -> str:
        return "performance"
    
    @property  
    def description(self) -> str:
        return "Test MCP server performance characteristics"
    
    @property
    def dependencies(self) -> List[str]:
        return ["protocol"]
    
    async def validate(self, context: ValidationContext) -> ValidatorResult:
        # Your custom validation logic here
        start_time = time.time()
        
        # Test response times, concurrent requests, etc.
        
        return ValidatorResult(
            validator_name=self.name,
            passed=True,
            errors=[],
            warnings=[],
            data={"response_time": 0.1},
            execution_time=time.time() - start_time
        )

# Register and use
config_manager = ConfigurationManager()
orchestrator = MCPValidationOrchestrator(config_manager)
orchestrator.register_validator(PerformanceValidator)
```

## Examples

See the `examples/` directory for:
- `sample-config.json` - Complete configuration example
- `custom_validator.py` - How to create custom validators
- `validation-config.json` - Advanced configuration scenarios

## Command Line Reference

```bash
mcp-validate [OPTIONS] [--] COMMAND [ARGS...]

Options:
  --config FILE              Configuration file path
  --profile NAME             Validation profile to use
  --env KEY=VALUE            Set environment variable (repeatable)
  --enable VALIDATOR         Enable specific validator
  --disable VALIDATOR        Disable specific validator
  --timeout SECONDS          Global timeout override
  --skip-mcp-scan           Skip mcp-scan security analysis
  --json-report FILENAME     Export JSON report
  --verbose                  Show detailed output
  --list-profiles           List available profiles
  --list-validators         List available validators
  -h, --help                Show help message
```

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure the MCP server command is in your PATH
2. **Timeout errors**: Increase timeout with `--timeout` or in config
3. **Permission issues**: Check environment variables and file permissions
4. **mcp-scan not found**: Install with `uvx install mcp-scan` or disable security validator

### Debug Mode

```bash
# Enable verbose output
mcp-validate --verbose -- python server.py

# Generate detailed JSON report
mcp-validate --json-report debug-report.json -- python server.py
```

### Environment Variables for Debugging

```bash
export MCP_VALIDATION_PROFILE=development  # Use dev-friendly profile
export DEBUG=1                            # Enable debug logging in your server
```