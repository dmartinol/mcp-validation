#!/usr/bin/env python3
"""Example usage of the Registry Validator for MCP validation."""

import asyncio
import json
from mcp_validation.validators.registry import RegistryValidator, PackageInfo
from mcp_validation.validators.base import ValidationContext


async def main():
    """Demonstrate registry validator usage."""
    
    # Example 1: Basic configuration with mixed package types
    print("=== Example 1: Basic Registry Validation ===")
    
    basic_config = {
        "enabled": True,
        "required": True,
        "packages": [
            # NPM packages
            "express@4.18.0",
            "typescript",
            
            # Python packages  
            {"name": "requests", "type": "pypi", "version": "2.28.0"},
            {"name": "django", "type": "pypi"},
            
            # Docker images
            {"name": "nginx", "type": "docker", "version": "latest"},
            {"name": "python", "type": "docker", "version": "3.11-slim"},
        ]
    }
    
    validator = RegistryValidator(basic_config)
    
    # Create a mock validation context (normally created by the validation framework)
    context = ValidationContext(
        process=None,  # Not needed for registry validation
        server_info={},
        capabilities={}
    )
    
    result = await validator.validate(context)
    
    print(f"Validation passed: {result.passed}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    print(f"Packages found: {result.data['packages_found']}/{result.data['total_packages']}")
    print(f"Execution time: {result.execution_time:.2f}s")
    
    print("\nDetailed results:")
    for pkg_result in result.data['packages_checked']:
        status = "✓" if pkg_result.get('exists', False) else "✗"
        name = pkg_result['name']
        registry = pkg_result.get('registry_url', 'unknown')
        print(f"  {status} {name} ({registry})")
        
        if pkg_result.get('error'):
            print(f"    Error: {pkg_result['error']}")
        elif pkg_result.get('exists'):
            if 'latest_version' in pkg_result:
                print(f"    Latest: {pkg_result['latest_version']}")
            if 'description' in pkg_result and pkg_result['description']:
                desc = pkg_result['description'][:60] + "..." if len(pkg_result['description']) > 60 else pkg_result['description']
                print(f"    Description: {desc}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Custom registry URLs
    print("=== Example 2: Custom Registry URLs ===")
    
    custom_config = {
        "enabled": True,
        "registries": {
            "npm_url": "https://registry.npmjs.org",
            "pypi_url": "https://pypi.org", 
            "docker_url": "https://registry-1.docker.io"
        },
        "packages": [
            {"name": "lodash", "type": "npm"},
            {"name": "flask", "type": "pypi"},
            {"name": "redis", "type": "docker"}
        ]
    }
    
    custom_validator = RegistryValidator(custom_config)
    custom_result = await custom_validator.validate(context)
    
    print(f"Custom registry validation passed: {custom_result.passed}")
    print(f"Packages checked: {len(custom_result.data['packages_checked'])}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Testing non-existent packages (should fail)
    print("=== Example 3: Testing Non-existent Packages ===")
    
    fail_config = {
        "enabled": True,
        "packages": [
            "definitely-not-a-real-package-name-12345",
            {"name": "also-not-real", "type": "pypi"},
            {"name": "definitely/not/real", "type": "docker"}
        ]
    }
    
    fail_validator = RegistryValidator(fail_config)
    fail_result = await fail_validator.validate(context)
    
    print(f"Should-fail validation passed: {fail_result.passed}")
    print(f"Errors found: {len(fail_result.errors)}")
    for error in fail_result.errors:
        print(f"  - {error}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 4: Show extensibility - adding a new registry type
    print("=== Example 4: Extensibility Example ===")
    print("The registry validator is designed to be extensible.")
    print("To add a new registry type (e.g., Maven, Cargo, etc.):")
    print("1. Create a new checker class implementing the RegistryChecker protocol")
    print("2. Add it to the RegistryValidator.checkers dictionary")
    print("3. Configure packages with the new registry type")
    print("\nExample new registry checker:")
    print("""
class MavenRegistryChecker:
    def __init__(self, registry_url="https://repo1.maven.org/maven2"):
        self.registry_url = registry_url
    
    async def check_package(self, package, session):
        # Implementation for Maven Central API
        # ...
        pass
""")


if __name__ == "__main__":
    asyncio.run(main())