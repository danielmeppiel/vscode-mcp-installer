FROM ghcr.io/astral-sh/uv:0.7.5-python3.13-bookworm

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app
RUN uv sync --frozen

# Set environment for MCP communication
ENV PYTHONUNBUFFERED=1

# Install package with UV (using --system flag)
RUN uv pip install --system -e .

CMD ["uv", "run", "mcp_installer/server.py"]