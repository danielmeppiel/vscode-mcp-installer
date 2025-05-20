"""Tests for the MCP Server verification tool."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from mcp_installer.main import extract_mcp_servers, check_missing_servers


def test_extract_mcp_servers_no_servers():
    """Test extracting MCP servers when no servers are configured."""
    # Create a temporary settings file with no MCP servers
    settings_content = {
        "editor.fontSize": 12,
        "terminal.integrated.shell.osx": "/bin/zsh"
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Test extraction
        result = extract_mcp_servers(Path(temp_path))
        assert result == set()
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_mcp_servers_with_docker():
    """Test extracting MCP servers with docker command configuration."""
    # Create a temporary settings file for testing
    settings_content = {
        "mcp": {
            "servers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "-e", "GITHUB_TOKEN", 
                        "ghcr.io/github/github-mcp-server"
                    ]
                },
                "oracle": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "-e", "CONN_STRING",
                        "dmeppiel/oracle-mcp-server"
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Test extraction
        result = extract_mcp_servers(Path(temp_path))
        assert "ghcr.io/github/github-mcp-server" in result
        assert "dmeppiel/oracle-mcp-server" in result
        assert len(result) == 2  # Only two entries, not four
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_mcp_servers_with_non_docker():
    """Test extracting MCP servers with non-docker command configuration."""
    # Create a temporary settings file for testing
    settings_content = {
        "mcp": {
            "servers": {
                "azure": {
                    "command": "npx",
                    "args": [
                        "-y", "@azure/mcp@latest", "server", "start"
                    ]
                },
                "custom-server": {
                    "command": "uvx",
                    "args": [
                        "mcp-server-fetch"
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Test extraction
        result = extract_mcp_servers(Path(temp_path))
        assert "@azure/mcp" in result
        assert "custom-server" in result
        assert len(result) == 2
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_mcp_servers_mixed_config():
    """Test extracting MCP servers with mixed configurations."""
    # Create a temporary settings file for testing with mixed configurations
    settings_content = {
        "mcp": {
            "servers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", "-e", "GITHUB_TOKEN", 
                        "ghcr.io/github/github-mcp-server"
                    ]
                },
                "azure": {
                    "command": "npx",
                    "args": [
                        "-y", "@azure/mcp@latest", "server", "start"
                    ]
                },
                "empty-server": {
                    "command": "unknown"
                    # No args defined
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Test extraction
        result = extract_mcp_servers(Path(temp_path))
        assert "ghcr.io/github/github-mcp-server" in result
        assert "@azure/mcp" in result
        assert "empty-server" in result
        assert len(result) == 3
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_mcp_servers_complex_docker_args():
    """Test extracting MCP servers with complex docker arguments."""
    # Create a temporary settings file with many docker args
    settings_content = {
        "mcp": {
            "servers": {
                "complex": {
                    "command": "docker",
                    "args": [
                        "run", "-i", "--rm", 
                        "-e", "ENV_VAR1", 
                        "-e", "ENV_VAR2",
                        "-v", "/path/to/volume:/container/path",
                        "-p", "8080:8080",
                        "mcr.microsoft.com/vscode/mcp/server:latest"
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
        json.dump(settings_content, temp)
        temp_path = temp.name
    
    try:
        # Test extraction
        result = extract_mcp_servers(Path(temp_path))
        assert "mcr.microsoft.com/vscode/mcp/server:latest" in result
        assert len(result) == 1
    finally:
        # Clean up
        os.unlink(temp_path)


def test_check_missing_servers():
    """Test checking for missing servers."""
    installed = {"server1:tag", "server2:tag", "server3:tag"}
    
    # All servers are installed
    required1 = ["server1:tag", "server2:tag"]
    assert check_missing_servers(required1, installed) == []
    
    # Some servers are missing
    required2 = ["server1:tag", "server4:tag"]
    assert check_missing_servers(required2, installed) == ["server4:tag"]
    
    # All servers are missing
    required3 = ["server4:tag", "server5:tag"]
    assert check_missing_servers(required3, installed) == ["server4:tag", "server5:tag"]
