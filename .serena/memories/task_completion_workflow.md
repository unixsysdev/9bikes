# Task Completion Workflow

## When a Task is Completed

### 1. Code Quality Checks
```bash
# Format code
uv run poe format

# Run linting
uv run poe lint

# Type checking
uv run poe type-check
```

### 2. Testing
```bash
# Run relevant tests
uv run pytest test -vv

# Run specific tests if working on particular features
uv run pytest test -vv -m python  # for Python-specific changes
uv run pytest test -vv -k "test_specific_feature"
```

### 3. Git Operations
```bash
# Check what has changed
git status
git diff

# Stage changes
git add .

# Commit with meaningful message
git commit -m "feat: implement monitor capability registry

- Add MONITOR_CAPABILITIES dictionary for template-driven monitor creation
- Implement MonitorTemplateEngine for guided setup
- Add support for crypto, GitHub, and email monitoring templates
- Include configuration wizards for user guidance"

# Push changes
git push
```

### 4. Documentation Updates
- Update README.md if public API changes
- Update relevant memory files if architecture changes
- Add/update docstrings for new functions
- Update configuration examples if needed

### 5. Configuration Validation
```bash
# Validate configuration files
uv run serena config edit  # Check for syntax errors

# Test MCP server startup
uv run serena start-mcp-server --help
```

### 6. Integration Testing
```bash
# Test MCP server manually if possible
uv run serena start-mcp-server --transport sse --port 9121

# Test with Claude Desktop or other MCP clients
# Verify tools are working correctly
```

## Definition of "Done"
- [ ] Code passes all linting and type checking
- [ ] All relevant tests pass
- [ ] Git changes are committed with clear messages
- [ ] Documentation is updated
- [ ] MCP server starts without errors
- [ ] Integration testing completed (if applicable)
- [ ] Memory files updated (if architecture changed)

## Quality Standards
- Maintain 140-character line limit
- Use type hints for all function parameters and returns
- Follow established naming conventions
- Include error handling for all external interactions
- Use Pydantic models for data validation where appropriate