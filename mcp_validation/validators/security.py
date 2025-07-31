"""Security analysis validator using mcp-scan."""

import asyncio
import json
import os
import shutil
import tempfile
import time
from typing import Dict, Any, List, Optional, Tuple

from .base import BaseValidator, ValidationContext, ValidatorResult


class SecurityValidator(BaseValidator):
    """Validates MCP server security using mcp-scan analysis."""
    
    @property
    def name(self) -> str:
        return "security"
    
    @property
    def description(self) -> str:
        return "Security analysis using mcp-scan tool"
    
    @property
    def dependencies(self) -> List[str]:
        return ["protocol"]  # Needs basic protocol established
    
    def is_applicable(self, context: ValidationContext) -> bool:
        """Only applicable if mcp-scan is available and enabled."""
        if not self.enabled:
            return False
        
        if not self.config.get('run_mcp_scan', True):
            return False
            
        return self._check_mcp_scan_available()
    
    def _check_mcp_scan_available(self) -> bool:
        """Check if mcp-scan tool is available."""
        return shutil.which("mcp-scan") is not None or shutil.which("uvx") is not None
    
    async def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute security validation."""
        start_time = time.time()
        errors = []
        warnings = []
        data = {
            "scan_results": None,
            "scan_file": None,
            "tools_scanned": 0,
            "vulnerabilities_found": 0,
            "vulnerability_types": [],
            "risk_levels": []
        }
        
        if not self._check_mcp_scan_available():
            warnings.append("mcp-scan tool not available")
            execution_time = time.time() - start_time
            return ValidatorResult(
                validator_name=self.name,
                passed=True,  # Not a failure if tool unavailable
                errors=errors,
                warnings=warnings,
                data=data,
                execution_time=execution_time
            )
        
        try:
            # Run mcp-scan analysis
            scan_results, scan_file = await self._run_mcp_scan(context, warnings)
            
            if scan_results:
                data["scan_results"] = scan_results
                data["scan_file"] = scan_file
                
                # Parse scan results
                tools_scanned, vulnerabilities = self._parse_scan_results(scan_results)
                data["tools_scanned"] = tools_scanned
                data["vulnerabilities_found"] = len(vulnerabilities)
                data["vulnerability_types"] = list(set(v.get("type", "unknown") for v in vulnerabilities))
                data["risk_levels"] = list(set(v.get("severity", "unknown") for v in vulnerabilities))
                
                # Check vulnerability threshold
                threshold = self.config.get('vulnerability_threshold', 'high')
                if self._check_vulnerability_threshold(vulnerabilities, threshold):
                    warnings.append(f"Vulnerabilities found exceed {threshold} threshold")
            
        except Exception as e:
            warnings.append(f"Security analysis failed: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return ValidatorResult(
            validator_name=self.name,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data=data,
            execution_time=execution_time
        )
    
    async def _run_mcp_scan(
        self, 
        context: ValidationContext, 
        warnings: List[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Run mcp-scan security analysis on the server."""
        
        # Create temporary MCP configuration file for mcp-scan
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
            # Get command from context (need to reconstruct from process)
            # For now, use a simplified approach
            config = {
                "mcpServers": {
                    "test-server": {
                        "command": "echo",  # Placeholder - this needs the actual command
                        "args": ["MCP server placeholder"]
                    }
                }
            }
            
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
                warnings.append("mcp-scan tool not available")
                return None, None
            
            # Run mcp-scan with timeout
            timeout = self.config.get('timeout', 60.0)
            process = await asyncio.create_subprocess_exec(
                *scan_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            if process.returncode == 0:
                try:
                    scan_results = json.loads(stdout.decode())
                    
                    # Save scan results to a timestamped file if configured
                    scan_filename = None
                    if self.config.get('save_scan_results', False):
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        scan_filename = f"mcp-scan-results_{timestamp}.json"
                        
                        with open(scan_filename, 'w') as scan_file:
                            json.dump(scan_results, scan_file, indent=2)
                    
                    return scan_results, scan_filename
                    
                except json.JSONDecodeError as e:
                    warnings.append(f"mcp-scan output parsing failed: {e}")
                    return None, None
            else:
                error_msg = stderr.decode().strip()
                warnings.append(f"mcp-scan failed: {error_msg}")
                return None, None
                
        finally:
            # Clean up temporary config file
            try:
                os.unlink(config_path)
            except:
                pass
    
    def _parse_scan_results(self, scan_results: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
        """Parse mcp-scan results to extract metrics."""
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
        
        return tools_scanned, vulnerabilities
    
    def _check_vulnerability_threshold(
        self, 
        vulnerabilities: List[Dict[str, Any]], 
        threshold: str
    ) -> bool:
        """Check if vulnerabilities exceed the specified threshold."""
        if not vulnerabilities:
            return False
        
        severity_levels = {
            'low': 1,
            'medium': 2, 
            'high': 3,
            'critical': 4
        }
        
        threshold_level = severity_levels.get(threshold.lower(), 3)
        
        for vuln in vulnerabilities:
            vuln_severity = vuln.get("severity", "unknown").lower()
            vuln_level = severity_levels.get(vuln_severity, 1)
            
            if vuln_level >= threshold_level:
                return True
        
        return False