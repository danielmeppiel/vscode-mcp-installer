"""Tests for the MCP Server CLI interface."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Import CLI function directly
# The mcp_installer.main module doesn't import server.py, so this is safe
from mcp_installer.main import cli


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
