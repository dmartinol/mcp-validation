"""Example of creating a custom MCP validator."""

import asyncio
import json
import time
from typing import Dict, Any, List

from mcp_validation.validators.base import BaseValidator, ValidationContext, ValidatorResult


class PerformanceValidator(BaseValidator):
    """Custom validator that tests MCP server performance characteristics."""
    
    @property
    def name(self) -> str:
        return "performance"
    
    @property
    def description(self) -> str:
        return "Test MCP server performance and response times"
    
    @property
    def dependencies(self) -> List[str]:
        return ["protocol", "capabilities"]  # Needs basic setup first
    
    def is_applicable(self, context: ValidationContext) -> bool:
        """Only applicable if server has tools or resources."""
        return (self.enabled and 
                (context.capabilities.get("tools") or 
                 context.capabilities.get("resources")))
    
    async def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute performance validation."""
        start_time = time.time()
        errors = []
        warnings = []
        
        # Performance test configuration
        max_response_time = self.config.get('max_response_time_ms', 1000)
        test_iterations = self.config.get('test_iterations', 5)
        concurrent_requests = self.config.get('concurrent_requests', 3)
        
        data = {
            "response_times": [],
            "average_response_time": 0.0,
            "max_response_time": 0.0,
            "failed_requests": 0,
            "concurrent_test_passed": True,
            "performance_grade": "unknown"
        }
        
        try:
            # Test 1: Sequential response time testing
            print(f"  🔄 Testing response times ({test_iterations} iterations)...")
            response_times = await self._test_sequential_performance(
                context, test_iterations
            )
            data["response_times"] = response_times
            
            if response_times:
                data["average_response_time"] = sum(response_times) / len(response_times)
                data["max_response_time"] = max(response_times)
                
                # Check performance thresholds
                if data["average_response_time"] > max_response_time:
                    warnings.append(
                        f"Average response time ({data['average_response_time']:.2f}ms) "
                        f"exceeds threshold ({max_response_time}ms)"
                    )
                
                if data["max_response_time"] > max_response_time * 2:
                    warnings.append(
                        f"Maximum response time ({data['max_response_time']:.2f}ms) "
                        f"is very high"
                    )
            
            # Test 2: Concurrent request handling
            if concurrent_requests > 1:
                print(f"  🔄 Testing concurrent requests ({concurrent_requests} simultaneous)...")
                concurrent_success = await self._test_concurrent_performance(
                    context, concurrent_requests
                )
                data["concurrent_test_passed"] = concurrent_success
                
                if not concurrent_success:
                    warnings.append("Server may not handle concurrent requests well")
            
            # Calculate performance grade
            data["performance_grade"] = self._calculate_performance_grade(data)
            
        except Exception as e:
            errors.append(f"Performance testing failed: {str(e)}")
        
        execution_time = time.time() - start_time
        
        # Performance validator provides warnings but doesn't fail validation
        return ValidatorResult(
            validator_name=self.name,
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data=data,
            execution_time=execution_time
        )
    
    async def _test_sequential_performance(
        self, 
        context: ValidationContext, 
        iterations: int
    ) -> List[float]:
        """Test sequential request performance."""
        response_times = []
        
        for i in range(iterations):
            try:
                start = time.time()
                
                # Send a simple request (tools/list or resources/list)
                if context.capabilities.get("tools"):
                    request = self._create_jsonrpc_request("tools/list")
                elif context.capabilities.get("resources"):
                    request = self._create_jsonrpc_request("resources/list")
                else:
                    continue
                
                context.process.stdin.write(request.encode())
                await context.process.stdin.drain()
                
                # Wait for response
                response_line = await asyncio.wait_for(
                    context.process.stdout.readline(),
                    timeout=5.0
                )
                
                end = time.time()
                response_time_ms = (end - start) * 1000
                response_times.append(response_time_ms)
                
                # Validate response is valid JSON
                self._parse_jsonrpc_response(response_line.decode())
                
            except asyncio.TimeoutError:
                # Count as failed request
                continue
            except Exception:
                # Count as failed request
                continue
        
        return response_times
    
    async def _test_concurrent_performance(
        self, 
        context: ValidationContext, 
        concurrent_count: int
    ) -> bool:
        """Test concurrent request handling."""
        try:
            # Create multiple concurrent requests
            tasks = []
            for _ in range(concurrent_count):
                task = self._send_concurrent_request(context)
                tasks.append(task)
            
            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if most requests succeeded
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            success_rate = success_count / len(results)
            
            return success_rate >= 0.7  # 70% success rate threshold
            
        except Exception:
            return False
    
    async def _send_concurrent_request(self, context: ValidationContext) -> bool:
        """Send a single concurrent request."""
        try:
            if context.capabilities.get("tools"):
                request = self._create_jsonrpc_request("tools/list")
            elif context.capabilities.get("resources"):
                request = self._create_jsonrpc_request("resources/list")
            else:
                return False
            
            context.process.stdin.write(request.encode())
            await context.process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                context.process.stdout.readline(),
                timeout=3.0
            )
            
            self._parse_jsonrpc_response(response_line.decode())
            return True
            
        except Exception:
            return False
    
    def _calculate_performance_grade(self, data: Dict[str, Any]) -> str:
        """Calculate performance grade based on metrics."""
        avg_time = data.get("average_response_time", float('inf'))
        max_time = data.get("max_response_time", float('inf'))
        concurrent_passed = data.get("concurrent_test_passed", False)
        
        if avg_time < 100 and max_time < 200 and concurrent_passed:
            return "excellent"
        elif avg_time < 250 and max_time < 500 and concurrent_passed:
            return "good"
        elif avg_time < 500 and max_time < 1000:
            return "acceptable"
        elif avg_time < 1000:
            return "slow"
        else:
            return "poor"
    
    def _create_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> str:
        """Create a JSON-RPC 2.0 request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
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


# Example of how to register and use the custom validator
def register_custom_validators(orchestrator):
    """Register custom validators with the orchestrator."""
    orchestrator.register_validator(PerformanceValidator)


# Example configuration for the custom validator
CUSTOM_CONFIG = {
    "active_profile": "performance_testing",
    "profiles": {
        "performance_testing": {
            "description": "Comprehensive testing including performance",
            "validators": {
                "protocol": {
                    "enabled": True,
                    "required": True
                },
                "capabilities": {
                    "enabled": True,
                    "required": False
                },
                "performance": {
                    "enabled": True,
                    "required": False,
                    "timeout": 30.0,
                    "parameters": {
                        "max_response_time_ms": 500,
                        "test_iterations": 10,
                        "concurrent_requests": 5
                    }
                }
            }
        }
    }
}