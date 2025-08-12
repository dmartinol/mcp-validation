"""Tests for console reporting of container validators."""

import pytest
from io import StringIO
import sys
from unittest.mock import patch

from mcp_validation.reporting.console import ConsoleReporter
from mcp_validation.validators.base import ValidatorResult


class TestConsoleReporting:
    """Test console reporting for container validators."""

    def test_container_ubi_warning_shown_in_non_verbose(self):
        """Test that container UBI warnings are shown even in non-verbose mode."""
        result = ValidatorResult(
            validator_name="container_ubi",
            passed=True,
            errors=[],
            warnings=["Container image 'ubuntu:latest' is not based on a UBI"],
            data={
                "image_name": "ubuntu:latest",
                "base_image": "ubuntu",
                "is_ubi_based": False,
                "rhel_version": None
            },
            execution_time=2.5
        )
        
        # Capture console output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            reporter = ConsoleReporter(verbose=False)
            reporter._report_validator_result(result)
        
        output = captured_output.getvalue()
        
        # Should show the warning even in non-verbose mode
        assert "⚠️  Container image 'ubuntu:latest' is not based on a UBI" in output
        assert "✅ Container_Ubi: Passed" in output
        assert "📦 Base Image: ubuntu (Non-UBI)" in output

    def test_container_version_warning_shown_in_non_verbose(self):
        """Test that container version warnings are shown even in non-verbose mode."""
        result = ValidatorResult(
            validator_name="container_version",
            passed=True,
            errors=[],
            warnings=["Image tag 'v1.0' may not be the latest available version"],
            data={
                "image_name": "hashicorp/terraform-mcp-server:v1.0",
                "image_tag": "v1.0",
                "using_latest": False
            },
            execution_time=1.5
        )
        
        # Capture console output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            reporter = ConsoleReporter(verbose=False)
            reporter._report_validator_result(result)
        
        output = captured_output.getvalue()
        
        # Should show the warning even in non-verbose mode
        assert "⚠️  Image tag 'v1.0' may not be the latest available version" in output
        assert "✅ Container_Version: Passed" in output
        assert "📌 Version: v1.0 (Specific tag)" in output

    def test_non_container_warnings_not_shown_in_non_verbose(self):
        """Test that non-container validator warnings are NOT shown in non-verbose mode."""
        result = ValidatorResult(
            validator_name="protocol",
            passed=True,
            errors=[],
            warnings=["Some protocol warning"],
            data={},
            execution_time=1.0
        )
        
        # Capture console output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            reporter = ConsoleReporter(verbose=False)
            reporter._report_validator_result(result)
        
        output = captured_output.getvalue()
        
        # Should NOT show the warning in non-verbose mode
        assert "⚠️  Some protocol warning" not in output
        assert "✅ Protocol: Passed" in output

    def test_container_ubi_data_reporting(self):
        """Test specific data reporting for UBI validator."""
        result = ValidatorResult(
            validator_name="container_ubi",
            passed=True,
            errors=[],
            warnings=[],
            data={
                "image_name": "registry.redhat.io/ubi9/ubi:latest",
                "base_image": "ubi9/ubi",
                "is_ubi_based": True,
                "rhel_version": "9"
            },
            execution_time=2.5
        )
        
        # Capture console output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            reporter = ConsoleReporter(verbose=False)
            reporter._report_validator_result(result)
        
        output = captured_output.getvalue()
        
        assert "🐳 Container Image: registry.redhat.io/ubi9/ubi:latest" in output
        assert "✅ UBI Base: ubi9/ubi (RHEL 9)" in output

    def test_container_version_data_reporting(self):
        """Test specific data reporting for version validator."""
        result = ValidatorResult(
            validator_name="container_version",
            passed=True,
            errors=[],
            warnings=[],
            data={
                "image_name": "hashicorp/terraform-mcp-server:latest",
                "image_tag": "latest",
                "using_latest": True
            },
            execution_time=1.5
        )
        
        # Capture console output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            reporter = ConsoleReporter(verbose=False)
            reporter._report_validator_result(result)
        
        output = captured_output.getvalue()
        
        assert "🐳 Container Image: hashicorp/terraform-mcp-server:latest" in output
        assert "✅ Version: latest (Latest)" in output