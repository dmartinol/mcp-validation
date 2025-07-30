import asyncio
import json
import subprocess
import time
import argparse
import os
import sys
import shutil
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MCPValidationResult:
    """Results from MCP server validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    server_info: Dict[str, Any]
    capabilities: Dict[str, Any]
    execution_time: float
    tools: List[str] = None
    prompts: List[str] = None
    resources: List[str] = None
    mcp_scan_results: Dict[str, Any] = None
    checklist: Dict[str, Any] = None
    mcp_scan_file: str = None


class MCPServerValidator:
    """Validates MCP server protocol compliance via stdio interface."""
    
    def __init__(self, timeout: float = 30.0, use_mcp_scan: bool = True):
        self.timeout = timeout
        self.request_id = 0
        self.use_mcp_scan = use_mcp_scan and self._check_mcp_scan_available()
    
    def _check_mcp_scan_available(self) -> bool:
        """Check if mcp-scan tool is available."""
        return shutil.which("mcp-scan") is not None or shutil.which("uvx") is not None
    
    def _get_next_id(self) -> int:
        """Get next request ID for JSON-RPC."""
        self.request_id += 1
        return self.request_id
    
    def _create_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> str:
        """Create a JSON-RPC 2.0 request."""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method
        }
        if params:
            request["params"] = params
        return json.dumps(request) + "\n"
    
    def _parse_jsonrpc_response(self, response_line: str) -> Dict[str, Any]:
        """Parse a JSON-RPC response line."""
        try:
            return json.loads(response_line.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    async def validate_mcp_server(self, command_args: List[str], env_vars: Dict[str, str] = None) -> MCPValidationResult:
        """
        Execute and validate an MCP server using the provided command arguments.
        
        Args:
            command_args: List of command and arguments to execute the MCP server
                         Example: ["python", "server.py"] or ["node", "server.js", "--config", "config.json"]
            env_vars: Optional dictionary of environment variables to set for the server process
        
        Returns:
            MCPValidationResult with validation status and details
        """
        start_time = time.time()
        errors = []
        warnings = []
        server_info = {}
        capabilities = {}
        tools = []
        prompts = []
        resources = []
        mcp_scan_results = None
        mcp_scan_file = None
        
        # Initialize checklist
        checklist = {
            "protocol_validation": {
                "initialize_request": {"status": "pending", "details": "Send MCP initialize request"},
                "initialize_response": {"status": "pending", "details": "Validate initialize response format"},
                "protocol_version": {"status": "pending", "details": "Check protocol version compatibility"},
                "server_info": {"status": "pending", "details": "Validate server information fields"},
                "capabilities": {"status": "pending", "details": "Validate capabilities structure"},
                "initialized_notification": {"status": "pending", "details": "Send initialized notification"}
            },
            "capability_testing": {
                "resources_capability": {"status": "pending", "details": "Test resources capability if advertised"},
                "tools_capability": {"status": "pending", "details": "Test tools capability if advertised"},
                "prompts_capability": {"status": "pending", "details": "Test prompts capability if advertised"}
            },
            "security_analysis": {
                "mcp_scan_available": {"status": "pending", "details": "Check if mcp-scan tool is available"},
                "mcp_scan_execution": {"status": "pending", "details": "Run mcp-scan security analysis"}
            }
        }
        
        try:
            # Prepare environment variables
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                *command_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Perform MCP protocol validation
            is_valid = await self._validate_protocol(process, errors, warnings, server_info, capabilities, tools, prompts, resources, checklist)
            
            # Run mcp-scan if available and protocol validation passed
            if self.use_mcp_scan:
                checklist["security_analysis"]["mcp_scan_available"]["status"] = "passed" if self.use_mcp_scan else "skipped"
                if is_valid:
                    print("🔄 Step 4: Running mcp-scan security analysis...")
                    mcp_scan_results, mcp_scan_file = await self._run_mcp_scan(command_args, env_vars, errors, warnings, checklist)
                    if mcp_scan_results:
                        print("✅ mcp-scan analysis complete")
                    else:
                        print("⚠️  mcp-scan analysis skipped or failed")
            else:
                checklist["security_analysis"]["mcp_scan_available"]["status"] = "skipped"
                checklist["security_analysis"]["mcp_scan_execution"]["status"] = "skipped"
            
            # Clean up process
            if process.returncode is None:
                try:
                    process.stdin.close()
                    await process.stdin.wait_closed()
                except:
                    pass
                
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            
        except FileNotFoundError:
            errors.append(f"Command not found: {command_args[0]}")
            is_valid = False
        except Exception as e:
            errors.append(f"Failed to start server: {str(e)}")
            is_valid = False
        
        execution_time = time.time() - start_time
        
        return MCPValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            server_info=server_info,
            capabilities=capabilities,
            execution_time=execution_time,
            tools=tools,
            prompts=prompts,
            resources=resources,
            mcp_scan_results=mcp_scan_results,
            checklist=checklist,
            mcp_scan_file=mcp_scan_file
        )
    
    async def _validate_protocol(
        self, 
        process: asyncio.subprocess.Process,
        errors: List[str],
        warnings: List[str],
        server_info: Dict[str, Any],
        capabilities: Dict[str, Any],
        tools: List[str],
        prompts: List[str],
        resources: List[str],
        checklist: Dict[str, Any]
    ) -> bool:
        """Validate MCP protocol compliance."""
        try:
            print("🔄 Step 1: Sending initialize request...")
            # Step 1: Send initialize request
            checklist["protocol_validation"]["initialize_request"]["status"] = "running"
            init_success = await self._test_initialize(process, errors, server_info, capabilities, checklist)
            if not init_success:
                print("❌ Initialize request failed")
                checklist["protocol_validation"]["initialize_request"]["status"] = "failed"
                return False
            print("✅ Initialize request successful")
            checklist["protocol_validation"]["initialize_request"]["status"] = "passed"
            
            print("🔄 Step 2: Sending initialized notification...")
            # Step 2: Send initialized notification
            checklist["protocol_validation"]["initialized_notification"]["status"] = "running"
            await self._send_initialized(process, errors)
            print("✅ Initialized notification sent")
            checklist["protocol_validation"]["initialized_notification"]["status"] = "passed"
            
            print("🔄 Step 3: Testing capabilities...")
            # Step 3: Test basic capabilities
            await self._test_capabilities(process, errors, warnings, capabilities, tools, prompts, resources, checklist)
            print("✅ Capability testing complete")
            
            return len(errors) == 0
            
        except asyncio.TimeoutError:
            errors.append(f"Server validation timed out after {self.timeout} seconds")
            return False
        except Exception as e:
            errors.append(f"Protocol validation failed: {str(e)}")
            return False
    
    async def _test_initialize(
        self,
        process: asyncio.subprocess.Process,
        errors: List[str],
        server_info: Dict[str, Any],
        capabilities: Dict[str, Any],
        checklist: Dict[str, Any]
    ) -> bool:
        """Test the initialize request/response."""
        # Send initialize request
        init_request = self._create_jsonrpc_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "mcp-validator",
                "version": "1.0.0"
            }
        })
        
        process.stdin.write(init_request.encode())
        await process.stdin.drain()
        
        # Read response
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(), 
                timeout=self.timeout
            )
            response = self._parse_jsonrpc_response(response_line.decode())
        except asyncio.TimeoutError:
            errors.append("Initialize request timed out")
            return False
        except ValueError as e:
            errors.append(f"Initialize response parsing failed: {e}")
            return False
        
        # Validate initialize response
        checklist["protocol_validation"]["initialize_response"]["status"] = "running"
        if "error" in response:
            errors.append(f"Initialize request failed: {response['error']}")
            checklist["protocol_validation"]["initialize_response"]["status"] = "failed"
            return False
        
        if "result" not in response:
            errors.append("Initialize response missing 'result' field")
            checklist["protocol_validation"]["initialize_response"]["status"] = "failed"
            return False
        
        checklist["protocol_validation"]["initialize_response"]["status"] = "passed"
        result = response["result"]
        
        # Validate required fields
        checklist["protocol_validation"]["server_info"]["status"] = "running"
        checklist["protocol_validation"]["capabilities"]["status"] = "running"
        required_fields = ["protocolVersion", "capabilities", "serverInfo"]
        for field in required_fields:
            if field not in result:
                errors.append(f"Initialize result missing required field: {field}")
        
        # Store server info and capabilities
        server_info.update(result.get("serverInfo", {}))
        capabilities.update(result.get("capabilities", {}))
        
        if "serverInfo" in result:
            checklist["protocol_validation"]["server_info"]["status"] = "passed"
        else:
            checklist["protocol_validation"]["server_info"]["status"] = "failed"
            
        if "capabilities" in result:
            checklist["protocol_validation"]["capabilities"]["status"] = "passed"
        else:
            checklist["protocol_validation"]["capabilities"]["status"] = "failed"
        
        # Validate protocol version
        checklist["protocol_validation"]["protocol_version"]["status"] = "running"
        protocol_version = result.get("protocolVersion")
        if protocol_version != "2024-11-05":
            errors.append(f"Unsupported protocol version: {protocol_version}")
            checklist["protocol_validation"]["protocol_version"]["status"] = "failed"
        else:
            checklist["protocol_validation"]["protocol_version"]["status"] = "passed"
        
        return len(errors) == 0
    
    async def _send_initialized(self, process: asyncio.subprocess.Process, errors: List[str]):
        """Send the initialized notification."""
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
        await process.stdin.drain()
    
    async def _test_capabilities(
        self,
        process: asyncio.subprocess.Process,
        errors: List[str],
        warnings: List[str],
        capabilities: Dict[str, Any],
        tools: List[str],
        prompts: List[str],
        resources: List[str],
        checklist: Dict[str, Any]
    ):
        """Test advertised capabilities."""
        # Test resources capability
        if capabilities.get("resources"):
            print("  🔄 Testing resources...")
            checklist["capability_testing"]["resources_capability"]["status"] = "running"
            await self._test_resources_list(process, errors, warnings, resources)
            checklist["capability_testing"]["resources_capability"]["status"] = "passed"
        else:
            checklist["capability_testing"]["resources_capability"]["status"] = "skipped"
        
        # Test tools capability  
        if capabilities.get("tools"):
            print("  🔄 Testing tools...")
            checklist["capability_testing"]["tools_capability"]["status"] = "running"
            await self._test_tools_list(process, errors, warnings, tools)
            checklist["capability_testing"]["tools_capability"]["status"] = "passed"
        else:
            checklist["capability_testing"]["tools_capability"]["status"] = "skipped"
        
        # Test prompts capability
        if capabilities.get("prompts"):
            print("  🔄 Testing prompts...")
            checklist["capability_testing"]["prompts_capability"]["status"] = "running"
            await self._test_prompts_list(process, errors, warnings, prompts)
            checklist["capability_testing"]["prompts_capability"]["status"] = "passed"
        else:
            checklist["capability_testing"]["prompts_capability"]["status"] = "skipped"
    
    async def _test_resources_list(self, process: asyncio.subprocess.Process, errors: List[str], warnings: List[str], resources: List[str]):
        """Test resources/list request."""
        await self._test_list_request(process, "resources/list", "resources", errors, warnings, resources)
    
    async def _test_tools_list(self, process: asyncio.subprocess.Process, errors: List[str], warnings: List[str], tools: List[str]):
        """Test tools/list request."""
        await self._test_list_request(process, "tools/list", "tools", errors, warnings, tools)
    
    async def _test_prompts_list(self, process: asyncio.subprocess.Process, errors: List[str], warnings: List[str], prompts: List[str]):
        """Test prompts/list request."""
        await self._test_list_request(process, "prompts/list", "prompts", errors, warnings, prompts)
    
    async def _test_list_request(
        self,
        process: asyncio.subprocess.Process,
        method: str,
        expected_field: str,
        errors: List[str],
        warnings: List[str],
        items_list: List[str]
    ):
        """Test a generic list request."""
        request = self._create_jsonrpc_request(method)
        
        try:
            process.stdin.write(request.encode())
            await process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            response = self._parse_jsonrpc_response(response_line.decode())
            
            if "error" in response:
                warnings.append(f"{method} request failed: {response['error']}")
                print(f"    ❌ {method} failed: {response['error']}")
            elif "result" not in response:
                warnings.append(f"{method} response missing 'result' field")
                print(f"    ❌ {method} missing result field")
            elif expected_field not in response["result"]:
                warnings.append(f"{method} result missing '{expected_field}' field")
                print(f"    ❌ {method} missing {expected_field} field")
            else:
                # Validate that it's a list
                items = response["result"][expected_field]
                if not isinstance(items, list):
                    warnings.append(f"{method} result '{expected_field}' should be a list")
                    print(f"    ❌ {method} {expected_field} should be a list")
                else:
                    # Extract names from items
                    for item in items:
                        if isinstance(item, dict) and "name" in item:
                            items_list.append(item["name"])
                        elif isinstance(item, str):
                            items_list.append(item)
                    
                    count = len(items)
                    print(f"    ✅ Found {count} {expected_field}")
                    if count > 0 and items_list:
                        names = ", ".join(items_list[:5])  # Show first 5 names
                        if count > 5:
                            names += f" (and {count-5} more)"
                        print(f"    📋 Names: {names}")
                    
        except asyncio.TimeoutError:
            warnings.append(f"{method} request timed out")
            print(f"    ⏰ {method} timed out")
        except Exception as e:
            warnings.append(f"{method} request failed: {str(e)}")
            print(f"    ❌ {method} failed: {str(e)}")
    
    async def _run_mcp_scan(self, command_args: List[str], env_vars: Dict[str, str] = None, errors: List[str] = None, warnings: List[str] = None, checklist: Dict[str, Any] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Run mcp-scan security analysis on the server."""
        if checklist:
            checklist["security_analysis"]["mcp_scan_execution"]["status"] = "running"
            
        try:
            # Create temporary MCP configuration file for mcp-scan
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
                config = {
                    "mcpServers": {
                        "test-server": {
                            "command": command_args[0],
                            "args": command_args[1:] if len(command_args) > 1 else [],
                        }
                    }
                }
                
                # Add environment variables if provided
                if env_vars:
                    config["mcpServers"]["test-server"]["env"] = env_vars
                
                json.dump(config, config_file, indent=2)
                config_path = config_file.name
            
            try:
                # Try uvx mcp-scan first, then fall back to mcp-scan
                scan_cmd = None
                if shutil.which("uvx"):
                    scan_cmd = ["uvx", "mcp-scan@latest", "--json", "--suppress-mcpserver-io", "true", config_path]
                elif shutil.which("mcp-scan"):
                    scan_cmd = ["mcp-scan", "--json", "--suppress-mcpserver-io", "true", config_path]
                
                if not scan_cmd:
                    if warnings:
                        warnings.append("mcp-scan tool not available")
                    if checklist:
                        checklist["security_analysis"]["mcp_scan_execution"]["status"] = "failed"
                    return None, None
                
                print(f"    🔍 Running: {' '.join(scan_cmd[:3])}...")
                
                # Run mcp-scan with timeout
                process = await asyncio.create_subprocess_exec(
                    *scan_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self.timeout
                )
                
                if process.returncode == 0:
                    try:
                        scan_results = json.loads(stdout.decode())
                        
                        # Save scan results to a timestamped file
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        scan_filename = f"mcp-scan-results_{timestamp}.json"
                        
                        with open(scan_filename, 'w') as scan_file:
                            json.dump(scan_results, scan_file, indent=2)
                        
                        # Extract key metrics from mcp-scan format
                        # The format is: {"/path/to/config.json": {"servers": [{"signature": {"tools": [...], "vulnerabilities": [...]}}]}}
                        tools_scanned = 0
                        vulnerabilities = []
                        
                        for config_path, config_data in scan_results.items():
                            if "servers" in config_data:
                                for server in config_data["servers"]:
                                    signature = server.get("signature", {})
                                    tools = signature.get("tools", [])
                                    tools_scanned += len(tools)
                                    
                                    # Look for vulnerabilities in the signature
                                    server_vulns = signature.get("vulnerabilities", [])
                                    vulnerabilities.extend(server_vulns)
                        
                        print(f"    📊 Scanned {tools_scanned} tools")
                        if vulnerabilities:
                            vuln_count = len(vulnerabilities)
                            print(f"    ⚠️  Found {vuln_count} potential security issues")
                            
                            # Show first few vulnerability types
                            vuln_types = [v.get("type", "unknown") for v in vulnerabilities[:3]]
                            if vuln_types:
                                types_str = ", ".join(vuln_types)
                                if len(vulnerabilities) > 3:
                                    types_str += f" (and {len(vulnerabilities)-3} more)"
                                print(f"    🚨 Issues: {types_str}")
                        else:
                            print("    ✅ No security issues detected")
                        
                        print(f"    💾 Scan results saved to: {scan_filename}")
                        
                        if checklist:
                            checklist["security_analysis"]["mcp_scan_execution"]["status"] = "passed"
                        
                        return scan_results, scan_filename
                        
                    except json.JSONDecodeError as e:
                        if warnings:
                            warnings.append(f"mcp-scan output parsing failed: {e}")
                        print(f"    ❌ Failed to parse mcp-scan output: {e}")
                        if checklist:
                            checklist["security_analysis"]["mcp_scan_execution"]["status"] = "failed"
                        return None, None
                else:
                    error_msg = stderr.decode().strip()
                    if warnings:
                        warnings.append(f"mcp-scan failed: {error_msg}")
                    print(f"    ❌ mcp-scan failed: {error_msg}")
                    if checklist:
                        checklist["security_analysis"]["mcp_scan_execution"]["status"] = "failed"
                    return None, None
                    
            finally:
                # Clean up temporary config file
                try:
                    os.unlink(config_path)
                except:
                    pass
                    
        except asyncio.TimeoutError:
            if warnings:
                warnings.append("mcp-scan analysis timed out")
            print("    ⏰ mcp-scan analysis timed out")
            if checklist:
                checklist["security_analysis"]["mcp_scan_execution"]["status"] = "failed"
            return None, None
        except Exception as e:
            if warnings:
                warnings.append(f"mcp-scan analysis failed: {str(e)}")
            print(f"    ❌ mcp-scan analysis failed: {str(e)}")
            if checklist:
                checklist["security_analysis"]["mcp_scan_execution"]["status"] = "failed"
            return None, None


