#!/usr/bin/env python3
"""Test fail-fast behavior with the Dynatrace typo command."""

import asyncio
import os
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_dynatrace_fail_fast():
    """Test fail-fast behavior with the specific Dynatrace typo command."""
    
    print("🚀 Testing Fail-Fast with Dynatrace Typo Command\n")
    print("=" * 70)
    
    # Enable debug mode
    os.environ['MCP_REGISTRY_DEBUG'] = '1'
    
    print("Command: npx -y @dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222")
    print("Expected: Registry validation should FAIL and stop execution")
    print("-" * 50)
    
    # Create registry validator with required=True
    validator = RegistryValidator({
        "enabled": True,
        "required": True,  # This makes it fail-fast
        "packages": []  # Empty so it will use command packages
    })
    
    # Create context with the typo command
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0,
        command_args=["npx", "-y", "@dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222"]
    )
    
    print("\n🔍 RUNNING REGISTRY VALIDATION...")
    result = await validator.validate(context)
    
    print(f"\n📊 REGISTRY VALIDATION RESULT:")
    print(f"Validator: {result.validator_name}")
    print(f"Passed: {'✅ YES' if result.passed else '❌ NO'}")
    print(f"Required: {'✅ YES' if validator.config.get('required') else '❌ NO'}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Packages Found: {result.data['packages_found']}/{result.data['total_packages']}")
    print(f"Package Source: {result.data.get('package_source', 'unknown')}")
    
    if result.errors:
        print(f"\n❌ ERRORS ({len(result.errors)}):")
        for error in result.errors:
            print(f"  • {error}")
    
    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    # Show package details
    print(f"\n📦 PACKAGE DETAILS:")
    for pkg_result in result.data.get('packages_checked', []):
        name = pkg_result['name']
        exists = pkg_result.get('exists', False)
        error = pkg_result.get('error', '')
        registry = pkg_result.get('registry_url', '').split('/')[-1] or 'unknown'
        
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"  {status} {name} [{registry}]")
        if error:
            print(f"    💥 Error: {error}")
    
    # Determine if validation should continue
    should_stop = not result.passed and validator.config.get('required', False)
    
    print(f"\n🎯 FAIL-FAST DECISION:")
    if should_stop:
        print("🛑 VALIDATION WOULD STOP HERE")
        print("   ✅ Registry validation failed")
        print("   ✅ Registry validator is marked as required")
        print("   ✅ continue_on_failure=False in profile")
        print("   ❌ Protocol validator would NOT run")
        print("   ❌ Other validators would NOT run")
        print("   ❌ MCP server would NOT be started")
    else:
        print("▶️  VALIDATION WOULD CONTINUE")
        print("   ✅ Registry validation passed")
        print("   ➡️  Protocol validator would run next")
    
    print(f"\n💡 COMPARISON:")
    print(f"OLD BEHAVIOR:")
    print(f"  • Only checked default packages (express, requests, node)")
    print(f"  • All defaults exist → Registry validation PASSED")
    print(f"  • Would continue to start MCP server with typo command")
    print(f"  • MCP server startup would fail later")
    
    print(f"\nNEW BEHAVIOR:")
    print(f"  • Extracts packages from actual command")
    print(f"  • Checks @dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222")
    print(f"  • Package doesn't exist → Registry validation FAILS")
    print(f"  • Stops validation immediately (fail-fast)")
    print(f"  • Prevents wasted time on doomed command")
    
    print(f"\n🚀 BENEFITS:")
    print(f"✅ Catches typos before MCP server startup")
    print(f"✅ Saves time by failing fast")
    print(f"✅ Clear error message about missing package")
    print(f"✅ Prevents confusing downstream errors")
    
    return result.passed


if __name__ == "__main__":
    asyncio.run(test_dynatrace_fail_fast())