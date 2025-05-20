#!/usr/bin/env python3.13
"""
Tests for the MCP configuration utility functions.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

import mcp_installer.config as config


def test_find_mcp_config_file_exists():
    """Test finding mcp.yml when it exists in the current directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config file
        config_path = Path(tmpdir) / "mcp.yml"
        with open(config_path, 'w') as f:
            f.write("version: 1.0\nservers: []")
        
        # Mock current working directory
        with mock.patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
            result = config.find_mcp_config_file()
            assert result == config_path


def test_find_mcp_config_file_in_parent():
    """Test finding mcp.yml when it exists in a parent directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config file in the parent directory
        config_path = Path(tmpdir) / "mcp.yml"
        with open(config_path, 'w') as f:
            f.write("version: 1.0\nservers: []")
        
        # Create a subdirectory
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        
        # Mock current working directory to be the subdirectory
        with mock.patch('pathlib.Path.cwd', return_value=subdir):
            result = config.find_mcp_config_file()
            assert result == config_path


def test_find_mcp_config_file_not_found():
    """Test find_mcp_config_file when no config file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock current working directory
        with mock.patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
            # Mock Path.parents to return empty list to avoid searching system directories
            with mock.patch('pathlib.Path.parents', new_callable=mock.PropertyMock, return_value=[]):
                result = config.find_mcp_config_file()
                assert result is None


