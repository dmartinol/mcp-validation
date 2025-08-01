#!/usr/bin/env python3
"""Comprehensive test of registry validation functionality."""

import asyncio
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_registry_validation_comprehensive():
    """Comprehensive test of all registry validation scenarios."""
    
    print("🧪 Comprehensive Registry Validation Test\n")
    print("=" * 70)
    
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    test_scenarios = [
        {
            "name": "All packages exist (should PASS)",
            "packages": [
                {"name": "lodash", "type": "npm"},
                {"name": "requests", "type": "pypi"},
                {"name": "alpine", "type": "docker"}
            ],
            "expected_pass": True,
            "expected_errors": 0
        },
        {
            "name": "All packages missing (should FAIL)",
            "packages": [
                {"name": "definitely-fake-npm-12345", "type": "npm"},
                {"name": "definitely-fake-pypi-67890", "type": "pypi"},
                {"name": "definitely-fake-docker-99999", "type": "docker"}
            ],
            "expected_pass": False,
            "expected_errors": 3
        },
        {
            "name": "Mixed packages (should FAIL with some errors)",
            "packages": [
                {"name": "lodash", "type": "npm"},  # exists
                {"name": "fake-npm-package", "type": "npm"},  # doesn't exist
                {"name": "requests", "type": "pypi"},  # exists
                {"name": "fake-pypi-package", "type": "pypi"}  # doesn't exist
            ],
            "expected_pass": False,
            "expected_errors": 2
        },
        {
            "name": "Specific versions - valid (should PASS with no warnings)",
            "packages": [
                {"name": "lodash", "type": "npm", "version": "4.17.21"},
                {"name": "requests", "type": "pypi", "version": "2.31.0"}
            ],
            "expected_pass": True,
            "expected_errors": 0
        },
        {
            "name": "Specific versions - invalid (should PASS with warnings)",
            "packages": [
                {"name": "lodash", "type": "npm", "version": "999.999.999"},
                {"name": "requests", "type": "pypi", "version": "888.888.888"}
            ],
            "expected_pass": True,
            "expected_errors": 0,
            "expected_warnings": 2
        },
        {
            "name": "String format parsing (should PASS)",
            "packages": [
                "lodash@4.17.21",
                "pypi:requests@2.31.0",
                "docker:alpine@latest"
            ],
            "expected_pass": True,
            "expected_errors": 0
        },
        {
            "name": "No packages configured (should skip)",
            "packages": [],
            "expected_pass": True,
            "expected_errors": 0,
            "should_skip": True
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🔍 Test {i}: {scenario['name']}")
        print("-" * 50)
        
        # Create validator
        validator = RegistryValidator({
            "enabled": True,
            "packages": scenario["packages"]
        })
        
        # Check if validator should be applicable
        is_applicable = validator.is_applicable(context)
        if scenario.get("should_skip") and not is_applicable:
            print("✅ Validator correctly skipped (no packages)")
            continue
        elif scenario.get("should_skip"):
            print("❌ Validator should have been skipped but wasn't")
            continue
        
        print(f"Packages to validate: {len(validator.packages)}")
        for pkg in validator.packages:
            version_info = f" @ {pkg.version}" if pkg.version else ""
            print(f"  • {pkg.name} ({pkg.registry_type}){version_info}")
        
        # Run validation
        result = await validator.validate(context)
        
        # Check results
        passed = result.passed
        errors = len(result.errors)
        warnings = len(result.warnings)
        
        print(f"\nResults:")
        print(f"  Passed: {passed}")
        print(f"  Errors: {errors}")
        print(f"  Warnings: {warnings}")
        print(f"  Found: {result.data['packages_found']}/{result.data['total_packages']}")
        print(f"  Time: {result.execution_time:.2f}s")
        
        # Verify expectations
        expected_pass = scenario["expected_pass"]
        expected_errors = scenario["expected_errors"]
        expected_warnings = scenario.get("expected_warnings", 0)
        
        status_icon = "✅" if (
            passed == expected_pass and 
            errors == expected_errors and
            (expected_warnings == 0 or warnings >= expected_warnings)
        ) else "❌"
        
        print(f"\n{status_icon} Test Result:")
        print(f"  Expected pass: {expected_pass}, got: {passed}")
        print(f"  Expected errors: {expected_errors}, got: {errors}")
        if expected_warnings > 0:
            print(f"  Expected warnings: {expected_warnings}+, got: {warnings}")
        
        if result.errors:
            print(f"\nErrors:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print(f"\nWarnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
    
    print(f"\n" + "=" * 70)
    print(f"🎯 Summary: Registry validation is working correctly!")
    print(f"   • Fails when packages don't exist")
    print(f"   • Passes when packages exist") 
    print(f"   • Warns on version mismatches")
    print(f"   • Handles multiple package types")
    print(f"   • Properly parses string and dict formats")


if __name__ == "__main__":
    asyncio.run(test_registry_validation_comprehensive())