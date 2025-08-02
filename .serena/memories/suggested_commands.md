# Suggested Commands

## Development Commands

### Package Management
```bash
# Install dependencies (from project root)
uv sync

# Install with optional dependencies
uv sync --extra dev
uv sync --extra agno
uv sync --extra google

# Add new dependency
uv add package_name
```

### Running the Project
```bash
# Start MCP server (main entry point)
uv run serena start-mcp-server

# Start MCP server with specific options
uv run serena start-mcp-server --transport sse --port 9121
uv run serena start-mcp-server --context ide-assistant --project $(pwd)

# Run MCP server via script
uv run python scripts/mcp_server.py

# Run Agno agent (alternative interface)
uv run python scripts/agno_agent.py
```

### Testing
```bash
# Run tests (excludes Java and Rust by default)
uv run pytest test -vv

# Run specific language tests
uv run pytest test -vv -m python
uv run pytest test -vv -m java
uv run pytest test -vv -m rust

# Run all tests
uv run pytest test -vv -m "not slow"
```

### Code Quality
```bash
# Format code
uv run black src scripts test
uv run ruff check --fix src scripts test

# Check formatting and linting
uv run black --check src scripts test
uv run ruff check src scripts test

# Type checking
uv run mypy src/serena

# Combined quality check
uv run poe lint
uv run poe format
uv run poe type-check
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker compose up serena
docker compose up serena-dev

# Build Docker image
docker build -t serena:latest .

# Run with Docker (example)
docker run --rm -i --network host -v /path/to/projects:/workspaces/projects serena:latest serena start-mcp-server --transport stdio
```

### Project Management
```bash
# Generate project configuration
uv run serena project generate-yml

# Index project for faster symbol lookup
uv run serena project index

# Edit Serena configuration
uv run serena config edit

# List available tools
uv run serena tools list
```

### System Commands (Linux)
```bash
# Standard utilities
ls -la          # List files with details
find . -name    # Find files by name
grep -r         # Search in files recursively
git status      # Check git status
git diff        # View changes
cd              # Change directory
```