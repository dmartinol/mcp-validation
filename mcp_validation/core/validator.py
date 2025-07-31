"""Core validation orchestrator for MCP servers."""

import asyncio
import os
import time
from typing import Dict, Any, List, Optional, Type

from ..validators.base import BaseValidator, ValidationContext, ValidatorResult
from ..config.settings import ConfigurationManager, ValidationProfile
from .result import ValidationSession
from .transport import JSONRPCTransport


class ValidatorRegistry:
    """Registry for available validators."""
    
    def __init__(self):
        self._validators: Dict[str, Type[BaseValidator]] = {}
    
    def register(self, validator_class: Type[BaseValidator]) -> None:
        """Register a validator class."""
        # Create temporary instance to get name
        temp_instance = validator_class()
        self._validators[temp_instance.name] = validator_class
    
    def get_validator(self, name: str) -> Optional[Type[BaseValidator]]:
        """Get validator class by name."""
        return self._validators.get(name)
    
    def list_validators(self) -> List[str]:
        """List all registered validator names."""
        return list(self._validators.keys())
    
    def create_validator(self, name: str, config: Dict[str, Any] = None) -> Optional[BaseValidator]:
        """Create validator instance with configuration."""
        validator_class = self.get_validator(name)
        if validator_class:
            return validator_class(config)
        return None


class MCPValidationOrchestrator:
    """Orchestrates MCP server validation using configurable validators."""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.registry = ValidatorRegistry()
        self._register_builtin_validators()
    
    def _register_builtin_validators(self) -> None:
        """Register built-in validators."""
        # Import and register built-in validators
        try:
            from ..validators.protocol import ProtocolValidator
            from ..validators.capabilities import CapabilitiesValidator  
            from ..validators.ping import PingValidator
            from ..validators.errors import ErrorComplianceValidator
            from ..validators.security import SecurityValidator
            
            self.registry.register(ProtocolValidator)
            self.registry.register(CapabilitiesValidator)
            self.registry.register(PingValidator)
            self.registry.register(ErrorComplianceValidator)
            self.registry.register(SecurityValidator)
        except ImportError as e:
            # Handle missing validators gracefully
            print(f"Warning: Some validators not available: {e}")
    
    def register_validator(self, validator_class: Type[BaseValidator]) -> None:
        """Register a custom validator."""
        self.registry.register(validator_class)
    
    async def validate_server(
        self, 
        command_args: List[str], 
        env_vars: Dict[str, str] = None,
        profile_name: Optional[str] = None
    ) -> ValidationSession:
        """Execute complete validation session against MCP server."""
        
        start_time = time.time()
        errors = []
        warnings = []
        validator_results = []
        
        # Use specified profile or active profile
        if profile_name:
            if profile_name not in self.config_manager.profiles:
                raise ValueError(f"Profile '{profile_name}' not found")
            profile = self.config_manager.profiles[profile_name]
        else:
            profile = self.config_manager.get_active_profile()
        
        try:
            # Start MCP server process
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            process = await asyncio.create_subprocess_exec(
                *command_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Create transport and validation context
            transport = JSONRPCTransport(process)
            context = ValidationContext(
                process=process,
                server_info={},
                capabilities={},
                timeout=profile.global_timeout
            )
            context.transport = transport
            
            # Create and configure validators
            validators = self._create_validators(profile)
            
            # Execute validators
            if profile.parallel_execution:
                validator_results = await self._execute_validators_parallel(validators, context, profile)
            else:
                validator_results = await self._execute_validators_sequential(validators, context, profile)
            
            # Clean up process
            await self._cleanup_process(process)
            
        except Exception as e:
            errors.append(f"Validation setup failed: {str(e)}")
        
        # Determine overall success
        overall_success = self._determine_overall_success(validator_results, profile)
        
        # Collect errors and warnings
        for result in validator_results:
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        
        execution_time = time.time() - start_time
        
        return ValidationSession(
            profile_name=profile.name,
            overall_success=overall_success,
            execution_time=execution_time,
            validator_results=validator_results,
            errors=errors,
            warnings=warnings
        )
    
    def _create_validators(self, profile: ValidationProfile) -> List[BaseValidator]:
        """Create configured validator instances."""
        validators = []
        
        for validator_name, validator_config in profile.validators.items():
            if not validator_config.enabled:
                continue
                
            validator = self.registry.create_validator(
                validator_name, 
                {
                    'enabled': validator_config.enabled,
                    'required': validator_config.required,
                    'timeout': validator_config.timeout or profile.global_timeout,
                    **validator_config.parameters
                }
            )
            
            if validator:
                validators.append(validator)
            else:
                print(f"Warning: Validator '{validator_name}' not found")
        
        # Sort by dependencies (simple topological sort)
        return self._sort_validators_by_dependencies(validators)
    
    def _sort_validators_by_dependencies(self, validators: List[BaseValidator]) -> List[BaseValidator]:
        """Sort validators by their dependencies."""
        # Simple dependency resolution - could be enhanced
        validator_map = {v.name: v for v in validators}
        sorted_validators = []
        processed = set()
        
        def process_validator(validator: BaseValidator):
            if validator.name in processed:
                return
            
            # Process dependencies first
            for dep_name in validator.dependencies:
                if dep_name in validator_map:
                    process_validator(validator_map[dep_name])
            
            sorted_validators.append(validator)
            processed.add(validator.name)
        
        for validator in validators:
            process_validator(validator)
        
        return sorted_validators
    
    async def _execute_validators_sequential(
        self, 
        validators: List[BaseValidator], 
        context: ValidationContext,
        profile: ValidationProfile
    ) -> List[ValidatorResult]:
        """Execute validators sequentially."""
        results = []
        
        for validator in validators:
            if not validator.is_applicable(context):
                continue
            
            try:
                result = await validator.validate(context)
                results.append(result)
                
                # Update context with results (for dependent validators)
                if validator.name == "protocol":
                    context.server_info.update(result.data.get("server_info", {}))
                    context.capabilities.update(result.data.get("capabilities", {}))
                
                # Stop on required validator failure if configured
                if not profile.continue_on_failure and validator.config.get('required') and not result.passed:
                    break
                    
            except Exception as e:
                error_result = ValidatorResult(
                    validator_name=validator.name,
                    passed=False,
                    errors=[f"Validator execution failed: {str(e)}"],
                    warnings=[],
                    data={},
                    execution_time=0.0
                )
                results.append(error_result)
                
                if not profile.continue_on_failure and validator.config.get('required'):
                    break
        
        return results
    
    async def _execute_validators_parallel(
        self, 
        validators: List[BaseValidator], 
        context: ValidationContext,
        profile: ValidationProfile
    ) -> List[ValidatorResult]:
        """Execute validators in parallel (where possible)."""
        # For now, implement sequential execution
        # Parallel execution would need more sophisticated dependency handling
        return await self._execute_validators_sequential(validators, context, profile)
    
    def _determine_overall_success(
        self, 
        validator_results: List[ValidatorResult], 
        profile: ValidationProfile
    ) -> bool:
        """Determine if overall validation was successful."""
        for result in validator_results:
            validator_config = profile.validators.get(result.validator_name)
            if validator_config and validator_config.required and not result.passed:
                return False
        return True
    
    async def _cleanup_process(self, process: asyncio.subprocess.Process) -> None:
        """Clean up the MCP server process."""
        if process.returncode is None:
            try:
                if process.stdin:
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