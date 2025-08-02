# Code Style and Conventions

## Python Style
- **Line Length**: 140 characters (configured in pyproject.toml)
- **Formatter**: Black with target version Python 3.11
- **Linter**: Ruff with extensive rule set
- **Type Checking**: MyPy with strict settings

## Code Quality Settings
- **Disallow untyped definitions**: True
- **Strict optional**: True
- **Check untyped defs**: True
- **No implicit optional**: True

## File Structure
- Source code in `src/` directory
- Tests in `test/` directory
- Scripts in `scripts/` directory
- Configuration templates in `src/serena/resources/`

## Naming Conventions
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Files**: snake_case.py
- **Directories**: lowercase with underscores

## Documentation
- **Docstrings**: Required for public methods (though many D-rules are ignored)
- **Type hints**: Required for all function signatures
- **Comments**: Inline comments for complex logic

## Import Organization
- Standard library imports first
- Third-party imports second
- Local imports last
- Use absolute imports when possible

## Error Handling
- Use specific exception types
- Include meaningful error messages
- Log errors appropriately using the logging framework

## MCP Conventions
- MCP functions decorated with `@mcp_function`
- Return structured dictionaries with consistent keys
- Include error handling for all MCP endpoints
- Validate inputs using Pydantic models when appropriate