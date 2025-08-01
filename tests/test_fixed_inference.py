#!/usr/bin/env python3
"""Test the fixed package type inference logic."""

import asyncio
from mcp_validation.validators.registry import RegistryValidator
from mcp_validation.validators.base import ValidationContext


async def test_package_type_inference():
    """Test that package type inference works correctly."""
    
    print("🧪 Testing Fixed Package Type Inference\n")
    
    test_cases = [
        # Test case format: (input, expected_type, expected_name)
        ("express", "npm", "express"),
        ("lodash", "npm", "lodash"),
        ("fake-npm-package", "npm", "fake-npm-package"),
        ("@angular/core", "npm", "@angular/core"),
        ("typescript", "npm", "typescript"),
        
        ("pypi:requests", "pypi", "requests"),
        ("pypi:fake-python-package", "pypi", "fake-python-package"),
        ("some_package.py", "pypi", "some_package.py"),
        
        ("docker:nginx", "docker", "nginx"),
        ("docker:fake-image", "docker", "fake-image"),
        ("nginx/nginx", "docker", "nginx/nginx"),
        ("fake/image", "docker", "fake/image"),
        
        # Version formats
        ("express@4.18.0", "npm", "express"),
        ("pypi:requests@2.31.0", "pypi", "requests"),
        ("docker:nginx@latest", "docker", "nginx"),
    ]
    
    print("Package Type Inference Results:")
    print("-" * 60)
    
    for input_pkg, expected_type, expected_name in test_cases:
        # Create validator with single package
        validator = RegistryValidator({
            "enabled": True,
            "packages": [input_pkg]
        })
        
        if len(validator.packages) > 0:
            pkg = validator.packages[0]
            status = "✅" if pkg.registry_type == expected_type and pkg.name == expected_name else "❌"
            print(f"{status} '{input_pkg}' → {pkg.registry_type}:{pkg.name} (expected {expected_type}:{expected_name})")
        else:
            print(f"❌ '{input_pkg}' → Failed to parse")
    
    print(f"\n🧪 Testing Registry Validation with Non-Existent Packages")
    print("-" * 60)
    
    # Test with packages that definitely don't exist
    test_validator = RegistryValidator({
        "enabled": True,
        "packages": [
            "definitely-fake-npm-package-12345",  # Should be npm
            "pypi:fake-python-package-67890",     # Should be pypi
            "docker:fake-image-99999"             # Should be docker
        ]
    })
    
    print(f"Packages configured:")
    for pkg in test_validator.packages:
        print(f"  - {pkg.name} ({pkg.registry_type})")
    
    context = ValidationContext(
        process=None,
        server_info={},
        capabilities={},
        timeout=30.0
    )
    
    result = await test_validator.validate(context)
    
    print(f"\nValidation Result:")
    print(f"  Passed: {result.passed}")
    print(f"  Packages found: {result.data['packages_found']}")
    print(f"  Packages missing: {result.data['packages_missing']}")
    print(f"  Errors: {len(result.errors)}")
    
    if result.errors:
        print(f"\nErrors (should have 3 for non-existent packages):")
        for error in result.errors:
            print(f"  - {error}")
    
    # Expected behavior: Should FAIL with 3 errors
    expected_pass = False
    expected_errors = 3
    
    if result.passed == expected_pass and len(result.errors) == expected_errors:
        print(f"\n✅ Registry validation working correctly!")
        print(f"   - Fails as expected: {not result.passed}")
        print(f"   - Correct error count: {len(result.errors)}")
    else:
        print(f"\n❌ Registry validation has issues:")
        print(f"   - Expected to fail: {expected_pass}, actual: {result.passed}")
        print(f"   - Expected errors: {expected_errors}, actual: {len(result.errors)}")


if __name__ == "__main__":
    asyncio.run(test_package_type_inference())