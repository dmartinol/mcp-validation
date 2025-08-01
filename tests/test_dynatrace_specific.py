#!/usr/bin/env python3
"""Test the specific Dynatrace command parsing."""

import re


def extract_npm_from_npx(command: str):
    """Extract npm package from npx command."""
    
    print(f"🔍 Analyzing: {command}")
    
    # Updated pattern to handle scoped packages and flags better
    patterns = [
        # npx with flags and scoped packages: npx -y @scope/package@version
        r'npx\s+(?:-[gy]\s+|--[^\s]+\s+)*(@?[^@\s]+)(?:@([^\s]+))?',
        
        # Alternative pattern for scoped packages
        r'npx\s+[^@]*(@[^/]+/[^@\s]+)(?:@([^\s]+))?',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"  Pattern {i}: {pattern}")
        matches = re.findall(pattern, command)
        print(f"  Matches: {matches}")
        
        for match in matches:
            if isinstance(match, tuple):
                package_name, version = match
            else:
                package_name, version = match, None
                
            if package_name and not package_name.startswith('-'):
                print(f"  ✅ Found: {package_name}" + (f"@{version}" if version else ""))
                return package_name, version
    
    print(f"  ❌ No package found")
    return None, None


def test_dynatrace_commands():
    """Test various Dynatrace command formats."""
    
    print("🧪 Testing Dynatrace Command Parsing\n")
    print("=" * 60)
    
    test_commands = [
        "npx @dynatrace-oss/dynatrace-mcp-server",
        "npx -y @dynatrace-oss/dynatrace-mcp-server",
        "npx -y @dynatrace-oss/dynatrace-mcp-serveoor@0.4.02222",
        "npx --yes @dynatrace-oss/dynatrace-mcp-server@latest",
        "npx -g @dynatrace-oss/dynatrace-mcp-server",
        "npx lodash@4.17.21",
        "npx express",
    ]
    
    for command in test_commands:
        print(f"\n{'='*60}")
        package, version = extract_npm_from_npx(command)
        
        if package:
            print(f"📦 RESULT: Package '{package}'" + (f" version '{version}'" if version else " (any version)"))
            
            # Show what registry validation would do
            if "serveoor" in package:
                print(f"🚨 This would FAIL registry validation (typo in package name)")
            elif version and "02222" in version:
                print(f"⚠️  This would WARN in registry validation (weird version)")
            else:
                print(f"✅ This would likely PASS registry validation")
        else:
            print(f"❌ RESULT: No package extracted")


if __name__ == "__main__":
    test_dynatrace_commands()