# vscode-mcp-installer

A tool to verify MCP (Model Context Protocol) servers installed in Visual Studio Code.

## Table of Contents

- [Setup](#setup)
- [Usage](#usage)
  - [CLI Usage](#cli-usage)
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

# Without activating
.venv/bin/code-mcp list
.venv/bin/code-mcp check mcr.microsoft.com/mcp/server:1.0
```

### MCP Server Usage

The tool can also be run as an MCP (Model Context Protocol) server, which allows you to interact with it using MCP clients, including AI assistants like GitHub Copilot.

#### Running with uv

```zsh
# Start the MCP server (recommended)
uv run mcp mcp_installer/server.py

# Start with MCP Inspector for development/debugging
uv run mcp dev mcp_installer/server.py
```

#### Running with Docker

```zsh
# Build the Docker image locally
docker build -t code-mcp-installer .

# Run with access to VS Code settings file (macOS)
docker run -i --rm \
  -v "${HOME}/Library/Application Support/Code/User/settings.json:/root/.config/Code/User/settings.json:ro" \
  code-mcp-installer

# For Linux
# docker run -i --rm -v "${HOME}/.config/Code/User/settings.json:/root/.config/Code/User/settings.json:ro" code-mcp-installer

# For Windows PowerShell
# docker run -i --rm -v "$env:APPDATA\Code\User\settings.json:/root/.config/Code/User/settings.json:ro" code-mcp-installer
```

#### Adding to VS Code settings.json

To add this MCP server to your VS Code configuration, add the following to your `settings.json` file:

```json
"mcp.servers": {
  "mcp-installer": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "-v",
      "${env:HOME}/Library/Application Support/Code/User/settings.json:/root/.config/Code/User/settings.json:ro",
      "code-mcp-installer"
    ]
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
      "${env:APPDATA}\\Code\\User\\settings.json:/root/.config/Code/User/settings.json:ro",
      "code-mcp-installer"
    ]
  }
}
```

#### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_servers` | List all MCP servers installed in VS Code | None |
| `check_servers` | Check if specific MCP servers are installed in VS Code | `servers`: List of server identifiers to check |

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
