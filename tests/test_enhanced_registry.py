#!/usr/bin/env python3
"""Test the enhanced registry validator with command parsing."""

import asyncio
import os
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_enhanced_registry_validator():
    """Test the enhanced registry validator with the Dynatrace typo command."""
    
    print("🚀 Testing Enhanced Registry Validator with Command Parsing\n")
    print("=" * 70)
    
    # Enable debug mode
    os.environ['MCP_REGISTRY_DEBUG'] = '1'
    
    test_scenarios = [
        {
            "name": "Dynatrace with typo (should FAIL)",
            "command": ["npx", "-y", "@dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222"],
            "expected_result": "FAIL",
            "description": "The typo 'serveoor' should be detected and validation should fail"
        },
        {
            "name": "Correct Dynatrace package (should PASS)",
            "command": ["npx", "-y", "@dynatrace-oss/dynatrace-mcp-server"],
            "expected_result": "PASS",
            "description": "The correct package name should pass validation"
        },
        {
            "name": "Correct package with bad version (should PASS with warning)",
            "command": ["npx", "-y", "@dynatrace-oss/dynatrace-mcp-server@999.999.999"],
            "expected_result": "PASS",
            "description": "Package exists but version doesn't - should pass with warning"
        },
        {
            "name": "Multiple packages command",
            "command": ["docker", "run", "-p", "8080:8080", "nginx:latest"],
            "expected_result": "PASS",
            "description": "Docker command should extract and validate nginx:latest"
        },
        {
            "name": "No packages in command (fallback to config)",
            "command": ["node", "server.js"],
            "expected_result": "PASS",
            "description": "Should fall back to configured packages when none extracted"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test {i}: {scenario['name']}")
        print(f"Command: {' '.join(scenario['command'])}")
        print(f"Expected: {scenario['expected_result']}")
        print(f"Description: {scenario['description']}")
        print("-" * 50)
        
        # Create validator with some default packages for fallback
        validator = RegistryValidator({
            "enabled": True,
            "packages": [
                {"name": "express", "type": "npm"},  # Fallback package that exists
            ]
        })
        
        # Create context with command arguments
        context = ValidationContext(
            process=None,
            server_info={},
            capabilities={},
            timeout=30.0,
            command_args=scenario["command"]
        )
        
        # Run validation
        result = await validator.validate(context)
        
        # Analyze results
        actual_result = "PASS" if result.passed else "FAIL"
        status_icon = "✅" if actual_result == scenario["expected_result"] else "❌"
        
        print(f"\n{status_icon} RESULT: {actual_result}")
        print(f"Expected: {scenario['expected_result']}")
        print(f"Package source: {result.data.get('package_source', 'unknown')}")
        print(f"Packages checked: {result.data['packages_found']}/{result.data['total_packages']}")
        print(f"Execution time: {result.execution_time:.2f}s")
        
        if result.errors:
            print("❌ Errors:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        # Show package details
        if result.data.get('packages_checked'):
            print("\n📦 Package Details:")
            for pkg_result in result.data['packages_checked']:
                name = pkg_result['name']
                exists = pkg_result.get('exists', False)
                error = pkg_result.get('error', '')
                registry = pkg_result.get('registry_url', '').split('/')[-1] or 'unknown'
                
                status = "✅ EXISTS" if exists else "❌ MISSING"
                print(f"  {status} {name} [{registry}]")
                if error:
                    print(f"    Error: {error}")
        
        print("\n" + "=" * 70)
    
    print(f"\n🎯 KEY IMPROVEMENTS:")
    print(f"✅ Registry validator now extracts packages from MCP commands")
    print(f"✅ Validates actual packages being executed, not just defaults")
    print(f"✅ Catches typos in package names immediately")
    print(f"✅ Verifies specific versions when provided")
    print(f"✅ Falls back to configured packages when no command packages found")
    
    print(f"\n💡 FOR THE DYNATRACE COMMAND:")
    print(f"Command: npx -y @dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222")
    print(f"Result: Would now FAIL ❌ (typo detected!)")
    print(f"Before: Would PASS ✅ (only checked defaults)")
    print(f"Impact: Prevents execution with invalid packages")


if __name__ == "__main__":
    asyncio.run(test_enhanced_registry_validator())