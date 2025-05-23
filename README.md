# vscode-mcp-installer

A tool to verify and install MCP (Model Context Protocol) servers in Visual Studio Code from a MCP Registry. Click one of the buttons below to quickly install the MCP server in VS Code (Badges work for Unix systems - for Windows please read below):

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Docker-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=mcp-installer&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-v%22%2C%22%24%7Benv%3AHOME%7D%2FLibrary%2FApplication%20Support%2FCode%2FUser%2Fsettings.json%3A%2Froot%2F.config%2FCode%2FUser%2Fsettings.json%3Arw%22%2C%22ghcr.io%2Fdanielmeppiel%2Fvscode-mcp-installer%3Alatest%22%5D%7D) [![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Docker-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=mcp-installer&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22-v%22%2C%22%24%7Benv%3AHOME%7D%2FLibrary%2FApplication%20Support%2FCode%20-%20Insiders%2FUser%2Fsettings.json%3A%2Froot%2F.config%2FCode%2FUser%2Fsettings.json%3Arw%22%2C%22ghcr.io%2Fdanielmeppiel%2Fvscode-mcp-installer%3Alatest%22%5D%7D&quality=insiders)

## Table of Contents

- [Setup](#setup)
- [Usage](#usage)
  - [CLI Usage](#cli-usage)
  - [MCP Configuration Files](#mcp-configuration-files)
  - [MCP Server Usage](#mcp-server-usage)
- [Development](#development)
- [Stack](#stack)

## Setup

```zsh
# Clone & enter repo
git clone https://github.com/yourusername/vscode-mcp-installer.git
cd vscode-mcp-installer

# Install with uv (requires Python 3.13+)
uv venv
uv pip install -e .
```

## Usage

### CLI Usage

```zsh
# With activated environment
source .venv/bin/activate
code-mcp list                                          # List all installed MCP servers
code-mcp check mcr.microsoft.com/mcp/server:1.0        # Check specific server(s)

# MCP Registry commands
code-mcp registry list                                 # List available servers from registry
code-mcp registry search redis                         # Search for servers with "redis" as exact name/or inside the description
code-mcp registry show 428785c9-039e-47f6-9636-...     # Show details for a specific server
code-mcp registry install redis-mcp-server             # Install server by name
code-mcp registry install 428785c9... --by-id          # Install server by ID

# MCP Configuration commands
code-mcp config install                                # Install servers from mcp.yml
code-mcp config verify                                 # Verify servers in mcp.yml are installed
code-mcp config init                                   # Create mcp.yml from installed servers

# Without activating
.venv/bin/code-mcp list
.venv/bin/code-mcp check mcr.microsoft.com/mcp/server:1.0
```

By default this server will use the [Azure Community MCP Registry](https://demo.registry.azure-mcp.net). You can set the `MCP_REGISTRY_URL` environment variable to use a different registry:

```zsh
export MCP_REGISTRY_URL=https://your-mcp-registry.example.com
code-mcp registry list
```

### MCP Configuration Files

The `code-mcp` tool supports managing MCP servers using configuration files, similar to dependency management tools like pipenv.

#### Creating a Configuration File

Create a `mcp.yml` file in your project root:

```yaml
version: "1.0"
servers:
  - "mcr.microsoft.com/mcp/python-lsp"
  - "mcr.microsoft.com/mcp/typescript-lsp"
  - "mcr.microsoft.com/mcp/nodejs"
```

#### Installing Servers from Configuration

To install all servers defined in the configuration file:

```bash
code-mcp config install
```

Use the `--no-interactive` flag to skip prompting for environment variables:

```bash
code-mcp config install --no-interactive
```

#### Verifying Configuration

Check if all servers in the configuration file are installed:

```bash
code-mcp config verify
```

#### Generating Configuration from Installed Servers

Create a configuration file from currently installed servers:

```bash
code-mcp config init --output mcp.yml
```

Environment variables for MCP servers will be prompted during installation in interactive mode. Sensitive values like tokens and passwords are hidden during input.

### MCP Server Usage

The tool can also be run as an MCP (Model Context Protocol) server, which allows you to interact with it using MCP clients, including AI assistants like GitHub Copilot.

When running as an MCP server, the following tools are available:

1. `list_servers` - List all MCP servers installed in VS Code
2. `check_servers` - Check if specific MCP servers are installed
3. `list_available_servers` - List available servers from the MCP Registry
4. `search_servers` - Search for MCP servers by name or description
5. `get_server_details` - Get detailed information about a specific server
6. `install_server` - Install an MCP server from the registry to VS Code
7. `get_registry_info` - Show information about the current MCP Registry

#### Running with uv

```zsh
# Start the MCP server (recommended)
uv run mcp mcp_installer/server.py

# Start with MCP Inspector for development/debugging
uv run mcp dev mcp_installer/server.py

# Use a custom registry URL
MCP_REGISTRY_URL=https://custom-registry.example.com uv run mcp mcp_installer/server.py
```

#### Running with Docker

```zsh
# Build the Docker image locally
docker build -t ghcr.io/danielmeppiel/vscode-mcp-installer:latest .

# Run with access to VS Code settings file (macOS)
# Note: rw mount is required for direct settings file modification
docker run -i --rm \
  -v "${HOME}/Library/Application Support/Code/User/settings.json:/root/.config/Code/User/settings.json:rw" \
  ghcr.io/danielmeppiel/vscode-mcp-installer:latest

# Use a custom registry URL with Docker
docker run -i --rm \
  -v "${HOME}/Library/Application Support/Code/User/settings.json:/root/.config/Code/User/settings.json:rw" \
  -e MCP_REGISTRY_URL=https://custom-registry.example.com \
  ghcr.io/danielmeppiel/vscode-mcp-installer:latest

# For Linux
# docker run -i --rm -v "${HOME}/.config/Code/User/settings.json:/root/.config/Code/User/settings.json:ro" ghcr.io/danielmeppiel/vscode-mcp-installer:latest

# For Windows PowerShell
# docker run -i --rm -v "$env:APPDATA\Code\User\settings.json:/root/.config/Code/User/settings.json:ro" ghcr.io/danielmeppiel/vscode-mcp-installer:latest
```

#### Adding to VS Code settings.json

To manually add this MCP server to your VS Code configuration, add the following to your `settings.json` file:

```json
"mcp.servers": {
  "mcp-installer": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "-v",
      "${env:HOME}/Library/Application Support/Code/User/settings.json:/root/.config/Code/User/settings.json:rw",
      "-e",
      "MCP_REGISTRY_URL",
      "ghcr.io/danielmeppiel/vscode-mcp-installer:latest"
    ],
    "env": {
      "MCP_REGISTRY_URL": "https://your-mcp-registry.example.com"
    }
  }
}
```

For Windows, use this configuration:

```json
"mcp.servers": {
  "mcp-installer": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "-v",
      "${env:APPDATA}\\Code\\User\\settings.json:/root/.config/Code/User/settings.json:rw",
      "-e",
      "MCP_REGISTRY_URL",
      "ghcr.io/danielmeppiel/vscode-mcp-installer:latest"
    ],
    "env": {
      "MCP_REGISTRY_URL": "https://your-mcp-registry.example.com"
    }
  }
}
```

#### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_servers` | List all MCP servers installed in VS Code | None |
| `check_servers` | Check if specific MCP servers are installed in VS Code | `servers`: List of server identifiers to check |
| `list_available_servers` | List available MCP servers from the MCP Registry | `limit`: Maximum number of entries to return (default: 30)<br>`cursor`: Pagination cursor for retrieving next set of results |
| `get_server_details` | Get detailed information about a specific MCP server | `server_id`: Unique identifier of the server |
| `search_servers` | Search for MCP servers by name or description | `query`: Search query string (case-insensitive) |
| `install_server` | Install an MCP server from the registry to VS Code | `server_id`: Unique identifier of the server to install<br>`server_name`: Name of the server to search for and install |
| `get_registry_info` | Show information about the current MCP Registry | None |

Example responses:

**list_servers**:
```json
{
  "settings_path": "/path/to/settings.json",
  "count": 2,
  "servers": ["mcr.microsoft.com/mcp/server:1.0", "mcr.microsoft.com/mcp/other:2.0"]
}
```

**check_servers**:
```json
{
  "all_installed": false,
  "installed_servers": ["mcr.microsoft.com/mcp/server:1.0"],
  "missing_servers": ["mcr.microsoft.com/mcp/missing:1.0"]
}
```

**list_available_servers**:
```json
{
  "registry_url": "https://demo.registry.azure-mcp.net",
  "servers": [
    {"id": "428785c9-039e-47f6-9636-...", "name": "redis-mcp-server", "description": "..."},
    {"id": "92a1f82c-8f7d-4a3e-...", "name": "postgres-mcp-server", "description": "..."}
  ],
  "next_cursor": "eyJwayI6IlBBUlRJV..."
}
```

**get_server_details**:
```json
{
  "registry_url": "https://demo.registry.azure-mcp.net",
  "id": "428785c9-039e-47f6-9636-...",
  "name": "redis-mcp-server",
  "description": "MCP server for Redis database operations",
  "version": "1.0.0",
  "vscode_config": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "mcr.microsoft.com/mcp/redis:1.0"]
  }
}
```

**search_servers**:
```json
{
  "registry_url": "https://demo.registry.azure-mcp.net",
  "query": "redis",
  "count": 1,
  "servers": [
    {"id": "428785c9-039e-47f6-9636-...", "name": "redis-mcp-server", "description": "..."}
  ]
}
```

**install_server**:
```json
{
  "success": true,
  "message": "Installed 'redis-mcp-server' successfully",
  "server_id": "428785c9-039e-47f6-9636-...",
  "registry_url": "https://demo.registry.azure-mcp.net",
  "vscode_config": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "mcr.microsoft.com/mcp/redis:1.0"]
  }
}
```

**get_registry_info**:
```json
{
  "registry_url": "https://demo.registry.azure-mcp.net",
  "status": "online",
  "health_check": {"status": "ok", "version": "1.0.0"},
  "message": "MCP Registry is accessible"
}
```
## Development

```zsh
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests, lint and format
pytest
flake8 mcp_installer tests
black mcp_installer tests
```

## Stack
- Python 3.13+
- `click` for CLI
- `mcp` package with `FastMCP` for MCP server functionality
- `pytest`, `flake8`, `black` for development
- GitHub Actions for CI/CD
