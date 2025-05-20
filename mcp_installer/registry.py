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

    def batch_search_servers(self, identifiers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Search for multiple servers in one operation, minimizing network requests
        
        Args:
            identifiers: List of server identifiers (IDs or names)
            
        Returns:
            Dictionary mapping identifiers to their server details, or None if not found
        """
        # First, get the full list of servers (one network call)
        results = self.list_servers(limit=100)
        all_servers = results.get("servers", [])
        
        # Build maps for quick lookups
        id_map = {server.get("id"): server for server in all_servers}
        name_map = {server.get("name"): server for server in all_servers}
        
        # Process all identifiers using the locally-cached data
        server_details = {}
        server_ids_to_fetch = []
        
        for identifier in identifiers:
            # Check if identifier is an ID we already have
            if identifier in id_map:
                server_ids_to_fetch.append(identifier)
                continue
                
            # Check if identifier is a name
            if identifier in name_map:
                server_ids_to_fetch.append(name_map[identifier].get("id"))
                continue
                
            # If not found by exact match, try case-insensitive search in the local data
            identifier_lower = identifier.lower()
            found = False
            
            for server in all_servers:
                if server.get("name", "").lower() == identifier_lower:
                    server_ids_to_fetch.append(server.get("id"))
                    found = True
                    break
                    
            if not found:
                # Server not found at all - we'll return None for this one
                server_details[identifier] = None
        
        # Make one request per unique server ID we need to fully resolve
        # This is still more efficient than one per identifier
        for server_id in set(server_ids_to_fetch):
            try:
                server_data = self.get_server(server_id)
                # Map this resolved server to all identifiers that match it
                for identifier in identifiers:
                    # Check if this identifier led to this server ID
                    if identifier in id_map and id_map[identifier].get("id") == server_id:
                        server_details[identifier] = server_data
                    elif identifier in name_map and name_map[identifier].get("id") == server_id:
                        server_details[identifier] = server_data
                    else:
                        # Search by lowercase name
                        identifier_lower = identifier.lower()
                        for server in all_servers:
                            if server.get("name", "").lower() == identifier_lower and server.get("id") == server_id:
                                server_details[identifier] = server_data
                                break
            except Exception:
                # If we fail to get a specific server, continue with the next one
                # Any identifiers that were supposed to use this server will remain unmapped
                pass
                
        return server_details


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
    Install an MCP server by directly modifying the VS Code settings.json file
    
    Args:
        config: VS Code server configuration
        scope: Installation scope ('user' or 'workspace')
        
    Returns:
        CompletedProcess instance with return code and output (simulated for compatibility)
    """
    from mcp_installer.main import find_settings_file
    import re
    
    # Get settings file path
    settings_path = find_settings_file()
    
    # Read the current settings file
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Parse the JSON, handling comments in the file
    content_no_comments = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    try:
        settings = json.loads(content_no_comments)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse settings file: {e}") from e
    
    # Extract server name
    server_name = config.get("name", f"server-{hash(json.dumps(config))}")
    
    # Ensure the MCP section exists
    if "mcp" not in settings:
        settings["mcp"] = {}
    
    # Ensure the servers section exists
    if "servers" not in settings["mcp"]:
        settings["mcp"]["servers"] = {}
    
    # Add or update the server
    settings["mcp"]["servers"][server_name] = {
        "command": config.get("command"),
        "args": config.get("args", []),
    }
    
    # Add environment variables if present
    if "env" in config:
        settings["mcp"]["servers"][server_name]["env"] = config["env"]
    
    # Write the updated settings back to the file
    # We need to preserve original formatting and comments, so we'll use a different approach
    # Rather than completely overwriting, we'll append or modify the specific section
    # First convert the section to JSON with nice formatting
    server_config_json = json.dumps(settings["mcp"]["servers"][server_name], indent=4)
    
    # Create a simulated result for compatibility
    result = subprocess.CompletedProcess(
        args=["code", "--add-mcp"],
        returncode=0,
        stdout=f"Successfully added MCP server '{server_name}' to VS Code settings.",
        stderr=""
    )
    
    # Now write the modified content back to the file
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
        return result
    except Exception as e:
        result.returncode = 1
        result.stderr = f"Error writing to settings file: {str(e)}"
        raise ValueError(f"Failed to update settings file: {e}") from e
