#!/usr/bin/env python3.13
"""
MCP Registry Client

This module provides functionality to interact with the MCP Registry API.
"""

import json
import os
import subprocess
from typing import Dict, List, Optional, Any, Union
import requests


DEFAULT_REGISTRY_URL = "https://demo.registry.azure-mcp.net"


def get_registry_url() -> str:
    """Get the MCP Registry URL from environment variable or default"""
    return os.environ.get("MCP_REGISTRY_URL", DEFAULT_REGISTRY_URL)


def get_vscode_path() -> str:
    """Get the VS Code executable path from environment variable or default to 'code'"""
    return os.environ.get("MCP_VSCODE_PATH", "code")


class MCPRegistryClient:
    """Client for interacting with the MCP Registry API"""
    
    def __init__(self, registry_url: Optional[str] = None):
        """Initialize the registry client with an optional custom URL"""
        self.registry_url = registry_url or get_registry_url()
        
    def list_servers(self, limit: int = 30, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        List available MCP servers from the registry
        
        Args:
            limit: Maximum number of entries to return (default: 30, max: 100)
            cursor: Pagination cursor for retrieving next set of results
            
        Returns:
            Dictionary with servers list and metadata
        """
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        response = requests.get(f"{self.registry_url}/v0/servers", params=params)
        response.raise_for_status()
        return response.json()
        
    def get_server(self, server_id: str) -> Dict[str, Any]:
        """
        Get details for a specific server by ID
        
        Args:
            server_id: Unique identifier of the server entry
            
        Returns:
            Dictionary with server details
        """
        response = requests.get(f"{self.registry_url}/v0/servers/{server_id}")
        response.raise_for_status()
        return response.json()
        
    def search_servers(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for servers by name or description
        
        Note: This performs client-side filtering on results from list_servers
        since the registry doesn't have a dedicated search endpoint.
        
        Args:
            query: Search query string (case-insensitive)
            
        Returns:
            List of matching server entries
        """
        # First, get the list of servers
        results = self.list_servers(limit=100)
        servers = results.get("servers", [])
        
        # Client-side filtering based on query
        query = query.lower()
        matches = []
        
        for server in servers:
            name = server.get("name", "").lower()
            description = server.get("description", "").lower()
            
            # Exact name match (case-insensitive)
            # - io.github.felores/github will match exactly "io.github.felores/github"
            # - "github" will not match "io.github.felores/github"
            name_match = query == name
            
            # Check if query matches either the name exactly or is found in the description
            if name_match or query in description:
                matches.append(server)
                
        return matches


def convert_to_vscode_config(server_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert registry server data to VS Code configuration format
    
    Args:
        server_data: Server data from the registry API
        
    Returns:
        Dictionary with VS Code server configuration
    """
    # Extract the server name (use a friendly version if possible)
    name = server_data.get("name", "")
    if "/" in name:
        # Extract the part after the last slash as the friendly name
        friendly_name = name.split("/")[-1]
    else:
        friendly_name = name
    
    # Default configuration
    config = {
        "name": friendly_name
    }
    
    # Find the appropriate package to use
    packages = server_data.get("packages", [])
    if not packages:
        raise ValueError("Server has no package information")
        
    # Prefer certain package types in this order: docker, npm, other
    package = None
    
    # First try to find a docker package
    for pkg in packages:
        if pkg.get("registry_name") == "docker":
            package = pkg
            break
            
    # If no docker package, try npm
    if package is None:
        for pkg in packages:
            if pkg.get("registry_name") == "npm":
                package = pkg
                break
                
    # If still no package, use the first one
    if package is None and packages:
        package = packages[0]
        
    if package is None:
        raise ValueError("No usable package found in server data")
        
    # Set command based on package type
    registry_name = package.get("registry_name", "").lower()
    
    # Get runtime arguments with their value_hints
    runtime_args = []
    for arg in package.get("runtime_arguments", []):
        if arg.get("type") == "positional" and arg.get("value_hint"):
            runtime_args.append(arg.get("value_hint"))
    
    if registry_name == "docker":
        config["command"] = "docker"
        
        # For Docker, we use the standard run arguments plus any runtime_arguments
        args = []
        
        # If we have runtime arguments, use them
        if runtime_args:
            args = runtime_args
        else:
            # Fallback to standard Docker arguments
            args = ["run", "-i", "--rm"]
            
            # Add environment variable flags if needed
            env_vars = package.get("environment_variables", [])
            for env in env_vars:
                env_name = env.get("name")
                if env_name:
                    args.extend(["-e", env_name])
            
            # Add the docker image - use package name as fallback
            args.append(package.get("name"))
        
        config["args"] = args
        
    elif registry_name == "npm":
        config["command"] = "npx"
        
        # For npm packages, use the runtime arguments if available
        if runtime_args:
            config["args"] = runtime_args
        else:
            # Fallback to just the package name
            config["args"] = [package.get("name")]
        
    else:
        # For other package types, try to use runtime arguments or fallback to package name
        config["command"] = registry_name
        if runtime_args:
            config["args"] = runtime_args
        else:
            config["args"] = [package.get("name")]
        
    # Add environment variables to config if any
    env_vars = package.get("environment_variables", [])
    if env_vars:
        config["env"] = {}
        for env in env_vars:
            env_name = env.get("name")
            if env_name:
                # Set an empty value by default - user will need to fill this in
                config["env"][env_name] = ""
    
    return config


def install_server_in_vscode(config: Dict[str, Any], scope: str = "user") -> subprocess.CompletedProcess:
    """
    Use subprocess to call VS Code CLI to install the server
    
    Args:
        config: VS Code server configuration
        scope: Installation scope ('user' or 'workspace')
        
    Returns:
        CompletedProcess instance with return code and output
    """
    config_json = json.dumps(config)
    
    # Get the VS Code executable path
    vscode_path = get_vscode_path()
    
    # Build the command
    cmd = [vscode_path, f"--add-mcp", config_json]
    
    # Run the command
    return subprocess.run(cmd, check=True, capture_output=True, text=True)
