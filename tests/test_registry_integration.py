#!/usr/bin/env python3
"""Test registry validator integration with MCP validation framework."""

import asyncio
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.config.settings import ConfigurationManager, ValidationProfile, ValidatorConfig


async def test_registry_integration():
    """Test that registry validator is properly integrated."""
    
    # Create a custom profile with only registry validation (no MCP server needed)
    registry_profile = ValidationProfile(
        name="registry_only",
        description="Registry validation only - no MCP server required",
        validators={
            "registry": ValidatorConfig(
                enabled=True,
                required=True,
                parameters={
                    "packages": [
                        {"name": "express", "type": "npm"},
                        {"name": "requests", "type": "pypi"},
                        {"name": "node", "type": "docker"},
                        "typescript",  # Test simple string format
                        {"name": "nonexistent-package-12345", "type": "npm"}  # Should fail
                    ]
                }
            )
        },
        global_timeout=30.0,
        continue_on_failure=True
    )
    
    # Create config manager and add our profile
    config_manager = ConfigurationManager()
    config_manager.create_profile(registry_profile)
    config_manager.set_active_profile("registry_only")
    
    # Create orchestrator
    orchestrator = MCPValidationOrchestrator(config_manager)
    
    # Check that registry validator is registered
    print("Registered validators:", orchestrator.registry.list_validators())
    
    # Test registry validator creation
    registry_validator = orchestrator.registry.create_validator("registry", {
        "packages": [{"name": "express", "type": "npm"}]
    })
    
    if registry_validator:
        print(f"✓ Registry validator created: {registry_validator.name}")
        print(f"  Description: {registry_validator.description}")
        print(f"  Packages configured: {len(registry_validator.packages)}")
    else:
        print("✗ Failed to create registry validator")
        return
    
    # Test validator execution without MCP server
    from mcp_validation.validators.base import ValidationContext
    
    context = ValidationContext(
        process=None,  # Registry validator doesn't need MCP process
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    print("\n=== Testing Registry Validator Execution ===")
    result = await registry_validator.validate(context)
    
    print(f"Validator: {result.validator_name}")
    print(f"Passed: {result.passed}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print(f"Packages checked: {result.data.get('total_packages', 0)}")
    print(f"Packages found: {result.data.get('packages_found', 0)}")
    print(f"Packages missing: {result.data.get('packages_missing', 0)}")
    
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    print("\nPackage Results:")
    for pkg_result in result.data.get('packages_checked', []):
        status = "✓" if pkg_result.get('exists', False) else "✗"
        name = pkg_result['name']
        registry_url = pkg_result.get('registry_url', '')
        print(f"  {status} {name} ({registry_url})")
        if pkg_result.get('error'):
            print(f"    Error: {pkg_result['error']}")


if __name__ == "__main__":
    asyncio.run(test_registry_integration())