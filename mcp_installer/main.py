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


if __name__ == "__main__":
    cli()
