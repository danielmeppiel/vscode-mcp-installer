#!/usr/bin/env python3.13
"""
MCP configuration management utilities.

Provides functionality to load, verify, and install MCP servers
from a configuration file.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

import click
import yaml

from mcp_installer.registry import MCPRegistryClient, convert_to_vscode_config, install_server_in_vscode


def find_mcp_config_file(filename: str = "mcp.yml") -> Optional[Path]:
    """Find mcp.yml config file by searching up from current directory."""
    cwd = Path.cwd()
    
    # Look in current directory and parents
    for path in [cwd, *cwd.parents]:
        config_path = path / filename
        if config_path.exists():
            return config_path
    
    return None


def load_mcp_config(config_path: Path) -> Dict:
    """
    Load and parse MCP config file.
    
    Args:
        config_path: Path to the MCP config file
        
    Returns:
        Parsed configuration dictionary
        
    Raises:
        ValueError: If the file cannot be parsed as YAML
    """
    with open(config_path, 'r') as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse MCP config file: {e}")


def resolve_server_from_registry(
    registry_client: MCPRegistryClient, 
    server_identifier: str,
) -> Dict:
    """
    Resolve a server from the registry by ID or name.
    
    Args:
        registry_client: MCPRegistryClient instance
        server_identifier: Server ID or name from mcp.yml
        
    Returns:
        Server data from registry
        
    Raises:
        ValueError: If the server cannot be resolved
    """
    try:
        # First try to resolve by ID (for backward compatibility)
        try:
            return registry_client.get_server(server_identifier)
        except Exception:
            # If that fails, try to resolve by name
            servers = registry_client.search_servers(server_identifier)
            
            # Look for an exact name match
            for server in servers:
                if server.get("name") == server_identifier:
                    return registry_client.get_server(server.get("id"))
            
            # If no exact match, raise an error
            if not servers:
                raise ValueError(f"No server found with name: {server_identifier}")
            
            # If there are multiple matches but no exact match, use the first one
            # (assuming it's the latest version)
            return registry_client.get_server(servers[0].get("id"))
            
    except Exception as e:
        raise ValueError(f"Server not found in registry: {server_identifier}") from e


def resolve_servers_from_registry_batch(
    registry_client: MCPRegistryClient,
    server_identifiers: List[str]
) -> Dict[str, Dict]:
    """
    Resolve multiple servers from the registry in batch for better performance.
    
    Args:
        registry_client: MCPRegistryClient instance
        server_identifiers: List of server IDs or names from mcp.yml
        
    Returns:
        Dictionary mapping server identifiers to their registry data
        
    Raises:
        ValueError: If any of the servers cannot be resolved
    """
    # Use the batch search function to minimize network requests
    server_details = registry_client.batch_search_servers(server_identifiers)
    
    # Check if any servers were not found
    missing_servers = [id for id, data in server_details.items() if data is None]
    if missing_servers:
        if len(missing_servers) == 1:
            raise ValueError(f"Server not found in registry: {missing_servers[0]}")
        else:
            raise ValueError(f"Multiple servers not found in registry: {', '.join(missing_servers)}")
            
    return server_details


def install_server_from_registry(
    server_identifier: str, 
    registry_client: MCPRegistryClient, 
    vscode_settings_path: Path,
    interactive: bool = True
) -> bool:
    """
    Install a server from the registry into VSCode settings.
    
    Args:
        server_identifier: Server ID or name from mcp.yml
        registry_client: MCPRegistryClient instance
        vscode_settings_path: Path to VSCode settings.json
        interactive: Whether to prompt for environment variables
        
    Returns:
        True if installation was successful, False otherwise
    """
    # Resolve server from registry
    try:
        server_data = resolve_server_from_registry(registry_client, server_identifier)
    except Exception as e:
        click.secho(f"Error resolving server: {e}", fg="red")
        return False
    
    # Get server name from registry data
    registry_name = server_data.get("name", "")
    server_name = registry_name.split("/")[-1] if "/" in registry_name else registry_name
    
    click.secho(f"\nInstalling server: {server_name}", fg="green")
    click.secho(f"  ID: {server_data.get('id')}", fg="blue")
    
    # Convert to VSCode configuration
    try:
        vscode_config = convert_to_vscode_config(server_data)
    except Exception as e:
        click.secho(f"Error creating configuration: {e}", fg="red")
        return False
    
    # If in interactive mode and env vars are present, prompt for values
    if interactive and "env" in vscode_config:
        click.secho("\nEnvironment Variables:", fg="yellow")
        for env_name in vscode_config["env"].keys():
            env_hidden = any(keyword in env_name.upper() for keyword in ["TOKEN", "SECRET", "KEY", "PASSWORD", "PASS"])
            
            # Check if already set in environment
            default_value = os.environ.get(env_name, "")
            
            # Prompt user
            env_value = click.prompt(
                f"  {env_name}", 
                default=default_value,
                hide_input=env_hidden,
                show_default=not env_hidden and bool(default_value)
            )
            
            vscode_config["env"][env_name] = env_value
    
    # Install in VSCode settings
    try:
        result = install_server_in_vscode(vscode_config)
        if result.returncode == 0:
            click.secho(f"Server '{server_name}' installed successfully", fg="green")
            return True
        else:
            click.secho(f"Failed to install server: {result.stderr}", fg="red")
            return False
    except Exception as e:
        click.secho(f"Error installing server: {e}", fg="red")
        return False
