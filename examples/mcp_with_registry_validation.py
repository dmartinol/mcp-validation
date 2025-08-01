#!/usr/bin/env python3
"""Example of using registry validation alongside MCP server validation."""

import asyncio
import tempfile
import json
import os
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.config.settings import ConfigurationManager


async def demonstrate_mcp_registry_validation():
    """Demonstrate registry validation in MCP context."""
    
    print("=== MCP Validation with Package Registry Checking ===\n")
    
    # Create configuration that includes both MCP and registry validation
    config_data = {
        "active_profile": "mcp_with_deps",
        "profiles": {
            "mcp_with_deps": {
                "description": "MCP validation with dependency verification",
                "validators": {
                    "protocol": {
                        "enabled": True,
                        "required": True,
                        "timeout": 10.0
                    },
                    "capabilities": {
                        "enabled": True,
                        "required": False
                    },
                    "registry": {
                        "enabled": True,
                        "required": False,
                        "parameters": {
                            "packages": [
                                # Common MCP server dependencies
                                {"name": "mcp", "type": "pypi"},
                                {"name": "@anthropic-ai/mcp-sdk", "type": "npm"},
                                {"name": "express", "type": "npm"},
                                {"name": "fastapi", "type": "pypi"},
                                {"name": "flask", "type": "pypi"},
                                {"name": "typescript", "type": "npm"},
                                {"name": "node", "type": "docker", "version": "18-alpine"},
                                {"name": "python", "type": "docker", "version": "3.11-slim"}
                            ]
                        }
                    }
                },
                "global_timeout": 30.0,
                "continue_on_failure": True,
                "parallel_execution": False
            },
            "registry_only": {
                "description": "Standalone registry validation for CI/CD",
                "validators": {
                    "registry": {
                        "enabled": True,
                        "required": True,
                        "parameters": {
                            "registries": {
                                "npm_url": "https://registry.npmjs.org",
                                "pypi_url": "https://pypi.org",
                                "docker_url": "https://registry-1.docker.io"
                            },
                            "packages": [
                                # Verify all dependencies before deployment
                                "lodash@4.17.21",
                                "requests@2.31.0",
                                "docker:nginx:1.25-alpine"
                            ]
                        }
                    }
                },
                "global_timeout": 60.0,
                "continue_on_failure": False
            }
        }
    }
    
    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f, indent=2)
        config_file = f.name
    
    try:
        # Load configuration
        config_manager = ConfigurationManager(config_file)
        orchestrator = MCPValidationOrchestrator(config_manager)
        
        print("Available validation profiles:")
        for profile_name in config_manager.list_profiles():
            profile = config_manager.profiles[profile_name]
            print(f"  • {profile_name}: {profile.description}")
        
        print(f"\nTesting with profile: {config_manager.active_profile}")
        
        # Show what the orchestrator would validate
        profile = config_manager.get_active_profile()
        print(f"\nValidation plan for '{profile.name}':")
        
        for validator_name, validator_config in profile.validators.items():
            if validator_config.enabled:
                status = "REQUIRED" if validator_config.required else "OPTIONAL"
                print(f"  📋 {validator_name.upper()} ({status})")
                
                if validator_name == "registry" and "packages" in validator_config.parameters:
                    packages = validator_config.parameters["packages"]
                    print(f"      Will verify {len(packages)} packages:")
                    for pkg in packages[:3]:  # Show first 3
                        if isinstance(pkg, dict):
                            name = pkg["name"]
                            pkg_type = pkg.get("type", "npm")
                            version = f"@{pkg['version']}" if pkg.get("version") else ""
                            print(f"        - {name}{version} ({pkg_type})")
                        else:
                            print(f"        - {pkg}")
                    if len(packages) > 3:
                        print(f"        ... and {len(packages) - 3} more")
        
        # Demonstrate registry-only validation (useful for CI/CD)
        print(f"\n=== Registry-Only Validation (CI/CD Use Case) ===")
        config_manager.set_active_profile("registry_only")
        
        registry_profile = config_manager.get_active_profile()
        registry_validator = orchestrator.registry.create_validator("registry", {
            'enabled': True,
            'required': True,
            **registry_profile.validators["registry"].parameters
        })
        
        # Execute registry validation
        from mcp_validation.validators.base import ValidationContext
        context = ValidationContext(
            process=None,
            server_info={},
            capabilities={},
            timeout=60.0
        )
        
        result = await registry_validator.validate(context)
        
        print(f"Registry validation: {'✅ PASS' if result.passed else '❌ FAIL'}")
        print(f"Dependencies verified: {result.data['packages_found']}/{result.data['total_packages']}")
        print(f"Execution time: {result.execution_time:.2f}s")
        
        if result.errors:
            print("\n❌ Dependency issues found:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("\n⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        print("\n📦 Package verification results:")
        for pkg_result in result.data['packages_checked']:
            status = "✅" if pkg_result.get('exists', False) else "❌"
            name = pkg_result['name']
            registry = pkg_result.get('registry_url', '').split('/')[-1] or 'unknown'
            print(f"  {status} {name} ({registry})")
        
        # Show practical usage scenarios
        print(f"\n=== Practical Usage Scenarios ===")
        print("1. MCP Server Development:")
        print("   mcp-validate --profile mcp_with_deps server.py")
        print("   → Validates MCP protocol + verifies dependencies exist")
        
        print("\n2. CI/CD Pipeline:")
        print("   mcp-validate --profile registry_only --config deps.json")
        print("   → Fast dependency verification before deployment")
        
        print("\n3. Security Auditing:")
        print("   mcp-validate --profile security_focused --include-registry")
        print("   → Security scan + dependency verification")
        
        print(f"\n✅ Registry validator is fully integrated and ready to use!")
        
    finally:
        # Clean up
        os.unlink(config_file)


if __name__ == "__main__":
    asyncio.run(demonstrate_mcp_registry_validation())