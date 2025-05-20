#!/usr/bin/env python3.13
"""
Integration tests for the MCP config CLI commands.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from mcp_installer.main import cli
from mcp_installer.config import find_mcp_config_file, load_mcp_config


@pytest.fixture
def mock_registry_client():
    """Create a mock registry client that returns predefined server data."""
    with mock.patch('mcp_installer.registry.MCPRegistryClient') as mock_client_class:
        mock_client = mock_client_class.return_value
        
        # Mock the get_server method
        def mock_get_server(server_id):
            mock_servers = {
                "server1": {
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
                            "name": "docker-image1",
                            "version": "",
                            "runtime_hint": "npx",
                            "runtime_arguments": [
                                {
                                    "is_required": True,
                                    "format": "string",
                                    "value": "-y",
                                    "default": "-y",
                                    "type": "positional",
                                    "value_hint": "-y"
                                },
                                {
                                    "is_required": True,
                                    "format": "string",
                                    "value": "@azure/mcp@latest",
                                    "default": "@azure/mcp@latest",
                                    "type": "positional",
                                    "value_hint": "@azure/mcp@latest"
                                }
                            ],
                            "environment_variables": [
                                {
                                    "description": "Your API key for Azure",
                                    "name": "ENV_VAR1"
                                }
                            ]
                        }
                    ]
                },
                "server2": {
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
                            "name": "docker-image2",
                            "version": "0.0.46",
                            "runtime_hint": "docker",
                            "runtime_arguments": [
                                {
                                    "is_required": True,
                                    "format": "string",
                                    "value": "run",
                                    "default": "run",
                                    "type": "positional",
                                    "value_hint": "run"
                                },
                                {
                                    "is_required": True,
                                    "format": "string",
                                    "value": "-i",
                                    "default": "-i",
                                    "type": "positional",
                                    "value_hint": "-i"
                                }
                            ]
                        }
                    ]
                }
            }
            
            if server_id not in mock_servers:
                raise ValueError(f"Server not found: {server_id}")
                
            return mock_servers[server_id]
        
        mock_client.get_server.side_effect = mock_get_server
        
        yield mock_client


@pytest.fixture
def mock_vscode_settings():
    """Create a temporary VSCode settings file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"
        
        # Create a settings file with some servers
        settings = {
            "mcp": {
                "servers": {
                    "server1": {
                        "command": "docker",
                        "args": ["docker", "run", "docker-image1"],
                        "env": {"ENV_VAR1": "value1"}
                    }
                }
            }
        }
        
        with open(settings_file, 'w') as f:
            json.dump(settings, f)
            
        # Mock the find_settings_file function
        with mock.patch('mcp_installer.main.find_settings_file', return_value=settings_file):
            yield settings_file


@pytest.fixture
def mock_mcp_config_file():
    """Create a temporary MCP config file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "mcp.yml"
        
        # Create a config file with some servers
        config = {
            "version": "1.0",
            "servers": ["server1", "server2"]
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
            
        # Mock the find_mcp_config_file function to return our temp file
        with mock.patch('mcp_installer.config.find_mcp_config_file', return_value=config_file):
            # Also patch cwd to return the temp directory
            with mock.patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                yield config_file


def test_config_install_command(mock_registry_client, mock_vscode_settings, mock_mcp_config_file):
    """Test the 'config install' command."""
    # Mock the install_server_from_registry function directly since that's what main.py calls
    with mock.patch('mcp_installer.config.install_server_from_registry') as mock_install_from_registry:
        # Setup the mock to return success
        mock_install_from_registry.return_value = True
        
        # Also mock load_mcp_config to ensure it returns the expected format
        with mock.patch('mcp_installer.config.load_mcp_config') as mock_load_config:
            mock_load_config.return_value = {"version": "1.0", "servers": ["server1", "server2"]}
            
            # Mock resolve_servers_from_registry_batch which is used by the command
            with mock.patch('mcp_installer.config.resolve_servers_from_registry_batch') as mock_resolve_batch:
                # Return server details that the command will process
                mock_resolve_batch.return_value = {
                    "server1": {"id": "server1", "name": "server1"},
                    "server2": {"id": "server2", "name": "server2"}
                }
                
                # Mock environment variable prompting (non-interactive mode)
                with mock.patch('click.prompt'):
                    runner = CliRunner()
                    result = runner.invoke(cli, ['config', 'install', '--no-interactive'])
                    
                    # Check result
                    assert result.exit_code == 0
                    assert "Using MCP config file" in result.output
                    assert "Installed" in result.output
                    
                    # Verify the batch resolve was called once with the right server IDs
                    mock_resolve_batch.assert_called_once()
                    # Check the server list in the resolve_batch call
                    _, args, _ = mock_resolve_batch.mock_calls[0]
                    assert args[1] == ["server1", "server2"]


def test_config_verify_command(mock_registry_client, mock_vscode_settings, mock_mcp_config_file):
    """Test the 'config verify' command."""
    # Mock load_mcp_config to ensure it returns the expected format
    with mock.patch('mcp_installer.config.load_mcp_config') as mock_load_config:
        mock_load_config.return_value = {"version": "1.0", "servers": ["server1", "server2"]}
        
        # Mock resolve_servers_from_registry_batch which is used by the command
        with mock.patch('mcp_installer.config.resolve_servers_from_registry_batch') as mock_resolve_batch:
            # Return server details that the command will process
            mock_resolve_batch.return_value = {
                "server1": {"id": "server1", "name": "server1", "packages": [{"name": "docker-image1"}]},
                "server2": {"id": "server2", "name": "server2", "packages": [{"name": "docker-image2"}]}
            }
            
            # Mock extract_mcp_servers to simulate only server1 being installed
            with mock.patch('mcp_installer.main.extract_mcp_servers') as mock_extract:
                # Only server1 is installed, server2 is missing
                mock_extract.return_value = {"docker-image1"}
                
                runner = CliRunner()
                result = runner.invoke(cli, ['config', 'verify'])
                
                # In our setup, server1 is installed but server2 is not
                assert result.exit_code == 1  # Should exit with code 1 for missing servers
                assert "Missing MCP servers" in result.output
                assert "server2" in result.output  # server2 should be reported as missing


def test_config_init_command(mock_vscode_settings):
    """Test the 'config init' command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "output.yml"
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'init', '--output', str(output_file)])
        
        # Check result
        assert result.exit_code == 0
        assert f"Created MCP config file: {output_file}" in result.output
        
        # Verify the file was created with the expected content
        assert output_file.exists()
        with open(output_file, 'r') as f:
            config = yaml.safe_load(f)
            assert "version" in config
            assert "servers" in config
            assert "docker-image1" in config["servers"]
