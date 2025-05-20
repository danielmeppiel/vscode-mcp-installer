#!/usr/bin/env python3.13
"""
MCP Server for MCP Installer

This module provides MCP server functionality for the MCP installer CLI commands,
allowing them to be accessed through the MCP protocol.
"""

import json
import requests
from typing import Dict, List, Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp_installer.main import find_settings_file, extract_mcp_servers, check_missing_servers
from mcp_installer.registry import (
    MCPRegistryClient, 
    convert_to_vscode_config, 
    install_server_in_vscode,
    get_registry_url
)

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

@mcp.tool(description="List all available MCP servers in the registry")
def list_available_servers(limit: int = 30, cursor: Optional[str] = None) -> Dict[str, Any]:
    """
    List available MCP servers from the MCP Registry.
    
    Args:
        limit: Maximum number of entries to return (default: 30)
        cursor: Pagination cursor for retrieving next set of results
    
    Returns:
        Dictionary with servers list and metadata
    """
    try:
        client = MCPRegistryClient()
        results = client.list_servers(limit=limit, cursor=cursor)
        
        # Add registry information to the response
        results["registry_url"] = get_registry_url()
        return results
    except Exception as e:
        return {
            "error": str(e),
            "registry_url": get_registry_url(),
            "servers": []
        }


@mcp.tool(description="Get details about a specific MCP server")
def get_server_details(server_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific MCP server.
    
    Args:
        server_id: Unique identifier of the server
        
    Returns:
        Dictionary with server details
    """
    try:
        client = MCPRegistryClient()
        server_data = client.get_server(server_id)
        
        # Add registry information to the response
        server_data["registry_url"] = get_registry_url()
        
        # Add VS Code configuration preview
        try:
            vscode_config = convert_to_vscode_config(server_data)
            server_data["vscode_config"] = vscode_config
        except Exception as e:
            server_data["vscode_config_error"] = str(e)
            
        return server_data
    except Exception as e:
        return {
            "error": str(e),
            "registry_url": get_registry_url(),
            "server_id": server_id
        }


@mcp.tool(description="Search for MCP servers by name or description")
def search_servers(query: str) -> Dict[str, Any]:
    """
    Search for MCP servers in the registry by name or description.
    
    Args:
        query: Search query string (case-insensitive)
        
    Returns:
        Dictionary with matching servers
    """
    try:
        client = MCPRegistryClient()
        servers = client.search_servers(query)
        
        return {
            "registry_url": get_registry_url(),
            "query": query,
            "servers": servers,
            "count": len(servers)
        }
    except Exception as e:
        return {
            "error": str(e),
            "registry_url": get_registry_url(),
            "query": query,
            "servers": [],
            "count": 0
        }


@mcp.tool(description="Install an MCP server from the registry")
def install_server(server_id: str = None, server_name: str = None) -> Dict[str, Any]:
    """
    Install an MCP server from the registry to VS Code.
    
    Args:
        server_id: Unique identifier of the server to install
        server_name: Name of the server to search for and install (used if server_id is not provided)
        
    Returns:
        Dictionary with installation result
    """
    try:
        if not server_id and not server_name:
            return {
                "success": False,
                "error": "Either server_id or server_name must be provided"
            }
            
        client = MCPRegistryClient()
        
        # Find server by ID or name
        server_data = None
        if server_id:
            server_data = client.get_server(server_id)
        elif server_name:
            # Find by name (search for it)
            servers = client.search_servers(server_name)
            if servers:
                # Use the first match
                server_data = client.get_server(servers[0]["id"])
            else:
                return {
                    "success": False,
                    "error": f"No server found with name '{server_name}'",
                    "registry_url": get_registry_url()
                }
        
        if not server_data:
            return {
                "success": False,
                "error": "Server not found",
                "registry_url": get_registry_url()
            }
            
        # Convert registry data to VS Code configuration
        vscode_config = convert_to_vscode_config(server_data)
        
        # Install the server
        result = install_server_in_vscode(vscode_config)
        
        return {
            "success": True,
            "message": f"Installed '{server_data.get('name', '')}' successfully",
            "server_id": server_data.get("id", ""),
            "registry_url": get_registry_url(),
            "command_output": result.stdout,
            "vscode_config": vscode_config
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "registry_url": get_registry_url()
        }


@mcp.tool(description="Show registry information")
def get_registry_info() -> Dict[str, Any]:
    """
    Get information about the currently configured MCP Registry.
    
    Returns:
        Dictionary with registry information
    """
    registry_url = get_registry_url()
    
    try:
        # Check if registry is accessible
        client = MCPRegistryClient()
        ping_response = requests.get(f"{registry_url}/v0/health")
        ping_response.raise_for_status()
        
        return {
            "registry_url": registry_url,
            "status": "online",
            "health_check": ping_response.json(),
            "message": "MCP Registry is accessible"
        }
    except Exception as e:
        return {
            "registry_url": registry_url,
            "status": "error",
            "error": str(e),
            "message": "Error connecting to MCP Registry"
        }


if __name__ == "__main__":
    mcp.run()