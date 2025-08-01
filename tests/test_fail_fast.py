#!/usr/bin/env python3
"""Test fail-fast behavior with registry validation first."""

import asyncio
import tempfile
import json
import os
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.config.settings import ConfigurationManager


async def test_fail_fast_validation():
    """Test fail-fast validation with registry checks first."""
    
    print("=== Fail-Fast Validation Demo ===\n")
    
    # Test 1: Configuration with missing packages (should fail fast)
    failing_config = {
        "active_profile": "fail_fast_test",
        "profiles": {
            "fail_fast_test": {
                "description": "Fail-fast test with missing dependencies",
                "validators": {
                    "registry": {
                        "enabled": True,
                        "required": True,
                        "parameters": {
                            "packages": [
                                {"name": "definitely-not-real-package-12345", "type": "npm"},
                                {"name": "another-fake-package", "type": "pypi"},
                                {"name": "express", "type": "npm"}  # This one exists
                            ]
                        }
                    },
                    "protocol": {
                        "enabled": True,
                        "required": True
                    }
                },
                "continue_on_failure": False,
                "global_timeout": 30.0
            }
        }
    }
    
    # Test 2: Configuration with all valid packages (should continue)
    passing_config = {
        "active_profile": "fail_fast_pass",
        "profiles": {
            "fail_fast_pass": {
                "description": "Fail-fast test with valid dependencies",
                "validators": {
                    "registry": {
                        "enabled": True,
                        "required": True,
                        "parameters": {
                            "packages": [
                                {"name": "lodash", "type": "npm"},
                                {"name": "requests", "type": "pypi"},
                                {"name": "alpine", "type": "docker"}
                            ]
                        }
                    },
                    "protocol": {
                        "enabled": True,
                        "required": True
                    }
                },
                "continue_on_failure": False,
                "global_timeout": 30.0
            }
        }
    }
    
    # Test failing case
    print("🔍 Test 1: Validation with missing dependencies (should fail fast)")
    await run_validation_test(failing_config, "fail_fast_test")
    
    print("\n" + "="*60 + "\n")
    
    # Test passing case
    print("🔍 Test 2: Validation with existing dependencies (should continue)")
    await run_validation_test(passing_config, "fail_fast_pass")
    
    print("\n" + "="*60 + "\n")
    
    # Show the built-in fail_fast profile
    print("🔍 Test 3: Built-in fail_fast profile")
    config_manager = ConfigurationManager()
    config_manager.set_active_profile("fail_fast")
    
    profile = config_manager.get_active_profile()
    print(f"Profile: {profile.name}")
    print(f"Description: {profile.description}")
    print(f"Continue on failure: {profile.continue_on_failure}")
    
    print("\nValidator execution order:")
    for i, (validator_name, validator_config) in enumerate(profile.validators.items(), 1):
        status = "REQUIRED" if validator_config.required else "OPTIONAL"
        print(f"  {i}. {validator_name.upper()} ({status})")
        if validator_name == "registry":
            packages = validator_config.parameters.get("packages", [])
            print(f"     Will check {len(packages)} packages before proceeding")


async def run_validation_test(config_data, profile_name):
    """Run a validation test with the given configuration."""
    
    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f, indent=2)
        config_file = f.name
    
    try:
        # Load configuration
        config_manager = ConfigurationManager(config_file)
        config_manager.set_active_profile(profile_name)
        
        orchestrator = MCPValidationOrchestrator(config_manager)
        profile = config_manager.get_active_profile()
        
        print(f"Profile: {profile.name}")
        print(f"Continue on failure: {profile.continue_on_failure}")
        
        # Create validators in order
        validators = []
        for validator_name, validator_config in profile.validators.items():
            if validator_config.enabled:
                validator = orchestrator.registry.create_validator(
                    validator_name,
                    {
                        'enabled': validator_config.enabled,
                        'required': validator_config.required,
                        **validator_config.parameters
                    }
                )
                if validator:
                    validators.append(validator)
        
        # Simulate sequential execution with fail-fast
        from mcp_validation.validators.base import ValidationContext
        context = ValidationContext(
            process=None,
            server_info={},
            capabilities={},
            timeout=30.0
        )
        
        print(f"\nExecuting {len(validators)} validators:")
        
        overall_success = True
        for i, validator in enumerate(validators, 1):
            print(f"\n  {i}. Running {validator.name.upper()} validator...")
            
            if validator.name == "registry":
                # Actually run registry validation
                result = await validator.validate(context)
                
                print(f"     Result: {'✅ PASS' if result.passed else '❌ FAIL'}")
                print(f"     Packages: {result.data['packages_found']}/{result.data['total_packages']} found")
                print(f"     Time: {result.execution_time:.2f}s")
                
                if result.errors:
                    print("     Errors:")
                    for error in result.errors[:2]:  # Show first 2 errors
                        print(f"       • {error}")
                    if len(result.errors) > 2:
                        print(f"       ... and {len(result.errors) - 2} more")
                
                if not result.passed and profile.validators[validator.name].required:
                    print(f"     🛑 STOPPING: Required validator failed")
                    overall_success = False
                    break
                    
            else:
                # Simulate other validators
                print(f"     Result: ⏭️  SKIPPED (no MCP server process)")
        
        if overall_success:
            print(f"\n✅ Validation would continue to completion")
        else:
            print(f"\n❌ Validation stopped early due to dependency failures")
            
    finally:
        os.unlink(config_file)


if __name__ == "__main__":
    asyncio.run(test_fail_fast_validation())