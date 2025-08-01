#!/usr/bin/env python3
"""Demonstrate fail-fast validation benefits for CI/CD and development."""

import asyncio
import time
from mcp_validation.core.validator import MCPValidationOrchestrator
from mcp_validation.config.settings import ConfigurationManager
from mcp_validation.validators.base import ValidationContext


async def demonstrate_fail_fast_benefits():
    """Show the benefits of fail-fast dependency validation."""
    
    print("🚀 Fail-Fast Registry Validation Benefits\n")
    print("="*60)
    
    # Scenario 1: Traditional validation order (slow failure)
    print("\n📊 SCENARIO 1: Traditional Validation Order")
    print("Order: Protocol → Capabilities → Registry → Security")
    print("Problem: Dependency issues discovered late, wasting time\n")
    
    await simulate_traditional_validation()
    
    print("\n" + "="*60)
    
    # Scenario 2: Fail-fast validation order (fast failure)
    print("\n⚡ SCENARIO 2: Fail-Fast Validation Order")
    print("Order: Registry → Protocol → Capabilities → Security") 
    print("Benefit: Dependency issues discovered immediately\n")
    
    await simulate_fail_fast_validation()
    
    print("\n" + "="*60)
    
    # Show practical CI/CD configuration
    print("\n🔧 PRACTICAL CI/CD CONFIGURATION")
    print_ci_cd_examples()
    
    print("\n" + "="*60)
    
    # Show development workflow
    print("\n💻 DEVELOPMENT WORKFLOW")
    print_development_workflow()


async def simulate_traditional_validation():
    """Simulate traditional validation order (slow to fail)."""
    
    print("Simulating traditional validation with missing dependencies...")
    
    start_time = time.time()
    
    # Simulate running protocol validation first (would take time)
    print("  1. 🔄 Running Protocol validation... (would take 5-10s)")
    await asyncio.sleep(0.1)  # Simulate work
    print("     ✅ Protocol validation passed")
    
    # Simulate capabilities validation
    print("  2. 🔄 Running Capabilities validation... (would take 3-5s)")  
    await asyncio.sleep(0.1)  # Simulate work
    print("     ✅ Capabilities validation passed")
    
    # Registry validation last - finds the real problem
    print("  3. 🔄 Running Registry validation...")
    
    # Actually run registry validation with missing packages
    config_manager = ConfigurationManager()
    orchestrator = MCPValidationOrchestrator(config_manager)
    
    registry_validator = orchestrator.registry.create_validator("registry", {
        "packages": [
            {"name": "missing-package-12345", "type": "npm"},
            {"name": "another-missing-package", "type": "pypi"}
        ]
    })
    
    context = ValidationContext(process=None, server_info={}, capabilities={}, timeout=30.0)
    result = await registry_validator.validate(context)
    
    elapsed = time.time() - start_time
    
    print(f"     ❌ Registry validation FAILED")
    print(f"     Missing packages: {result.data['packages_missing']}")
    for error in result.errors[:2]:
        print(f"       • {error}")
    
    print(f"\n💸 WASTED TIME: {elapsed:.1f}s + (8-15s in real validation)")
    print("   Problem: Dependencies checked last, after expensive validations")


async def simulate_fail_fast_validation():
    """Simulate fail-fast validation order (fast to fail)."""
    
    print("Simulating fail-fast validation with missing dependencies...")
    
    start_time = time.time()
    
    # Registry validation first - finds problems immediately
    print("  1. 🔄 Running Registry validation...")
    
    config_manager = ConfigurationManager()
    orchestrator = MCPValidationOrchestrator(config_manager)
    
    registry_validator = orchestrator.registry.create_validator("registry", {
        "packages": [
            {"name": "missing-package-12345", "type": "npm"},
            {"name": "another-missing-package", "type": "pypi"}
        ]
    })
    
    context = ValidationContext(process=None, server_info={}, capabilities={}, timeout=30.0)
    result = await registry_validator.validate(context)
    
    elapsed = time.time() - start_time
    
    print(f"     ❌ Registry validation FAILED")
    print(f"     Missing packages: {result.data['packages_missing']}")
    for error in result.errors[:2]:
        print(f"       • {error}")
    
    print("  🛑 STOPPING: Required dependency validation failed")
    print("     Skipping expensive Protocol, Capabilities, Security validations")
    
    print(f"\n⚡ TIME SAVED: {elapsed:.1f}s vs 8-15s")
    print("   Benefit: Issues found in seconds, not minutes")


def print_ci_cd_examples():
    """Show practical CI/CD pipeline configurations."""
    
    print("Example GitHub Actions workflow:")
    print("""
# .github/workflows/mcp-validation.yml
name: MCP Validation
on: [push, pull_request]

jobs:
  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Fast Dependency Check
        run: |
          mcp-validate --profile fail_fast \\
                      --config .mcp-validation.json \\
                      ./server.py
        # Fails fast if dependencies missing
        # Saves CI minutes and gives immediate feedback
  
  full-validation:
    needs: dependency-check
    runs-on: ubuntu-latest
    steps:
      - name: Comprehensive Validation
        run: |
          mcp-validate --profile comprehensive \\
                      ./server.py
""")
    
    print("\nDocker build optimization:")
    print("""
# Dockerfile
FROM node:18-alpine

# Check dependencies first (fail fast)
COPY package.json .
RUN mcp-validate --profile registry_only --config package.json

# Only proceed if dependencies exist
COPY . .
RUN npm install
""")


def print_development_workflow():
    """Show development workflow benefits."""
    
    print("Development workflow with fail-fast validation:")
    print("""
1. 📝 Write MCP server code
2. ⚡ Quick dependency check:
   $ mcp-validate --profile fail_fast ./server.py
   
   ❌ FAIL: Package 'tyepscript' not found (typo!)
   ⏱️  Time: 2 seconds
   
3. 🔧 Fix dependencies
4. ⚡ Re-check:
   $ mcp-validate --profile fail_fast ./server.py
   
   ✅ PASS: All dependencies found
   ⏱️  Time: 3 seconds
   
5. 🚀 Full validation:
   $ mcp-validate --profile comprehensive ./server.py
   
   ✅ PASS: Complete MCP validation
   ⏱️  Time: 15 seconds

BENEFIT: Catch dependency issues in 2-3 seconds instead of 15+ seconds
""")
    
    print("Pre-commit hook example:")
    print("""
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mcp-deps-check
        name: MCP Dependencies Check
        entry: mcp-validate --profile fail_fast
        language: system
        pass_filenames: false
        # Fails commit if dependencies missing
        # Developer gets immediate feedback
""")


if __name__ == "__main__":
    asyncio.run(demonstrate_fail_fast_benefits())