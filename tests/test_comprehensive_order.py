#!/usr/bin/env python3
"""Test that comprehensive profile runs registry validation first."""

from mcp_validation.config.settings import ConfigurationManager


def test_comprehensive_validation_order():
    """Test that comprehensive profile has registry validation first."""
    
    config_manager = ConfigurationManager()
    comprehensive_profile = config_manager.profiles["comprehensive"]
    
    print("🔍 Comprehensive Profile Validation Order")
    print("=" * 50)
    
    print(f"Profile: {comprehensive_profile.name}")
    print(f"Description: {comprehensive_profile.description}")
    print(f"Continue on failure: {comprehensive_profile.continue_on_failure}")
    
    print("\nValidator execution order:")
    validators_list = list(comprehensive_profile.validators.items())
    
    for i, (validator_name, validator_config) in enumerate(validators_list, 1):
        status = "REQUIRED" if validator_config.required else "OPTIONAL"
        enabled = "ENABLED" if validator_config.enabled else "DISABLED"
        
        icon = "🔧" if validator_name == "registry" else "📋"
        print(f"  {i}. {icon} {validator_name.upper()} ({status}, {enabled})")
        
        # Show registry details
        if validator_name == "registry" and hasattr(validator_config, 'parameters'):
            packages = validator_config.parameters.get("packages", [])
            print(f"      📦 Will verify {len(packages)} packages:")
            for pkg in packages:
                if isinstance(pkg, dict):
                    name = pkg["name"]
                    pkg_type = pkg["type"]
                    print(f"         • {name} ({pkg_type})")
                else:
                    print(f"         • {pkg}")
    
    # Verify registry is first
    first_validator = validators_list[0][0]
    if first_validator == "registry":
        print(f"\n✅ SUCCESS: Registry validation runs FIRST")
        print("   → Dependencies checked before expensive MCP validations")
        print("   → Fail-fast behavior enabled")
    else:
        print(f"\n❌ ISSUE: Registry validation is not first (position: {[name for name, _ in validators_list].index('registry') + 1})")
        print("   → Dependencies checked late, slower failure detection")
    
    print(f"\n📊 Validation Strategy Summary:")
    print(f"   • Registry validation: {'FIRST' if first_validator == 'registry' else 'LATER'}")
    print(f"   • Fail-fast on registry: {'YES' if not comprehensive_profile.continue_on_failure else 'NO'}")
    print(f"   • Total validators: {len(validators_list)}")
    print(f"   • Required validators: {sum(1 for _, config in validators_list if config.required)}")


if __name__ == "__main__":
    test_comprehensive_validation_order()