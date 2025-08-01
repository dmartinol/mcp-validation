#!/usr/bin/env python3
"""Test registry validator with configuration file."""

import asyncio
import tempfile
import json
import os
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.config.settings import ConfigurationManager


async def test_with_config_file():
    """Test registry validator using configuration file."""
    
    # Create a temporary config file
    config_data = {
        "active_profile": "registry_test",
        "profiles": {
            "registry_test": {
                "description": "Test registry validation with config file",
                "validators": {
                    "registry": {
                        "enabled": True,
                        "required": False,
                        "parameters": {
                            "registries": {
                                "npm_url": "https://registry.npmjs.org",
                                "pypi_url": "https://pypi.org",
                                "docker_url": "https://registry-1.docker.io"
                            },
                            "packages": [
                                {"name": "lodash", "type": "npm", "version": "4.17.21"},
                                {"name": "flask", "type": "pypi"},
                                {"name": "alpine", "type": "docker", "version": "3.18"},
                                "typescript@5.0.0",
                                {"name": "definitely-fake-package-name", "type": "npm"}
                            ]
                        }
                    }
                },
                "global_timeout": 30.0,
                "continue_on_failure": True,
                "parallel_execution": False
            }
        }
    }
    
    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f, indent=2)
        config_file = f.name
    
    try:
        # Load configuration from file
        print(f"Loading configuration from: {config_file}")
        config_manager = ConfigurationManager(config_file)
        
        print(f"Active profile: {config_manager.active_profile}")
        print(f"Available profiles: {config_manager.list_profiles()}")
        
        # Create orchestrator
        orchestrator = MCPValidationOrchestrator(config_manager)
        
        # Get the active profile and show validator configuration
        profile = config_manager.get_active_profile()
        print(f"\nProfile: {profile.name}")
        print(f"Description: {profile.description}")
        print("Configured validators:")
        for validator_name, validator_config in profile.validators.items():
            print(f"  - {validator_name}: enabled={validator_config.enabled}, required={validator_config.required}")
        
        # Create registry validator with profile configuration
        registry_config = profile.validators["registry"]
        validator = orchestrator.registry.create_validator("registry", {
            'enabled': registry_config.enabled,
            'required': registry_config.required,
            **registry_config.parameters
        })
        
        if not validator:
            print("Failed to create registry validator")
            return
        
        print(f"\n=== Registry Validator Configuration ===")
        print(f"Validator name: {validator.name}")
        print(f"Packages to check: {len(validator.packages)}")
        for pkg in validator.packages:
            print(f"  - {pkg.name} ({pkg.registry_type})" + (f" @ {pkg.version}" if pkg.version else ""))
        
        # Execute validation
        from mcp_validation.validators.base import ValidationContext
        context = ValidationContext(
            process=None,
            server_info={},
            capabilities={},
            timeout=30.0
        )
        
        print(f"\n=== Executing Registry Validation ===")
        result = await validator.validate(context)
        
        print(f"Overall result: {'PASS' if result.passed else 'FAIL'}")
        print(f"Execution time: {result.execution_time:.2f}s")
        print(f"Total packages: {result.data['total_packages']}")
        print(f"Found: {result.data['packages_found']}")
        print(f"Missing: {result.data['packages_missing']}")
        print(f"Errors: {result.data['registry_errors']}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  ❌ {error}")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  ⚠️  {warning}")
        
        print("\nDetailed Package Results:")
        for pkg_result in result.data['packages_checked']:
            status = "✅" if pkg_result.get('exists', False) else "❌"
            name = pkg_result['name']
            registry = pkg_result.get('registry_url', 'unknown').replace('https://', '')
            
            print(f"  {status} {name} [{registry}]")
            
            if pkg_result.get('exists'):
                if 'latest_version' in pkg_result:
                    print(f"      Latest: {pkg_result['latest_version']}")
                if 'description' in pkg_result and pkg_result['description']:
                    desc = pkg_result['description'][:50] + "..." if len(pkg_result['description']) > 50 else pkg_result['description']
                    print(f"      Description: {desc}")
                # Check version/tag validation
                if 'requested_version_exists' in pkg_result:
                    version_status = "✅" if pkg_result['requested_version_exists'] else "❌"
                    print(f"      Requested version: {version_status}")
                elif 'requested_tag_exists' in pkg_result:
                    tag_status = "✅" if pkg_result['requested_tag_exists'] else "❌"
                    print(f"      Requested tag: {tag_status}")
            
            if pkg_result.get('error'):
                print(f"      Error: {pkg_result['error']}")
        
    finally:
        # Clean up temp file
        os.unlink(config_file)


if __name__ == "__main__":
    asyncio.run(test_with_config_file())