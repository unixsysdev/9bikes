# Codebase Structure

## Root Directory Structure
```
/root/Workspace/9bikes_mcp/
├── README.md                    # Main project documentation and RFC
├── serena/                      # Serena framework (foundation)
└── .serena/                     # Serena configuration and memories
```

## Serena Framework Structure
```
serena/
├── src/
│   ├── serena/                  # Main Serena package
│   │   ├── mcp.py              # MCP server implementation
│   │   ├── agent.py            # Agent framework
│   │   ├── cli.py              # Command-line interface
│   │   ├── tools/              # Tool implementations
│   │   └── resources/          # Configuration templates
│   ├── solidlsp/               # Language server protocol integration
│   └── interprompt/            # Prompt management
├── test/                       # Test suite
├── scripts/                    # Utility scripts
│   ├── mcp_server.py          # MCP server entry point
│   └── agno_agent.py          # Agno agent entry point
├── pyproject.toml             # Python project configuration
├── compose.yaml               # Docker composition
└── README.md                  # Serena documentation
```

## Key Components

### MCP Server (`src/serena/mcp.py`)
- `SerenaMCPFactory`: Main MCP server factory
- `SerenaMCPRequestContext`: Request handling context
- Integration with Serena's tool system

### Agent Framework (`src/serena/agent.py`)
- Base agent implementation
- Tool orchestration
- Session management

### Tools (`src/serena/tools/`)
- `file_tools.py`: File system operations
- `symbol_tools.py`: Code symbol manipulation
- `cmd_tools.py`: Shell command execution
- `memory_tools.py`: Memory management
- `workflow_tools.py`: Workflow coordination

### Language Server Integration (`src/solidlsp/`)
- LSP protocol handlers
- Language-specific server implementations
- Symbol analysis and code understanding

## Configuration Structure
```
.serena/
├── serena_config.yml           # Global Serena configuration
├── project.yml                 # Project-specific configuration
└── memories/                   # Project memories
    ├── project_purpose.md
    ├── tech_stack.md
    └── ...
```

## Important Files
- `pyproject.toml`: Dependencies, build configuration, tool settings
- `compose.yaml`: Docker deployment configuration
- `scripts/mcp_server.py`: Main entry point for MCP server
- `src/serena/cli.py`: Command-line interface implementation