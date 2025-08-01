#!/usr/bin/env python3
"""Test the debug messages in registry validator."""

import asyncio
import os
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_debug_messages():
    """Test debug messages with various scenarios."""
    
    print("🐛 Testing Registry Validator Debug Messages\n")
    print("=" * 60)
    
    # Enable debug mode
    os.environ['MCP_REGISTRY_DEBUG'] = '1'
    
    test_scenarios = [
        {
            "name": "Valid packages (should pass)",
            "packages": [
                {"name": "lodash", "type": "npm"},
                {"name": "requests", "type": "pypi"}
            ]
        },
        {
            "name": "Invalid packages (should fail)",
            "packages": [
                {"name": "definitely-fake-npm-xyz", "type": "npm"},
                {"name": "definitely-fake-pypi-abc", "type": "pypi"}
            ]
        },
        {
            "name": "Mixed scenario (should partially pass)",
            "packages": [
                {"name": "lodash", "type": "npm"},  # exists
                {"name": "fake-package-999", "type": "npm"}  # doesn't exist
            ]
        },
        {
            "name": "Version validation (should warn)",
            "packages": [
                {"name": "lodash", "type": "npm", "version": "999.999.999"}
            ]
        },
        {
            "name": "No packages (should skip)",
            "packages": []
        }
    ]
    
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test {i}: {scenario['name']}")
        print("-" * 40)
        
        # Create validator
        validator = RegistryValidator({
            "enabled": True,
            "packages": scenario["packages"]
        })
        
        # Run validation with debug enabled
        result = await validator.validate(context)
        
        print(f"\nSummary:")
        print(f"  Result: {'✅ PASS' if result.passed else '❌ FAIL'}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        print(f"  Found: {result.data['packages_found']}/{result.data['total_packages']}")
        
        if result.errors:
            print(f"  Error details:")
            for error in result.errors:
                print(f"    - {error}")
        
        print("\n" + "=" * 60)
    
    # Disable debug mode
    print(f"\n🔇 Testing with debug disabled")
    print("-" * 40)
    os.environ['MCP_REGISTRY_DEBUG'] = '0'
    
    validator = RegistryValidator({
        "enabled": True,
        "packages": [{"name": "fake-package-silent", "type": "npm"}]
    })
    
    print("Running validation (should be silent)...")
    result = await validator.validate(context)
    print(f"Result: {'✅ PASS' if result.passed else '❌ FAIL'} (no debug output above)")
    
    print(f"\n📋 Debug Usage Instructions:")
    print(f"To enable debug mode, set environment variable:")
    print(f"  export MCP_REGISTRY_DEBUG=1")
    print(f"  # or")
    print(f"  MCP_REGISTRY_DEBUG=1 python your_script.py")
    print(f"\nTo disable debug mode:")
    print(f"  export MCP_REGISTRY_DEBUG=0")
    print(f"  # or simply unset the variable")


if __name__ == "__main__":
    asyncio.run(test_debug_messages())