# Tech Stack

## Core Technologies
- **Python 3.11**: Primary development language (required version >=3.11, <3.12)
- **MCP (Model Context Protocol)**: Version 1.12.3 for Claude integration
- **Flask**: Web framework for HTTP endpoints and health checks
- **Pydantic**: Data validation and settings management
- **PyYAML**: Configuration file management

## Database & Storage
- **MySQL**: Primary database for user data and monitor configurations
- **Redis**: Caching and session management
- **InfluxDB**: Time-series database for monitor data storage
- **Vault/Kubernetes Secrets**: Secret management

## Infrastructure
- **Kubernetes**: Container orchestration for monitor deployments
- **Docker**: Containerization (compose.yaml available)
- **UV**: Package management and task runner

## Development Dependencies
- **pytest**: Testing framework with various markers
- **black**: Code formatting
- **ruff**: Linting and code analysis
- **mypy**: Type checking
- **syrupy**: Snapshot testing

## Language Server Support
Built on top of Serena's LSP integration supporting:
- Python (via Pyright/Jedi)
- TypeScript/JavaScript
- PHP, Go, Rust, C#, Java, Elixir, Clojure, C/C++

## Optional Integrations
- **Agno**: Model-agnostic agent framework
- **Google GenAI**: For Gemini model support
- **Anthropic**: For Claude model integration
- **SQLAlchemy**: Database ORM (optional)