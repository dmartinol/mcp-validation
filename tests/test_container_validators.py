"""Tests for container image validators."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_validation.validators.container import ContainerUBIValidator, ContainerVersionValidator
from mcp_validation.validators.base import ValidationContext


@pytest.fixture
def mock_context():
    """Create a mock validation context."""
    context = MagicMock(spec=ValidationContext)
    context.command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
    context.timeout = 30.0
    return context


@pytest.fixture
def mock_context_podman():
    """Create a mock validation context for podman."""
    context = MagicMock(spec=ValidationContext)
    context.command_args = ["podman", "run", "-i", "--rm", "registry.redhat.io/ubi9/ubi:latest"]
    context.timeout = 30.0
    return context


@pytest.fixture
def mock_context_non_container():
    """Create a mock validation context for non-container command."""
    context = MagicMock(spec=ValidationContext)
    context.command_args = ["python", "server.py"]
    context.timeout = 30.0
    return context


class TestContainerUBIValidator:
    """Test cases for ContainerUBIValidator."""

    def test_validator_properties(self):
        """Test validator basic properties."""
        validator = ContainerUBIValidator()
        assert validator.name == "container_ubi"
        assert "UBI" in validator.description
        assert "runtime_exists" in validator.dependencies

    def test_is_applicable_docker(self, mock_context):
        """Test validator is applicable for docker commands."""
        validator = ContainerUBIValidator({"enabled": True})
        assert validator.is_applicable(mock_context)

    def test_is_applicable_podman(self, mock_context_podman):
        """Test validator is applicable for podman commands."""
        validator = ContainerUBIValidator({"enabled": True})
        assert validator.is_applicable(mock_context_podman)

    def test_is_applicable_non_container(self, mock_context_non_container):
        """Test validator is not applicable for non-container commands."""
        validator = ContainerUBIValidator({"enabled": True})
        assert not validator.is_applicable(mock_context_non_container)

    def test_is_applicable_disabled(self, mock_context):
        """Test validator is not applicable when disabled."""
        validator = ContainerUBIValidator({"enabled": False})
        assert not validator.is_applicable(mock_context)

    def test_extract_image_name_docker(self):
        """Test image name extraction from docker command."""
        validator = ContainerUBIValidator()
        command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
        image_name = validator._extract_image_name(command_args)
        assert image_name == "hashicorp/terraform-mcp-server"

    def test_extract_image_name_podman_with_options(self):
        """Test image name extraction from podman command with options."""
        validator = ContainerUBIValidator()
        command_args = ["podman", "run", "-v", "/tmp:/tmp", "-e", "VAR=value", "registry.redhat.io/ubi9/ubi:latest", "sh"]
        image_name = validator._extract_image_name(command_args)
        assert image_name == "registry.redhat.io/ubi9/ubi:latest"

    def test_extract_image_name_invalid_command(self):
        """Test image name extraction from invalid command."""
        validator = ContainerUBIValidator()
        command_args = ["python", "server.py"]
        image_name = validator._extract_image_name(command_args)
        assert image_name is None

    @pytest.mark.asyncio
    async def test_validate_no_image_name(self, mock_context_non_container):
        """Test validation when image name cannot be extracted."""
        validator = ContainerUBIValidator({"enabled": True})
        result = await validator.validate(mock_context_non_container)
        
        assert not result.passed
        assert len(result.errors) > 0
        assert "Could not extract container image name" in result.errors[0]

    @pytest.mark.asyncio
    @patch('mcp_validation.validators.container.asyncio.create_subprocess_exec')
    async def test_validate_non_ubi_image_warn_only(self, mock_subprocess, mock_context):
        """Test validation of a non-UBI image with warn_only=True (should pass with warning)."""
        # Mock successful image inspection for non-UBI image
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b'[{"Config": {"Labels": {"name": "ubuntu", "description": "Ubuntu base image"}, "Env": []}}]',
            b''
        )
        mock_subprocess.return_value = mock_process

        validator = ContainerUBIValidator({"enabled": True, "warn_only_for_non_ubi": True})
        result = await validator.validate(mock_context)
        
        assert result.passed  # Should pass but with warning
        assert not result.data["is_ubi_based"]
        assert len(result.warnings) > 0
        assert len(result.errors) == 0
        assert "not based on a UBI" in result.warnings[0]
        assert "Consider using a UBI-based image" in result.warnings[0]

    @pytest.mark.asyncio
    @patch('mcp_validation.validators.container.asyncio.create_subprocess_exec')
    async def test_validate_non_ubi_image_strict_mode(self, mock_subprocess, mock_context):
        """Test validation of a non-UBI image with warn_only=False (should fail)."""
        # Mock successful image inspection for non-UBI image
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b'[{"Config": {"Labels": {"name": "ubuntu", "description": "Ubuntu base image"}, "Env": []}}]',
            b''
        )
        mock_subprocess.return_value = mock_process

        validator = ContainerUBIValidator({"enabled": True, "warn_only_for_non_ubi": False})
        result = await validator.validate(mock_context)
        
        assert not result.passed  # Should fail
        assert not result.data["is_ubi_based"]
        assert len(result.errors) > 0
        assert "not based on a UBI" in result.errors[0]
        assert "Consider using a UBI-based image" in result.errors[0]

    @pytest.mark.asyncio
    @patch('mcp_validation.validators.container.asyncio.create_subprocess_exec')
    async def test_validate_ubi_compliant_image(self, mock_subprocess, mock_context):
        """Test validation of a UBI-compliant image."""
        # Mock successful image inspection
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b'[{"Config": {"Labels": {"name": "ubi9/ubi", "com.redhat.component": "ubi9-container"}, "Env": ["REDHAT_SUPPORT_PRODUCT=ubi"]}}]',
            b''
        )
        mock_subprocess.return_value = mock_process

        validator = ContainerUBIValidator({"enabled": True})
        result = await validator.validate(mock_context)
        
        assert result.passed
        assert result.data["is_ubi_based"]
        assert result.data["rhel_version"] == "9"

    def test_check_ubi_compliance_ubi9(self):
        """Test UBI compliance checking for UBI 9 image."""
        validator = ContainerUBIValidator()
        inspection_result = {
            "image_inspected": True,
            "image_labels": {
                "name": "ubi9/ubi",
                "com.redhat.component": "ubi9-container",
                "summary": "Red Hat Universal Base Image 9"
            },
            "image_env": ["REDHAT_SUPPORT_PRODUCT=ubi"]
        }
        
        result = validator._check_ubi_compliance(inspection_result)
        
        assert result["is_ubi_based"]
        assert result["rhel_version"] == "9"
        assert result["base_image"] == "ubi9/ubi"

    def test_check_ubi_compliance_non_ubi(self):
        """Test UBI compliance checking for non-UBI image."""
        validator = ContainerUBIValidator()
        inspection_result = {
            "image_inspected": True,
            "image_labels": {
                "name": "ubuntu",
                "description": "Ubuntu base image"
            },
            "image_env": []
        }
        
        result = validator._check_ubi_compliance(inspection_result)
        
        assert not result["is_ubi_based"]
        assert result["rhel_version"] is None
        assert result["base_image"] == "ubuntu"


class TestContainerVersionValidator:
    """Test cases for ContainerVersionValidator."""

    def test_validator_properties(self):
        """Test validator basic properties."""
        validator = ContainerVersionValidator()
        assert validator.name == "container_version"
        assert "latest" in validator.description
        assert "runtime_exists" in validator.dependencies

    def test_is_applicable_docker(self, mock_context):
        """Test validator is applicable for docker commands."""
        validator = ContainerVersionValidator({"enabled": True})
        assert validator.is_applicable(mock_context)

    def test_is_applicable_non_container(self, mock_context_non_container):
        """Test validator is not applicable for non-container commands."""
        validator = ContainerVersionValidator({"enabled": True})
        assert not validator.is_applicable(mock_context_non_container)

    def test_parse_image_name_with_tag(self):
        """Test parsing image name with tag."""
        validator = ContainerVersionValidator()
        result = validator._parse_image_name("hashicorp/terraform-mcp-server:v1.0")
        
        assert result["image_repository"] == "hashicorp/terraform-mcp-server"
        assert result["image_tag"] == "v1.0"
        assert result["image_registry"] is None

    def test_parse_image_name_with_registry(self):
        """Test parsing image name with registry."""
        validator = ContainerVersionValidator()
        result = validator._parse_image_name("registry.redhat.io/ubi9/ubi:latest")
        
        assert result["image_registry"] == "registry.redhat.io"
        assert result["image_repository"] == "ubi9/ubi"
        assert result["image_tag"] == "latest"

    def test_parse_image_name_latest_default(self):
        """Test parsing image name without tag defaults to latest."""
        validator = ContainerVersionValidator()
        result = validator._parse_image_name("hashicorp/terraform-mcp-server")
        
        assert result["image_repository"] == "hashicorp/terraform-mcp-server"
        assert result["image_tag"] == "latest"

    @pytest.mark.asyncio
    async def test_validate_latest_tag(self, mock_context):
        """Test validation of image using latest tag."""
        # Update context to use latest tag
        mock_context.command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server:latest"]
        
        validator = ContainerVersionValidator({"enabled": True})
        result = await validator.validate(mock_context)
        
        assert result.passed
        assert result.data["using_latest"]
        assert result.data["image_tag"] == "latest"

    @pytest.mark.asyncio
    async def test_validate_specific_tag(self, mock_context):
        """Test validation of image using specific tag."""
        # Update context to use specific tag
        mock_context.command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server:v1.0"]
        
        validator = ContainerVersionValidator({"enabled": True})
        result = await validator.validate(mock_context)
        
        assert result.passed  # Should pass but may have warnings
        assert not result.data["using_latest"]
        assert result.data["image_tag"] == "v1.0"

    @pytest.mark.asyncio
    async def test_validate_no_image_name(self, mock_context_non_container):
        """Test validation when image name cannot be extracted."""
        validator = ContainerVersionValidator({"enabled": True})
        result = await validator.validate(mock_context_non_container)
        
        assert not result.passed
        assert len(result.errors) > 0
        assert "Could not extract container image name" in result.errors[0]


class TestContainerDetection:
    """Test cases for container runtime detection in CLI."""

    def test_detect_docker_run(self):
        """Test detection of docker run command."""
        from mcp_validation.cli.main import is_container_runtime_command
        
        command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
        assert is_container_runtime_command(command_args)

    def test_detect_podman_run(self):
        """Test detection of podman run command."""
        from mcp_validation.cli.main import is_container_runtime_command
        
        command_args = ["podman", "run", "-i", "--rm", "registry.redhat.io/ubi9/ubi:latest"]
        assert is_container_runtime_command(command_args)

    def test_detect_non_container_command(self):
        """Test non-container commands are not detected."""
        from mcp_validation.cli.main import is_container_runtime_command
        
        command_args = ["python", "server.py"]
        assert not is_container_runtime_command(command_args)

    def test_detect_docker_without_run(self):
        """Test docker commands without run are not detected."""
        from mcp_validation.cli.main import is_container_runtime_command
        
        command_args = ["docker", "ps"]
        assert not is_container_runtime_command(command_args)

    def test_detect_short_command(self):
        """Test short commands are not detected."""
        from mcp_validation.cli.main import is_container_runtime_command
        
        command_args = ["docker"]
        assert not is_container_runtime_command(command_args)

    def test_detect_runtime_command_docker(self):
        """Test runtime command detection for docker."""
        from mcp_validation.cli.main import detect_runtime_command
        
        command_args = ["docker", "run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
        runtime = detect_runtime_command(command_args)
        assert runtime == "docker"

    def test_detect_runtime_command_podman(self):
        """Test runtime command detection for podman.""" 
        from mcp_validation.cli.main import detect_runtime_command
        
        command_args = ["podman", "run", "-i", "--rm", "registry.redhat.io/ubi9/ubi:latest"]
        runtime = detect_runtime_command(command_args)
        assert runtime == "podman"