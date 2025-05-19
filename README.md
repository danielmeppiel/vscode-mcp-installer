# vscode-mcp-installer

A CLI tool to verify MCP (Model Context Protocol) servers installed in Visual Studio Code.

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

```zsh
# With activated environment
source .venv/bin/activate
code-mcp list                                          # List all installed MCP servers
code-mcp check mcr.microsoft.com/mcp/server:1.0        # Check specific server(s)

# Without activating
.venv/bin/code-mcp list
.venv/bin/code-mcp check mcr.microsoft.com/mcp/server:1.0
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
- `pytest`, `flake8`, `black` for development
- GitHub Actions for CI/CD
