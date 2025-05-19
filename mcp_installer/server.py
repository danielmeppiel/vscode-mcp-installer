#!/usr/bin/env python3.13
"""
MCP Server for MCP Installer

This module provides MCP server functionality for the MCP installer CLI commands,
allowing them to be accessed through the MCP protocol.
"""

from mcp.server.fastmcp import FastMCP
from mcp_installer.main import find_settings_file, extract_mcp_servers, check_missing_servers

# Create the MCP server
mcp = FastMCP(
    name="MCP Installer"
)


@mcp.tool(description="List all MCP servers installed in VS Code")
def list_servers() -> dict:
    """List all MCP servers currently installed in VS Code settings."""
    try:
        settings_path = find_settings_file()
        installed_servers = extract_mcp_servers(settings_path)
        
        servers_list = sorted(list(installed_servers))
        
        # Return in a structured format for better display
        return {
            "settings_path": str(settings_path),
            "count": len(servers_list),
            "servers": servers_list
        }
    except Exception as e:
        return {
            "error": str(e),
            "servers": []
        }


@mcp.tool(description="Check if specific MCP servers are installed in VS Code")
def check_servers(servers: list[str]) -> dict:
    """
    Verify MCP server installation in VSCode.
    
    Args:
        servers: List of MCP server identifiers to check
    """
    try:
        # Find and read settings file
        settings_path = find_settings_file()
        installed_servers = extract_mcp_servers(settings_path)
        
        # Check which servers are missing
        missing_servers = check_missing_servers(servers, installed_servers)
        
        # Return results
        return {
            "all_installed": len(missing_servers) == 0,
            "installed_servers": list(installed_servers),
            "missing_servers": missing_servers
        }
    except Exception as e:
        return {
            "error": str(e),
            "all_installed": False,
            "installed_servers": [],
            "missing_servers": servers
        }

if __name__ == "__main__":
    mcp.run()