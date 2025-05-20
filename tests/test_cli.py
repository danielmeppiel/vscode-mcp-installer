"""Tests for the MCP Server CLI interface."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

# Import CLI function directly
# The mcp_installer.main module doesn't import server.py, so this is safe
from mcp_installer.main import cli, registry


def test_list_command_no_servers():
    """Test the 'list' command when no servers are configured."""
    # Create a temporary settings file with no MCP servers
    settings_content = {
        "editor.fontSize": 12
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Patch the find_settings_file to return our temp file
        with patch('mcp_installer.main.find_settings_file', return_value=Path(temp_path)):
            runner = CliRunner()
            result = runner.invoke(cli, ['list'])
            # Check that the command executed successfully
            assert result.exit_code == 0
            # Check that the appropriate message is displayed
            assert "No MCP servers detected in settings.json" in result.output
    finally:
        # Clean up
        os.unlink(temp_path)


def test_list_command_with_servers():
    """Test the 'list' command with servers configured."""
    # Create a temporary settings file with MCP servers
    settings_content = {
        "mcp": {
            "servers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "ghcr.io/github/github-mcp-server"
                    ],
                    "env": {
                        "TOKEN": "secret"
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Patch the find_settings_file to return our temp file
        with patch('mcp_installer.main.find_settings_file', return_value=Path(temp_path)):
            runner = CliRunner()
            result = runner.invoke(cli, ['list'])
            # Check that the command executed successfully
            assert result.exit_code == 0
            # Check that the server is listed with proper details
            assert "Server: github" in result.output
            assert "ghcr.io/github/github-mcp-server" in result.output
            assert "Command: docker" in result.output
    finally:
        # Clean up
        os.unlink(temp_path)


def test_check_command_all_installed():
    """Test the 'check' command when all servers are installed."""
    # Create a temporary settings file with MCP servers
    settings_content = {
        "mcp": {
            "servers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "ghcr.io/github/github-mcp-server"
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Patch the find_settings_file to return our temp file
        with patch('mcp_installer.main.find_settings_file', return_value=Path(temp_path)):
            runner = CliRunner()
            result = runner.invoke(cli, ['check', 'ghcr.io/github/github-mcp-server'])
            # Should exit with code 0 when all servers are installed
            assert "All required MCP servers are installed." in result.output
    finally:
        # Clean up
        os.unlink(temp_path)


def test_check_command_missing_server():
    """Test the 'check' command when some servers are missing."""
    # Create a temporary settings file with MCP servers
    settings_content = {
        "mcp": {
            "servers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "ghcr.io/github/github-mcp-server"
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Patch the find_settings_file to return our temp file
        with patch('mcp_installer.main.find_settings_file', return_value=Path(temp_path)):
            runner = CliRunner()
            result = runner.invoke(cli, ['check', 'mcr.microsoft.com/missing/server:latest'])
            # Should list missing servers
            assert "The following MCP servers are not installed:" in result.output
            assert "mcr.microsoft.com/missing/server:latest" in result.output
    finally:
        # Clean up
        os.unlink(temp_path)


# Tests for registry-related CLI commands
def test_registry_command_group():
    """Test the 'registry' command group exists and shows help text."""
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', '--help'])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    # Check that basic help text is shown
    assert "Commands to interact with the MCP Registry" in result.output
    assert "list" in result.output
    assert "search" in result.output
    assert "show" in result.output
    assert "install" in result.output
    
@patch('mcp_installer.registry.MCPRegistryClient')
def test_registry_list_command(mock_client_class):
    """Test the 'registry list' command."""
    # Setup mock client response
    mock_client = mock_client_class.return_value
    mock_client.list_servers.return_value = {
        "servers": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "test-mcp-server",
                "description": "A test MCP server",
                "created_at": "2025-05-17T17:34:22.912Z"
            },
            {
                "id": "456e7890-e12d-34e5-f678-426614174001",
                "name": "another-server",
                "description": "Another test MCP server",
                "created_at": "2025-05-18T10:22:15.301Z"
            }
        ],
        "metadata": {
            "count": 2
        }
    }
    
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', 'list'])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    # Check that both servers are listed
    assert "test-mcp-server" in result.output
    assert "another-server" in result.output
    assert "Total: 2 servers" in result.output
    # Verify the client was called correctly
    mock_client.list_servers.assert_called_once_with(limit=30, cursor=None)


@patch('mcp_installer.registry.MCPRegistryClient')
def test_registry_search_command(mock_client_class):
    """Test the 'registry search' command."""
    # Setup mock client response
    mock_client = mock_client_class.return_value
    mock_client.search_servers.return_value = [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "redis-mcp-server",
            "description": "A Redis MCP server for key-value storage",
        }
    ]
    
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', 'search', 'redis'])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    # Check that the search results are displayed
    assert "redis-mcp-server" in result.output
    assert "A Redis MCP server" in result.output
    # Verify the client was called correctly
    mock_client.search_servers.assert_called_once_with("redis")


@patch('mcp_installer.registry.MCPRegistryClient')
def test_registry_show_command(mock_client_class):
    """Test the 'registry show' command."""
    # Setup mock client response
    mock_client = mock_client_class.return_value
    mock_client.get_server.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "redis-mcp-server",
        "description": "A Redis MCP server for key-value storage",
        "repository": {
            "url": "https://github.com/example/redis-mcp-server",
            "source": "github"
        },
        "version_detail": {
            "version": "1.0.0",
            "release_date": "2025-05-01T00:00:00Z",
            "is_latest": True
        },
        "packages": [
            {
                "registry_name": "docker",
                "name": "mcp/redis",
                "version": "1.0.0",
                "package_arguments": [
                    {
                        "description": "Docker image",
                        "type": "positional",
                        "value": "mcp/redis:latest"
                    }
                ],
                "environment_variables": [
                    {
                        "name": "REDIS_URL", 
                        "description": "Redis connection URL"
                    }
                ]
            }
        ]
    }
    
    server_id = "123e4567-e89b-12d3-a456-426614174000"
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', 'show', server_id])
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    # Check that server details are displayed
    assert "redis-mcp-server" in result.output
    assert "A Redis MCP server for key-value storage" in result.output
    assert "https://github.com/example/redis-mcp-server" in result.output
    assert "1.0.0" in result.output
    assert "docker" in result.output
    assert "REDIS_URL" in result.output
    # Verify the client was called correctly
    mock_client.get_server.assert_called_once_with(server_id)


@patch('mcp_installer.registry.MCPRegistryClient')
@patch('mcp_installer.registry.convert_to_vscode_config')
@patch('mcp_installer.registry.install_server_in_vscode')
def test_registry_install_command_by_id(mock_install, mock_convert, mock_client_class):
    """Test the 'registry install' command with --by-id flag."""
    # Setup mock client response
    mock_client = mock_client_class.return_value
    server_data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "redis-mcp-server",
        "description": "A Redis MCP server"
    }
    mock_client.get_server.return_value = server_data
    
    # Setup mock conversion and installation
    vscode_config = {"name": "redis-mcp-server", "command": "docker", "args": ["run", "-i", "--rm", "mcp/redis"]}
    mock_convert.return_value = vscode_config
    mock_install.return_value.stdout = "Server installed"
    
    # Run command with --by-id flag and respond 'y' to the confirmation prompt
    server_id = "123e4567-e89b-12d3-a456-426614174000"
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', 'install', server_id, '--by-id'], input='y\n')
    
    # Verify the command executed successfully
    assert result.exit_code == 0
    # Check expected output
    assert "redis-mcp-server" in result.output
    assert "Server installed successfully" in result.output
    # Verify the client and utility functions were called correctly
    mock_client.get_server.assert_called_once_with(server_id)
    mock_convert.assert_called_once_with(server_data)
    mock_install.assert_called_once_with(vscode_config)


@patch('mcp_installer.registry.MCPRegistryClient')
def test_registry_install_command_by_name_multiple_matches(mock_client_class):
    """Test the 'registry install' command with name that matches multiple servers."""
    # Setup mock client response
    mock_client = mock_client_class.return_value
    mock_client.search_servers.return_value = [
        {"id": "123", "name": "redis-server-1"},
        {"id": "456", "name": "redis-server-2"}
    ]
    
    runner = CliRunner()
    result = runner.invoke(cli, ['registry', 'install', 'redis'])
    
    # Verify the command executed with warning
    assert result.exit_code == 0
    # Check that multiple matches warning is displayed
    assert "Multiple servers found matching" in result.output
    assert "Please use --by-id flag" in result.output
    # Verify the client was called correctly
    mock_client.search_servers.assert_called_once_with("redis")
    # Verify that get_server was not called (should not proceed to installation)
    mock_client.get_server.assert_not_called()
