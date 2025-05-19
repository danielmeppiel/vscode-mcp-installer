"""Tests for the MCP Server CLI interface."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

# Import CLI function without importing MCP server
import sys
import importlib.util
from types import ModuleType

def import_module_from_file(name, path):
    """Import a module from file without importing its imports."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Import just the main module without triggering server imports
main_module = import_module_from_file(
    "mcp_installer.main", 
    "/Users/danielmeppiel/Repos/vscode-mcp-installer/mcp_installer/main.py"
)
cli = main_module.cli


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
