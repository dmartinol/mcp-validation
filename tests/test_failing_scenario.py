#!/usr/bin/env python3
"""Test a specific failing scenario with debug output."""

import asyncio
import os
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_failing_scenario():
    """Test a specific scenario that should fail with detailed debug output."""
    
    print("🐛 Registry Validator Failing Scenario Analysis\n")
    print("=" * 70)
    
    # Enable debug mode
    os.environ['MCP_REGISTRY_DEBUG'] = '1'
    
    print("Testing scenario that demonstrates why registry validation fails:")
    print("- Multiple non-existent packages")
    print("- Version mismatches") 
    print("- Mixed existing/non-existing packages")
    print("-" * 70)
    
    # Create a scenario that will definitely fail
    validator = RegistryValidator({
        "enabled": True,
        "packages": [
            # This package doesn't exist
            {"name": "absolutely-fake-package-xyz123", "type": "npm"},
            
            # This package exists but version doesn't  
            {"name": "lodash", "type": "npm", "version": "999.888.777"},
            
            # This package exists and should work
            {"name": "express", "type": "npm"},
            
            # This PyPI package doesn't exist
            {"name": "totally-fake-python-package-abc456", "type": "pypi"},
            
            # Docker image that doesn't exist
            {"name": "fake-docker-image-def789", "type": "docker"}
        ]
    })
    
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    print("\n🔍 Running validation with debug enabled...")
    print("-" * 70)
    
    result = await validator.validate(context)
    
    print("-" * 70)
    print(f"\n📊 FINAL ANALYSIS:")
    print(f"  Overall Result: {'✅ PASS' if result.passed else '❌ FAIL'}")
    print(f"  Total Packages: {result.data['total_packages']}")
    print(f"  Packages Found: {result.data['packages_found']}")
    print(f"  Packages Missing: {result.data['packages_missing']}")
    print(f"  Registry Errors: {result.data['registry_errors']}")
    print(f"  Validation Errors: {len(result.errors)}")
    print(f"  Validation Warnings: {len(result.warnings)}")
    print(f"  Execution Time: {result.execution_time:.2f}s")
    
    if result.errors:
        print(f"\n❌ ERRORS (causing validation failure):")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")
    
    if result.warnings:
        print(f"\n⚠️  WARNINGS (not causing failure):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")
    
    print(f"\n📦 DETAILED PACKAGE RESULTS:")
    for i, pkg_result in enumerate(result.data['packages_checked'], 1):
        name = pkg_result['name']
        exists = pkg_result.get('exists', False)
        error = pkg_result.get('error', 'None')
        registry = pkg_result.get('registry_url', 'Unknown').split('/')[-1]
        
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"  {i}. {name} [{registry}] - {status}")
        if error != 'None':
            print(f"     Error: {error}")
    
    print(f"\n🎯 WHY THIS VALIDATION FAILED:")
    print(f"  The registry validator failed because {result.data['packages_missing']} out of")
    print(f"  {result.data['total_packages']} packages could not be found in their registries.")
    print(f"  Even though {result.data['packages_found']} packages exist, the validation")
    print(f"  requires ALL packages to be available for it to pass.")
    
    print(f"\n💡 HOW TO FIX:")
    if result.errors:
        print(f"  1. Check package names for typos")
        print(f"  2. Verify packages exist in the specified registries")
        print(f"  3. Consider using different package names or registries")
        print(f"  4. Remove packages that are not actually required")
    
    if result.warnings:
        print(f"\n  Version-related warnings can be fixed by:")
        print(f"  1. Using existing version numbers")
        print(f"  2. Removing version constraints (allow any version)")
        print(f"  3. Updating to newer versions that exist")


if __name__ == "__main__":
    asyncio.run(test_failing_scenario())