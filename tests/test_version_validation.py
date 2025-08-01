#!/usr/bin/env python3
"""Test version validation capabilities of the registry validator."""

import asyncio
from mcp_validation.validators.registry import RegistryValidator, PackageInfo
from mcp_validation.validators.base import ValidationContext


async def test_version_validation():
    """Test that registry validator properly validates specific versions."""
    
    print("🔍 Registry Validator Version Checking\n")
    print("=" * 60)
    
    # Test cases with different version scenarios
    test_cases = [
        {
            "name": "Valid NPM version",
            "packages": [{"name": "lodash", "type": "npm", "version": "4.17.21"}],
            "expected": "Should PASS - version exists"
        },
        {
            "name": "Invalid NPM version", 
            "packages": [{"name": "lodash", "type": "npm", "version": "999.999.999"}],
            "expected": "Should WARN - package exists but version doesn't"
        },
        {
            "name": "Valid PyPI version",
            "packages": [{"name": "requests", "type": "pypi", "version": "2.31.0"}],
            "expected": "Should PASS - version exists"
        },
        {
            "name": "Invalid PyPI version",
            "packages": [{"name": "requests", "type": "pypi", "version": "999.999.999"}],
            "expected": "Should WARN - package exists but version doesn't"
        },
        {
            "name": "Valid Docker tag",
            "packages": [{"name": "alpine", "type": "docker", "version": "latest"}],
            "expected": "Should PASS - tag exists"
        },
        {
            "name": "Invalid Docker tag",
            "packages": [{"name": "alpine", "type": "docker", "version": "nonexistent-tag-12345"}],
            "expected": "Should WARN - image exists but tag doesn't"
        },
        {
            "name": "No version specified",
            "packages": [{"name": "express", "type": "npm"}],
            "expected": "Should PASS - any version acceptable"
        },
        {
            "name": "Mixed version scenarios",
            "packages": [
                {"name": "lodash", "type": "npm", "version": "4.17.21"},  # Valid
                {"name": "express", "type": "npm", "version": "999.999.999"},  # Invalid version
                {"name": "typescript", "type": "npm"},  # No version required
            ],
            "expected": "Should PASS overall with warnings for invalid versions"
        }
    ]
    
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"Expected: {test_case['expected']}")
        print("-" * 40)
        
        # Create validator with test packages
        validator = RegistryValidator({
            "enabled": True,
            "packages": test_case["packages"]
        })
        
        print(f"Packages to check:")
        for pkg in validator.packages:
            version_info = f" @ {pkg.version}" if pkg.version else " (any version)"
            print(f"  • {pkg.name} ({pkg.registry_type}){version_info}")
        
        # Run validation
        result = await validator.validate(context)
        
        print(f"\nResult: {'✅ PASS' if result.passed else '❌ FAIL'}")
        print(f"Time: {result.execution_time:.2f}s")
        print(f"Packages found: {result.data['packages_found']}/{result.data['total_packages']}")
        
        if result.errors:
            print("❌ Errors:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        # Show detailed version checking results
        print("\n📦 Detailed Package Results:")
        for pkg_result in result.data['packages_checked']:
            status = "✅" if pkg_result.get('exists', False) else "❌"
            name = pkg_result['name']
            
            print(f"  {status} {name}")
            
            if pkg_result.get('exists'):
                # Show available versions/tags
                if 'available_versions' in pkg_result:
                    versions = pkg_result['available_versions']
                    print(f"    Available versions: {', '.join(versions[:5])}" + 
                          (f" ... (+{len(versions)-5} more)" if len(versions) > 5 else ""))
                elif 'available_tags' in pkg_result:
                    tags = pkg_result['available_tags']
                    print(f"    Available tags: {', '.join(tags[:5])}" + 
                          (f" ... (+{len(tags)-5} more)" if len(tags) > 5 else ""))
                
                if 'latest_version' in pkg_result:
                    print(f"    Latest version: {pkg_result['latest_version']}")
                
                # Version validation results
                if 'requested_version_exists' in pkg_result:
                    version_status = "✅ FOUND" if pkg_result['requested_version_exists'] else "❌ NOT FOUND"
                    print(f"    Requested version: {version_status}")
                elif 'requested_tag_exists' in pkg_result:
                    tag_status = "✅ FOUND" if pkg_result['requested_tag_exists'] else "❌ NOT FOUND"
                    print(f"    Requested tag: {tag_status}")
                else:
                    print(f"    Version check: ⏭️  SKIPPED (any version acceptable)")
            
            if pkg_result.get('error'):
                print(f"    Error: {pkg_result['error']}")
        
        print("\n" + "=" * 60)
    
    # Summary
    print(f"\n📋 Version Validation Summary:")
    print(f"• Registry validator checks EXACT versions when specified")
    print(f"• Generates warnings (not errors) for version mismatches")
    print(f"• Allows 'any version' when no version specified")
    print(f"• Supports version checking for NPM, PyPI, and Docker")
    print(f"• Version validation helps catch dependency conflicts early")


if __name__ == "__main__":
    asyncio.run(test_version_validation())