async def validate_mcp_server_command(command_args: List[str], timeout: float = 30.0, env_vars: Dict[str, str] = None, use_mcp_scan: bool = True) -> MCPValidationResult:
    """
    Convenience function to validate an MCP server.
    
    Args:
        command_args: List of command and arguments to execute the MCP server
        timeout: Timeout in seconds for the validation
        env_vars: Optional dictionary of environment variables to set for the server process
        use_mcp_scan: Whether to run mcp-scan security analysis
    
    Returns:
        MCPValidationResult with validation status and details
    
    Example:
        result = await validate_mcp_server_command(["python", "server.py"])
        if result.is_valid:
            print("Server is MCP compliant!")
        else:
            print("Validation errors:", result.errors)
    """
    validator = MCPServerValidator(timeout=timeout, use_mcp_scan=use_mcp_scan)
    return await validator.validate_mcp_server(command_args, env_vars)


def parse_env_args(env_args: List[str]) -> Dict[str, str]:
    """Parse environment variable arguments in KEY=VALUE format."""
    env_vars = {}
    for env_arg in env_args:
        if '=' not in env_arg:
            raise ValueError(f"Environment variable must be in KEY=VALUE format: {env_arg}")
        key, value = env_arg.split('=', 1)
        env_vars[key] = value
    return env_vars


