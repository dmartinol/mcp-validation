# MCP Validation Tool

A comprehensive validation tool for [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers to ensure protocol compliance, security, and proper implementation.

## Goal

This tool validates MCP servers by:

- **Protocol Compliance**: Tests the complete MCP initialization handshake
- **Standard Conformance**: Validates JSON-RPC 2.0 format and required fields  
- **Capability Testing**: Verifies advertised capabilities (resources, tools, prompts)
- **Security Analysis**: Integrates with [mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) for vulnerability detection
- **Registry Validation**: Ensures servers match their registry schema definitions
- **Detailed Reporting**: Exports comprehensive JSON reports with validation checklists
- **Automated Testing**: Provides programmatic validation for CI/CD pipelines

## Features

- ✅ **Protocol Validation**: Complete MCP handshake and capability testing
- ✅ **Security Scanning**: Integrated mcp-scan vulnerability analysis
- ✅ **JSON Reports**: Comprehensive validation reports with linked security scans
- ✅ **Step-by-Step Logging**: Real-time validation progress with detailed feedback
- ✅ **Tool Discovery**: Lists all available tools, prompts, and resources
- ✅ **Environment Variables**: Configurable environment setup
- ✅ **Timeout Handling**: Configurable validation timeouts
- ✅ **Exit Codes**: Proper exit codes for automation
- ✅ **Verbose Mode**: Optional detailed output

## Installation

```bash
# Clone and install
git clone https://github.com/modelcontextprotocol/mcp-validation
cd mcp-validation
uv sync
```

Or install directly:
```bash
pip install mcp-validation
```

## Usage

### Basic Validation

```bash
# Validate a Python MCP server
mcp-validate python server.py

# Validate a Node.js MCP server
mcp-validate node server.js

# Validate npx packages (use -- separator for flags)
mcp-validate -- npx -y kubernetes-mcp-server@latest
```

### With Environment Variables

```bash
# IoTDB MCP server example
mcp-validate \
  --env IOTDB_HOST=127.0.0.1 \
  --env IOTDB_PORT=6667 \
  --env IOTDB_USER=root \
  --env IOTDB_PASSWORD=root \
  python src/iotdb_mcp_server/server.py
```

### JSON Report Generation

```bash
# Generate comprehensive JSON report
mcp-validate --json-report validation-report.json python server.py

# With security analysis and custom timeout
mcp-validate \
  --timeout 60 \
  --json-report full-report.json \
  --env API_KEY=secret \
  -- npx -y some-mcp-server@latest
```

### Security Analysis Options

```bash
# Skip mcp-scan for faster validation
mcp-validate --skip-mcp-scan python server.py

# Full validation with security scan
mcp-validate --timeout 120 --json-report report.json python server.py
```

### Programmatic Usage

```python
import asyncio
from mcp_validation import validate_mcp_server_command

async def test_server():
    result = await validate_mcp_server_command(
        command_args=["python", "server.py"],
        env_vars={"API_KEY": "secret"},
        timeout=30.0,
        use_mcp_scan=True
    )
    
    if result.is_valid:
        print(f"✓ Server is MCP compliant!")
        print(f"Tools: {result.tools}")
        print(f"Capabilities: {list(result.capabilities.keys())}")
        if result.mcp_scan_results:
            print(f"Security scan: {result.mcp_scan_file}")
    else:
        print("✗ Validation failed:")
        for error in result.errors:
            print(f"  - {error}")

asyncio.run(test_server())
```

## CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `command` | Command and arguments to run the MCP server | `python server.py` |
| `--env KEY=VALUE` | Set environment variables (repeatable) | `--env HOST=localhost` |
| `--timeout SECONDS` | Validation timeout in seconds (default: 30) | `--timeout 60` |
| `--verbose` | Show detailed output including warnings | `--verbose` |
| `--skip-mcp-scan` | Skip mcp-scan security analysis | `--skip-mcp-scan` |
| `--json-report FILE` | Export detailed JSON report to file | `--json-report report.json` |

## Validation Process

The tool performs these validation steps:

1. **Process Execution**: Starts the server with provided arguments and environment
2. **Initialize Handshake**: Sends MCP `initialize` request with protocol version
3. **Protocol Compliance**: Validates JSON-RPC 2.0 format and required response fields
4. **Capability Discovery**: Tests advertised capabilities (resources, tools, prompts)
5. **Security Analysis**: Runs mcp-scan vulnerability detection (optional)
6. **Report Generation**: Creates detailed JSON reports with validation checklist

## Output Format

```
Testing MCP server: npx -y kubernetes-mcp-server@latest

🔄 Step 1: Sending initialize request...
✅ Initialize request successful
🔄 Step 2: Sending initialized notification...
✅ Initialized notification sent
🔄 Step 3: Testing capabilities...
  🔄 Testing tools...
    ✅ Found 18 tools
    📋 Names: configuration_view, events_list, helm_install, helm_list, helm_uninstall (and 13 more)
  🔄 Testing prompts...
    ✅ Found 0 prompts
  🔄 Testing resources...
    ✅ Found 0 resources
✅ Capability testing complete
🔄 Step 4: Running mcp-scan security analysis...
    🔍 Running: uvx mcp-scan@latest --json...
    📊 Scanned 18 tools
    ✅ No security issues detected
    💾 Scan results saved to: mcp-scan-results_20250730_120203.json
✅ mcp-scan analysis complete

✓ Valid: True
⏱ Execution time: 10.49s
🖥 Server: kubernetes-mcp-server vv0.0.46
🔧 Capabilities: logging, prompts, resources, tools
🔨 Tools (18): configuration_view, events_list, helm_install, helm_list, helm_uninstall, namespaces_list, pods_delete, pods_exec, pods_get, pods_list, pods_list_in_namespace, pods_log, pods_run, pods_top, resources_create_or_update, resources_delete, resources_get, resources_list
🔍 Security Scan: No issues found in 18 tools
📋 JSON report saved to: validation-report.json
```

## JSON Report Structure

The `--json-report` option generates comprehensive validation reports:

```json
{
  "report_metadata": {
    "generated_at": "2025-07-30T12:02:03.456789",
    "validator_version": "0.1.0",
    "command": "npx -y kubernetes-mcp-server@latest",
    "environment_variables": {}
  },
  "validation_summary": {
    "is_valid": true,
    "execution_time_seconds": 10.49,
    "total_errors": 0,
    "total_warnings": 0
  },
  "validation_checklist": {
    "protocol_validation": {
      "initialize_request": {"status": "passed", "details": "..."},
      "initialize_response": {"status": "passed", "details": "..."},
      "protocol_version": {"status": "passed", "details": "..."}
    },
    "capability_testing": {
      "tools_capability": {"status": "passed", "details": "..."},
      "resources_capability": {"status": "skipped", "details": "..."}
    },
    "security_analysis": {
      "mcp_scan_execution": {"status": "passed", "details": "..."}
    }
  },
  "server_information": {
    "server_info": {"name": "kubernetes-mcp-server", "version": "v0.0.46"},
    "capabilities": {"logging": {}, "tools": {"listChanged": true}},
    "discovered_items": {
      "tools": {"count": 18, "names": ["configuration_view", "..."]}
    }
  },
  "security_analysis": {
    "mcp_scan_executed": true,
    "mcp_scan_file": "mcp-scan-results_20250730_120203.json",
    "summary": {
      "tools_scanned": 18,
      "vulnerabilities_found": 0,
      "vulnerability_types": [],
      "risk_levels": []
    }
  },
  "issues": {
    "errors": [],
    "warnings": []
  }
}
```

## Exit Codes

- `0`: Server is MCP compliant
- `1`: Validation failed or server is non-compliant

## MCP Registry Validation

For servers listed in the [MCP Registry](https://github.com/modelcontextprotocol/registry), this tool can validate:

- Package installation requirements
- Environment variable specifications
- Argument format compliance
- Protocol implementation correctness

## Development

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and development workflows.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/modelcontextprotocol/mcp-validation
cd mcp-validation
```

### Quick Start with Makefile

For convenience, this project includes a Makefile with common development tasks:

```bash
# Setup development environment
make install

# Run the full pre-commit workflow (format, lint, test)
make pre-commit

# Run tests
make test

# Format code
make format

# See all available commands
make help
```

### Manual Setup

```bash
# Install all dependencies including dev extras
uv sync --extra dev

# Alternatively, install the package in development mode
uv pip install -e ".[dev]"
```

### Available Make Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install dependencies with dev extras |
| `make dev-setup` | Complete development environment setup |
| `make test` | Run all tests (excluding partner repos) |
| `make test-cov` | Run tests with coverage report |
| `make test-fast` | Run tests with fail-fast (-x flag) |
| `make debug-test` | Run tests with debug output and registry logging |
| `make format` | Format code with Black |
| `make check` | Check formatting without making changes |
| `make lint` | Check code with Ruff (no fixes) |
| `make lint-fix` | Check and fix code issues with Ruff |
| `make pre-commit` | Run full pre-commit workflow (format, lint, test) |
| `make ci` | Run CI-like checks (no automatic fixes) |
| `make clean` | Clean up cache and temporary files |

### Manual Testing Commands

```bash
# Run all tests
make test
# OR manually:
uv run --extra dev pytest tests/ -v

# Run tests with coverage
make test-cov
# OR manually:
uv run --extra dev pytest tests/ --cov=mcp_validation --cov-report=term-missing

# Run specific test file
uv run --extra dev pytest tests/test_enhanced_registry.py -v

# Run tests and stop on first failure
make test-fast
# OR manually:
uv run --extra dev pytest tests/ -x
```

### Code Formatting and Linting

```bash
# Format code with Black
make format
# OR manually:
uv run --extra dev black mcp_validation/

# Check code formatting (without making changes)
make check
# OR manually:
uv run --extra dev black --check mcp_validation/

# Lint with Ruff (with fixes)
make lint-fix
# OR manually:
uv run --extra dev ruff check --fix mcp_validation/

# Lint with Ruff (check only)
make lint
# OR manually:
uv run --extra dev ruff check mcp_validation/

# Type checking with mypy
uv run --extra dev mypy mcp_validation/
```

### Workflows

```bash
# Pre-commit workflow (format, lint, test)
make pre-commit

# CI-style checks (no automatic fixes)
make ci

# Manual pre-commit workflow
uv run --extra dev black mcp_validation/ && \
uv run --extra dev ruff check --fix mcp_validation/ && \
uv run --extra dev pytest tests/ -v
```

### Development Guidelines

1. **Testing**: All new features must include tests
2. **Code Style**: Use Black for formatting and Ruff for linting
3. **Type Hints**: Add type hints for all public APIs
4. **Documentation**: Update README and docstrings for new features

### Test Configuration

The project uses pytest with the following configuration in `pyproject.toml`:

- **Test Discovery**: Looks for tests in the `tests/` directory
- **Async Support**: Configured for async/await testing
- **Exclusions**: Automatically excludes partner repositories and build directories
- **Markers**: Strict marker checking enabled

### Debugging Tests

```bash
# Run tests with debug output and registry logging
make debug-test

# Run tests with verbose output and debug information
uv run --extra dev pytest -v -s

# Run specific test with debugging
uv run --extra dev pytest tests/test_enhanced_registry.py::test_enhanced_registry_validator -v -s

# Enable registry debug logging during tests
MCP_REGISTRY_DEBUG=1 uv run --extra dev pytest tests/test_enhanced_registry.py -v
```

## Examples

### Validate Registry Server

```bash
# Apache IoTDB MCP Server from registry
mcp-validate \
  --env IOTDB_HOST=127.0.0.1 \
  --env IOTDB_PORT=6667 \
  --env IOTDB_USER=root \
  --env IOTDB_PASSWORD=root \
  --env IOTDB_DATABASE=test \
  --env IOTDB_SQL_DIALECT=table \
  python src/iotdb_mcp_server/server.py
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Validate MCP Server
  run: |
    mcp-validate --json-report validation-report.json python server.py
  env:
    DATABASE_URL: sqlite:///test.db

- name: Upload validation report
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: mcp-validation-report
    path: |
      validation-report.json
      mcp-scan-results_*.json
```

### Security Analysis

The tool integrates with [mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) for comprehensive security analysis:

- **Automatic Detection**: Checks for `uvx` or `mcp-scan` availability
- **Vulnerability Scanning**: Analyzes tools for potential security issues
- **Separate Reports**: Security results saved to timestamped JSON files
- **Linked Reports**: Main validation report references security scan files
- **Skip Option**: Use `--skip-mcp-scan` for faster validation without security analysis

## Contributing

Contributions are welcome! Please see our [contributing guidelines](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Registry](https://github.com/modelcontextprotocol/registry)
- [mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) - Security vulnerability scanner for MCP servers
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)