def test_load_mcp_config():
    """Test loading a valid MCP config file."""
    test_data = {
        "version": "1.0",
        "servers": ["server1", "server2"]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp:
        yaml.dump(test_data, temp)
    
    try:
        result = config.load_mcp_config(Path(temp.name))
        assert result == test_data
    finally:
        os.unlink(temp.name)


def test_load_mcp_config_invalid():
    """Test loading an invalid MCP config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp:
        temp.write("{invalid: yaml: content")
    
    try:
        with pytest.raises(ValueError):
            config.load_mcp_config(Path(temp.name))
    finally:
        os.unlink(temp.name)


def test_resolve_server_from_registry():
    """Test resolving a server from the registry."""
    # Mock the registry client
    mock_client = mock.MagicMock()
    mock_client.get_server.return_value = {
        "id": "428785c9-039e-47f6-9636-cbe289cc1990",
        "name": "io.github.azure/azure-mcp",
        "description": "This repository is for development of the Azure MCP Server.",
        "repository": {
            "url": "https://github.com/Azure/azure-mcp",
            "source": "github",
            "id": "967503541"
        },
        "version_detail": {
            "version": "0.0.1-seed",
            "release_date": "2025-05-15T04:53:50Z",
            "is_latest": True
        },
        "packages": [
            {
                "registry_name": "npm",
                "name": "Azure/azure-mcp"
            }
        ]
    }
    
    result = config.resolve_server_from_registry(mock_client, "428785c9-039e-47f6-9636-cbe289cc1990")
    
    mock_client.get_server.assert_called_once_with("428785c9-039e-47f6-9636-cbe289cc1990")
    assert result["id"] == "428785c9-039e-47f6-9636-cbe289cc1990"
    assert result["name"] == "io.github.azure/azure-mcp"


def test_resolve_server_from_registry_not_found():
    """Test resolving a server that doesn't exist in the registry."""
    # Mock the registry client to raise an exception
    mock_client = mock.MagicMock()
    mock_client.get_server.side_effect = Exception("Server not found")
    
    with pytest.raises(ValueError):
        config.resolve_server_from_registry(mock_client, "nonexistent-server")


@mock.patch('mcp_installer.config.convert_to_vscode_config')
@mock.patch('mcp_installer.config.install_server_in_vscode')
@mock.patch('mcp_installer.config.resolve_server_from_registry')
@mock.patch('click.prompt')
@mock.patch('click.secho')
def test_install_server_from_registry(mock_secho, mock_prompt, mock_resolve, mock_install, mock_convert):
    """Test installing a server from the registry."""
    # Setup mocks
    mock_registry_client = mock.MagicMock()
    mock_vscode_settings_path = mock.MagicMock()
    
    mock_server_data = {
        "id": "428785c9-039e-47f6-9636-cbe289cc1990",
        "name": "io.github.azure/azure-mcp",
        "description": "This repository is for development of the Azure MCP Server, bringing the power of Azure to your agents.",
        "repository": {
            "url": "https://github.com/Azure/azure-mcp",
            "source": "github",
            "id": "967503541"
        },
        "version_detail": {
            "version": "0.0.1-seed",
            "release_date": "2025-05-15T04:53:50Z",
            "is_latest": True
        },
        "package_canonical": "npm",
        "packages": [
            {
                "registry_name": "npm",
                "name": "test-image",
                "version": "",
                "runtime_hint": "npx",
                "runtime_arguments": [
                    {
                        "is_required": True,
                        "format": "string",
                        "value": "-y",
                        "type": "positional",
                        "value_hint": "-y"
                    }
                ],
                "environment_variables": [
                    {
                        "description": "Your API key",
                        "name": "TEST_VAR"
                    }
                ]
            }
        ]
    }
    mock_resolve.return_value = mock_server_data
    
    mock_vscode_config = {
        "name": "test-server",
        "command": "docker",
        "args": ["docker", "run", "test-image"],
        "env": {"TEST_VAR": ""}
    }
    mock_convert.return_value = mock_vscode_config
    
    mock_install_result = mock.MagicMock()
    mock_install_result.returncode = 0
    mock_install.return_value = mock_install_result
    
    # Test with interactive=True
    mock_prompt.return_value = "test-value"
    
    result = config.install_server_from_registry(
        "test-server", 
        mock_registry_client,
        mock_vscode_settings_path, 
        interactive=True
    )
    
    # Verify the expected calls
    mock_resolve.assert_called_once_with(mock_registry_client, "test-server")
    mock_convert.assert_called_once_with(mock_server_data)
    mock_prompt.assert_called_once()
    mock_install.assert_called_once()
    
    # Verify environment variable was set
    assert mock_vscode_config["env"]["TEST_VAR"] == "test-value"
    assert result is True


@mock.patch('mcp_installer.config.convert_to_vscode_config')
@mock.patch('mcp_installer.config.install_server_in_vscode')
@mock.patch('mcp_installer.config.resolve_server_from_registry')
@mock.patch('click.prompt')
@mock.patch('click.secho')
def test_install_server_from_registry_non_interactive(mock_secho, mock_prompt, mock_resolve, 
                                                     mock_install, mock_convert):
    """Test installing a server from the registry in non-interactive mode."""
    # Setup mocks
    mock_registry_client = mock.MagicMock()
    mock_vscode_settings_path = mock.MagicMock()
    
    mock_server_data = {
        "id": "0d96666a-ccb9-4c1b-959a-ea5def24cf14",
        "name": "io.github.21st-dev/magic-mcp",
        "description": "It's like v0 but in your Cursor/WindSurf/Cline. 21st dev Magic MCP server for working with your frontend like Magic",
        "repository": {
            "url": "https://github.com/21st-dev/magic-mcp",
            "source": "github",
            "id": "935450522"
        },
        "version_detail": {
            "version": "0.0.1-seed",
            "release_date": "2025-05-15T04:52:52Z",
            "is_latest": True
        },
        "package_canonical": "npm",
        "packages": [
            {
                "registry_name": "docker",
                "name": "test-image",
                "version": "0.0.46",
                "runtime_hint": "docker",
                "environment_variables": [
                    {
                        "description": "your-api-key",
                        "name": "TEST_VAR"
                    }
                ]
            }
        ]
    }
    mock_resolve.return_value = mock_server_data
    
    mock_vscode_config = {
        "name": "test-server",
        "command": "docker",
        "args": ["docker", "run", "test-image"],
        "env": {"TEST_VAR": ""}
    }
    mock_convert.return_value = mock_vscode_config
    
    mock_install_result = mock.MagicMock()
    mock_install_result.returncode = 0
    mock_install.return_value = mock_install_result
    
    # Test with interactive=False
    result = config.install_server_from_registry(
        "test-server", 
        mock_registry_client,
        mock_vscode_settings_path, 
        interactive=False
    )
    
    # Verify the expected calls
    mock_resolve.assert_called_once_with(mock_registry_client, "test-server")
    mock_convert.assert_called_once_with(mock_server_data)
    mock_prompt.assert_not_called()  # No prompts in non-interactive mode
    mock_install.assert_called_once()
    
    # Verify environment variable was not changed
    assert mock_vscode_config["env"]["TEST_VAR"] == ""
    assert result is True


@mock.patch('mcp_installer.config.convert_to_vscode_config')
@mock.patch('mcp_installer.config.install_server_in_vscode')
@mock.patch('mcp_installer.config.resolve_server_from_registry')
@mock.patch('click.secho')
def test_install_server_from_registry_installation_failure(mock_secho, mock_resolve, 
                                                         mock_install, mock_convert):
    """Test installing a server from the registry when installation fails."""
    # Setup mocks
    mock_registry_client = mock.MagicMock()
    mock_vscode_settings_path = mock.MagicMock()
    
    mock_server_data = {
        "id": "428785c9-039e-47f6-9636-cbe289cc1990",
        "name": "io.github.azure/azure-mcp",
        "description": "This repository is for development of the Azure MCP Server, bringing the power of Azure to your agents.",
        "repository": {
            "url": "https://github.com/Azure/azure-mcp",
            "source": "github",
            "id": "967503541"
        },
        "version_detail": {
            "version": "0.0.1-seed",
            "release_date": "2025-05-15T04:53:50Z",
            "is_latest": True
        },
        "package_canonical": "npm",
        "packages": [
            {
                "registry_name": "npm",
                "name": "test-image",
                "version": "",
                "runtime_hint": "npx"
            }
        ]
    }
    mock_resolve.return_value = mock_server_data
    
    mock_vscode_config = {
        "name": "test-server",
        "command": "docker",
        "args": ["docker", "run", "test-image"]
    }
    mock_convert.return_value = mock_vscode_config
    
    # Simulate installation failure
    mock_install_result = mock.MagicMock()
    mock_install_result.returncode = 1
    mock_install_result.stderr = "Installation failed"
    mock_install.return_value = mock_install_result
    
    result = config.install_server_from_registry(
        "test-server", 
        mock_registry_client,
        mock_vscode_settings_path
    )
    
    # Verify the result is False
    assert result is False