def generate_json_report(result: MCPValidationResult, command_args: List[str], env_vars: Dict[str, str] = None) -> Dict[str, Any]:
    """Generate a comprehensive JSON report of the validation results."""
    import datetime
    
    report = {
        "report_metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "validator_version": "0.1.0",
            "command": " ".join(command_args),
            "environment_variables": env_vars or {}
        },
        "validation_summary": {
            "is_valid": result.is_valid,
            "execution_time_seconds": result.execution_time,
            "total_errors": len(result.errors),
            "total_warnings": len(result.warnings)
        },
        "server_information": {
            "server_info": result.server_info,
            "capabilities": result.capabilities,
            "discovered_items": {
                "tools": {
                    "count": len(result.tools) if result.tools else 0,
                    "names": result.tools or []
                },
                "prompts": {
                    "count": len(result.prompts) if result.prompts else 0,
                    "names": result.prompts or []
                },
                "resources": {
                    "count": len(result.resources) if result.resources else 0,
                    "names": result.resources or []
                }
            }
        },
        "validation_checklist": result.checklist,
        "security_analysis": {
            "mcp_scan_executed": result.mcp_scan_results is not None,
            "mcp_scan_file": result.mcp_scan_file,
            "summary": None
        },
        "issues": {
            "errors": result.errors,
            "warnings": result.warnings
        }
    }
    
    # Add security analysis summary if available
    if result.mcp_scan_results:
        # Parse mcp-scan format: {"/path/to/config.json": {"servers": [{"signature": {"tools": [...], "vulnerabilities": [...]}}]}}
        tools_scanned = 0
        vulnerabilities = []
        
        for config_path, config_data in result.mcp_scan_results.items():
            if "servers" in config_data:
                for server in config_data["servers"]:
                    signature = server.get("signature", {})
                    tools = signature.get("tools", [])
                    tools_scanned += len(tools)
                    
                    # Look for vulnerabilities in the signature
                    server_vulns = signature.get("vulnerabilities", [])
                    vulnerabilities.extend(server_vulns)
        
        report["security_analysis"]["summary"] = {
            "tools_scanned": tools_scanned,
            "vulnerabilities_found": len(vulnerabilities),
            "vulnerability_types": list(set(v.get("type", "unknown") for v in vulnerabilities)),
            "risk_levels": list(set(v.get("severity", "unknown") for v in vulnerabilities))
        }
    
    return report


