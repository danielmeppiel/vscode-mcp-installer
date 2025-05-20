#!/usr/bin/env python3.13
"""
MCP Server Verification Tool

This tool checks if the required MCP servers (specified by Docker image strings)
are installed in VSCode's settings.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set

import click


def find_settings_file() -> Path:
    """Locate the VSCode settings.json file based on the operating system."""
    if sys.platform == 'darwin':  # macOS
        settings_path = Path.home() / 'Library' / 'Application Support' / 'Code' / 'User' / 'settings.json'
    elif sys.platform == 'win32':  # Windows
        settings_path = Path.home() / 'AppData' / 'Roaming' / 'Code' / 'User' / 'settings.json'
    else:  # Linux and others
        settings_path = Path.home() / '.config' / 'Code' / 'User' / 'settings.json'
    
    if not settings_path.exists():
        raise FileNotFoundError(f"VSCode settings file not found at {settings_path}")
    
    return settings_path


def extract_mcp_servers(settings_path: Path) -> Set[str]:
    """
    Extract the list of installed MCP servers from settings.json.
    
    Identifies each MCP server based on its configuration and returns a set
    of server identifiers.
    """
    with open(settings_path, 'r') as f:
        settings = json.load(f)
    
    mcp_servers = set()
    
    # Check for MCP server settings (mcp.servers)
    if "mcp" in settings and "servers" in settings["mcp"]:
        servers = settings["mcp"]["servers"]
        for server_name, config in servers.items():
            command = config.get('command', 'unknown')
            
            # Different handling based on server type
            if command == "docker" and "args" in config:
                # For Docker servers, extract the image name
                docker_image = extract_docker_image(config["args"])
                if docker_image:
                    mcp_servers.add(docker_image)
                else:
                    # Fallback if we couldn't extract the image name
                    mcp_servers.add(f"{server_name} ({command})")
            
            elif command == "npx" and "args" in config:
                # For NPM packages, extract the package name
                npm_package = extract_npm_package(config["args"])
                if npm_package:
                    mcp_servers.add(npm_package)
                else:
                    # Fallback if we couldn't extract the package name
                    mcp_servers.add(f"{server_name} ({command})")
            
            else:
                # For any other server type
                server_identifier = f"{server_name} ({command})"
                mcp_servers.add(server_identifier)
    
    return mcp_servers

def extract_docker_image(args: List[str]) -> str:
    """Extract Docker image name from command arguments."""
    i = 0
    
    # Skip 'docker run' part and common flags
    while i < len(args) and args[i] in ["docker", "run", "-i", "--rm"]:
        i += 1
    
    # Process the remaining arguments
    while i < len(args):
        arg = args[i]
        if arg.startswith("-"):
            # Skip option flags and their values
            if arg in ["-e", "--env", "-v", "--volume", "-p", "--publish"]:
                i += 2  # Skip the flag and its value
            else:
                i += 1  # Skip just the flag
        else:
            # Found a non-flag argument, check if it looks like a Docker image
            if (":" in arg or "/" in arg or 
                arg.startswith("ghcr.io/") or 
                arg.startswith("mcr.microsoft.com/") or
                not arg.startswith("-")):
                return arg
            i += 1
    
    return None

def extract_npm_package(args: List[str]) -> str:
    """Extract NPM package name from command arguments."""
    for i, arg in enumerate(args):
        # Look for an argument that starts with '@' or contains a '/' which is common for npm packages
        if arg.startswith("@") or ("/" in arg and not arg.startswith("-")):
            if "@latest" in arg:
                # Extract just the package name if it has a version specifier
                return arg.split("@latest")[0]
            return arg
    
    # If we can't find a package name, check for just npm commands
    if len(args) > 0 and not args[0].startswith("-"):
        return args[0]
        
    return None
    

def check_missing_servers(required_servers: List[str], installed_servers: Set[str]) -> List[str]:
    """Check which required servers are missing from the installed set."""
    return [server for server in required_servers if server not in installed_servers]


@click.group()
def cli():
    """MCP Server Verification Tool for VS Code."""
    pass


@cli.command('check')
@click.argument('servers', nargs=-1, required=True)
def check_servers(servers):
    """
    Verify MCP server installation in VSCode.
    
    SERVERS: List of MCP server Docker images to check (e.g., "mcr.microsoft.com/mcp/server:1.0")
    """
    try:
        # Convert to list for consistent handling
        required_servers = list(servers)
        
        # Find and read settings file
        settings_path = find_settings_file()
        installed_servers = extract_mcp_servers(settings_path)
        
        # Check which servers are missing
        missing_servers = check_missing_servers(required_servers, installed_servers)
        
        # Report results
        if missing_servers:
            click.secho("The following MCP servers are not installed:", fg="yellow")
            for server in missing_servers:
                click.secho(f"  - {server}", fg="red")
            sys.exit(1)
        else:
            click.secho("All required MCP servers are installed.", fg="green")
            sys.exit(0)
            
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(2)


@cli.command('list')
def list_servers():
    """List all MCP servers currently installed in VS Code settings."""
    try:
        settings_path = find_settings_file()
        click.secho(f"Found settings file at: {settings_path}", fg="green")
        
        # Use the extract_mcp_servers function to get all servers
        installed_servers = extract_mcp_servers(settings_path)
        
        if installed_servers:
            click.secho("\nInstalled MCP servers:", fg="green")
            for server in sorted(installed_servers):
                click.secho(f"  - {server}", fg="blue")
            click.secho(f"\nTotal: {len(installed_servers)} servers", fg="green")
            
            # Also print detailed server configurations
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                
            if "mcp" in settings and "servers" in settings["mcp"]:
                click.secho("\nDetailed MCP Server Configurations:", fg="green")
                servers = settings["mcp"]["servers"]
                
                for server_name, config in servers.items():
                    click.secho(f"\nServer: {server_name}", fg="blue", bold=True)
                    click.secho(f"  Command: {config.get('command', 'N/A')}", fg="cyan")
                    
                    if "args" in config:
                        args_str = " ".join(config["args"])
                        click.secho(f"  Args: {args_str}", fg="cyan")
                    
                    if "env" in config:
                        click.secho("  Environment Variables:", fg="cyan")
                        for env_name, env_value in config["env"].items():
                            # Truncate long env values for readability
                            if len(str(env_value)) > 50:
                                env_value = str(env_value)[:47] + "..."
                            click.secho(f"    {env_name}: {env_value}", fg="cyan")
        else:
            click.secho("No MCP servers detected in settings.json", fg="yellow")
        
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)


# Registry-related commands
@cli.group('registry')
def registry():
    """Commands to interact with the MCP Registry."""
    pass


@registry.command('list')
@click.option('--limit', default=30, help='Maximum number of entries to return')
@click.option('--cursor', help='Pagination cursor for retrieving next set of results')
def list_registry_servers(limit, cursor):
    """List available MCP servers from the registry."""
    try:
        # Import here to avoid circular imports
        from mcp_installer.registry import MCPRegistryClient, get_registry_url
        
        registry_url = get_registry_url()
        click.secho(f"Using MCP Registry: {registry_url}", fg="green")
        
        client = MCPRegistryClient(registry_url)
        results = client.list_servers(limit=limit, cursor=cursor)
        
        servers = results.get("servers", [])
        metadata = results.get("metadata", {})
        
        if servers:
            click.secho("\nMCP Registry Servers:", fg="green")
            for server in servers:
                name = server.get("name", "Unknown")
                server_id = server.get("id", "")
                description = server.get("description", "")
                
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                    
                click.secho(f"\nServer: {name}", fg="blue", bold=True)
                click.secho(f"  ID: {server_id}", fg="cyan")
                click.secho(f"  Description: {description}", fg="cyan")
                
            click.secho(f"\nTotal: {len(servers)} servers", fg="green")
            
            # Show pagination info
            next_cursor = metadata.get("next_cursor")
            if next_cursor:
                click.secho(f"\nFor more results, run with --cursor={next_cursor}", fg="yellow")
        else:
            click.secho("No MCP servers found in the registry", fg="yellow")
            
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)


@registry.command('search')
@click.argument('query')
def search_registry_servers(query):
    """Search for MCP servers in the registry by name or description."""
    try:
        # Import here to avoid circular imports
        from mcp_installer.registry import MCPRegistryClient, get_registry_url
        
        registry_url = get_registry_url()
        click.secho(f"Using MCP Registry: {registry_url}", fg="green")
        click.secho(f"Searching for: '{query}'", fg="green")
        
        client = MCPRegistryClient(registry_url)
        servers = client.search_servers(query)
        
        if servers:
            click.secho(f"\nFound {len(servers)} matching servers:", fg="green")
            for server in servers:
                name = server.get("name", "Unknown")
                server_id = server.get("id", "")
                description = server.get("description", "")
                
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                    
                click.secho(f"\nServer: {name}", fg="blue", bold=True)
                click.secho(f"  ID: {server_id}", fg="cyan")
                click.secho(f"  Description: {description}", fg="cyan")
        else:
            click.secho(f"No servers found matching '{query}'", fg="yellow")
            
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)


@registry.command('show')
@click.argument('server_id')
def show_server_details(server_id):
    """Get detailed information about a specific MCP server."""
    try:
        # Import here to avoid circular imports
        from mcp_installer.registry import MCPRegistryClient, get_registry_url
        
        registry_url = get_registry_url()
        click.secho(f"Using MCP Registry: {registry_url}", fg="green")
        
        client = MCPRegistryClient(registry_url)
        server_data = client.get_server(server_id)
        
        # Display server information
        name = server_data.get("name", "Unknown")
        description = server_data.get("description", "")
        
        click.secho(f"\nServer: {name}", fg="blue", bold=True)
        click.secho(f"ID: {server_id}", fg="cyan")
        click.secho(f"Description: {description}", fg="cyan")
        
        # Display repository information
        repo = server_data.get("repository", {})
        if repo:
            click.secho("\nRepository:", fg="green")
            click.secho(f"  URL: {repo.get('url', 'N/A')}", fg="cyan")
            click.secho(f"  Source: {repo.get('source', 'N/A')}", fg="cyan")
        
        # Display version information
        version = server_data.get("version_detail", {})
        if version:
            click.secho("\nVersion:", fg="green")
            click.secho(f"  Version: {version.get('version', 'N/A')}", fg="cyan")
            click.secho(f"  Release Date: {version.get('release_date', 'N/A')}", fg="cyan")
            click.secho(f"  Latest: {version.get('is_latest', False)}", fg="cyan")
        
        # Display package information
        packages = server_data.get("packages", [])
        if packages:
            click.secho("\nPackages:", fg="green")
            for i, pkg in enumerate(packages):
                registry_name = pkg.get("registry_name", "unknown")
                name = pkg.get("name", "N/A")
                version = pkg.get("version", "N/A")
                
                click.secho(f"\n  Package {i+1}: {name}", fg="blue")
                click.secho(f"    Registry: {registry_name}", fg="cyan")
                click.secho(f"    Version: {version}", fg="cyan")
                
                # Display arguments
                args = pkg.get("package_arguments", [])
                if args:
                    click.secho("    Arguments:", fg="cyan")
                    for arg in args:
                        arg_desc = arg.get("description", "")
                        arg_value = arg.get("value", "")
                        click.secho(f"      - {arg_desc}: {arg_value}", fg="white")
                
                # Display environment variables
                env_vars = pkg.get("environment_variables", [])
                if env_vars:
                    click.secho("    Environment Variables:", fg="cyan")
                    for env in env_vars:
                        env_name = env.get("name", "")
                        env_desc = env.get("description", "")
                        click.secho(f"      - {env_name}: {env_desc}", fg="white")
                        
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)


@registry.command('install')
@click.argument('identifier')
@click.option('--by-id', is_flag=True, help='Interpret the identifier as a server ID')
def install_registry_server(identifier, by_id):
    """
    Install an MCP server from the registry to VS Code.
    
    IDENTIFIER can be either a server name or ID (with --by-id flag).
    """
    try:
        # Import here to avoid circular imports
        from mcp_installer.registry import (
            MCPRegistryClient, 
            get_registry_url, 
            convert_to_vscode_config, 
            install_server_in_vscode
        )
        
        registry_url = get_registry_url()
        click.secho(f"Using MCP Registry: {registry_url}", fg="green")
        
        client = MCPRegistryClient(registry_url)
        
        # Find server by ID or name
        server_data = None
        if by_id:
            server_id = identifier
            click.secho(f"Looking up server by ID: {server_id}", fg="green")
            server_data = client.get_server(server_id)
        else:
            # Find by name
            click.secho(f"Searching for server by name: {identifier}", fg="green")
            servers = client.search_servers(identifier)
            
            if not servers:
                click.secho(f"No servers found matching '{identifier}'", fg="red")
                return
                
            if len(servers) > 1:
                click.secho(f"Multiple servers found matching '{identifier}':", fg="yellow")
                for i, server in enumerate(servers):
                    click.secho(f"  {i+1}. {server.get('name')} (ID: {server.get('id')})", fg="yellow")
                click.secho("\nPlease use --by-id flag with the specific server ID", fg="yellow")
                return
                
            # Use the first (and only) match
            server_data = client.get_server(servers[0]["id"])
        
        if not server_data:
            click.secho("Server not found", fg="red")
            return
            
        # Convert registry data to VS Code configuration
        server_name = server_data.get("name", "")
        click.secho(f"Installing server: {server_name}", fg="green")
        
        vscode_config = convert_to_vscode_config(server_data)
        
        # Show the configuration
        click.secho("\nVS Code configuration:", fg="green")
        click.secho(json.dumps(vscode_config, indent=2), fg="cyan")
        
        # Confirm installation
        if click.confirm("Do you want to install this server?"):
            # Install the server
            result = install_server_in_vscode(vscode_config)
            click.secho(f"\nServer installed successfully: {server_name}", fg="green")
            
            if result.stdout:
                click.secho("\nOutput:", fg="green")
                click.secho(result.stdout, fg="white")
        else:
            click.secho("Installation cancelled", fg="yellow")
            
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)


if __name__ == "__main__":
    cli()
