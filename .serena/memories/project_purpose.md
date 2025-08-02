# Project Purpose

This is the **9bikes_mcp** project, which aims to build a **Claude Monitor System** - a distributed monitoring system that enables Claude to orchestrate long-running data collection processes via MCP (Model Context Protocol).

## Key Features
- **MCP-based Architecture**: Uses Model Context Protocol for Claude integration
- **Secure Credential Management**: Built-in secret storage and encryption
- **Multi-tenant Isolation**: Support for multiple users and projects
- **Intelligent Alert Routing**: Smart notification system
- **Conversational Interface**: All interaction happens through Claude conversations
- **Monitor Templates**: Pre-built monitor types for common use cases

## Foundation
The project builds upon the existing **Serena** codebase in the `serena/` directory, which is a powerful coding agent toolkit that provides:
- MCP server implementation
- Semantic code analysis capabilities
- LSP-based language server integration
- Tool-based agent framework

## Goals
1. Create a monitoring system that Claude can control conversationally
2. Support various monitor types (API polling, WebSocket streams, webhooks)
3. Provide secure secret management for API keys and credentials
4. Enable intelligent alerting and data visualization
5. Maintain conversational control without external UIs

The system is designed to be "Claude-first" - no dashboards or web UIs, everything managed through natural language conversation with Claude.