def save_json_report(report: Dict[str, Any], filename: str) -> None:
    """Save the JSON report to a file."""
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"📋 JSON report saved to: {filename}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate MCP server protocol compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mcp-validate python server.py
  mcp-validate --env IOTDB_HOST=localhost --env IOTDB_PORT=6667 python server.py
  mcp-validate --timeout 60 node server.js --config config.json
  mcp-validate --env API_KEY=secret ./binary-server --verbose
  mcp-validate -- npx -y kubernetes-mcp-server@latest
        """
    )
    
    parser.add_argument(
        'command',
        nargs='+',
        help='Command and arguments to run the MCP server'
    )
    
    parser.add_argument(
        '--env',
        action='append',
        default=[],
        metavar='KEY=VALUE',
        help='Set environment variable (can be used multiple times)'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Timeout in seconds for validation (default: 30.0)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output including warnings'
    )
    
    parser.add_argument(
        '--skip-mcp-scan',
        action='store_true',
        help='Skip mcp-scan security analysis'
    )
    
    parser.add_argument(
        '--json-report',
        metavar='FILENAME',
        help='Export detailed JSON report to specified file'
    )
    
    return parser


async def main():
    """Main CLI entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Parse environment variables
        env_vars = parse_env_args(args.env) if args.env else None
        
        # Display what we're testing
        print(f"Testing MCP server: {' '.join(args.command)}")
        if env_vars:
            print("Environment variables:")
            for key, value in env_vars.items():
                # Mask potential secrets in output
                display_value = value if len(value) < 20 else f"{value[:10]}..."
                print(f"  {key}={display_value}")
        print()
        
        # Run validation
        result = await validate_mcp_server_command(
            command_args=args.command,
            timeout=args.timeout,
            env_vars=env_vars,
            use_mcp_scan=not args.skip_mcp_scan
        )
        
        # Display results
        print(f"✓ Valid: {result.is_valid}")
        print(f"⏱ Execution time: {result.execution_time:.2f}s")
        
        if result.server_info:
            name = result.server_info.get('name', 'Unknown')
            version = result.server_info.get('version', 'Unknown')
            print(f"🖥 Server: {name} v{version}")
        
        if result.capabilities:
            caps = list(result.capabilities.keys())
            print(f"🔧 Capabilities: {', '.join(caps)}")
        
        # Display discovered items
        if result.tools:
            print(f"🔨 Tools ({len(result.tools)}): {', '.join(result.tools)}")
        
        if result.prompts:
            print(f"💬 Prompts ({len(result.prompts)}): {', '.join(result.prompts)}")
        
        if result.resources:
            print(f"📁 Resources ({len(result.resources)}): {', '.join(result.resources)}")
        
        # Display mcp-scan results if available
        if result.mcp_scan_results:
            # Parse mcp-scan format
            tools_scanned = 0
            vulnerabilities = []
            
            for config_path, config_data in result.mcp_scan_results.items():
                if "servers" in config_data:
                    for server in config_data["servers"]:
                        signature = server.get("signature", {})
                        tools = signature.get("tools", [])
                        tools_scanned += len(tools)
                        server_vulns = signature.get("vulnerabilities", [])
                        vulnerabilities.extend(server_vulns)
            
            if vulnerabilities:
                print(f"🔍 Security Scan: {len(vulnerabilities)} issues found in {tools_scanned} tools")
            else:
                print(f"🔍 Security Scan: No issues found in {tools_scanned} tools")
        
        # Generate JSON report if requested
        if args.json_report:
            report = generate_json_report(result, args.command, env_vars)
            save_json_report(report, args.json_report)
        
        if result.errors:
            print("\n❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.warnings and (args.verbose or not result.is_valid):
            print("\n⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        # Exit with appropriate code
        sys.exit(0 if result.is_valid else 1)
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def cli_main():
    """Synchronous entry point for CLI script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()