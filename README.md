# 9bikes Monitor System

A simple monitoring system that lets you talk to Claude to set up and manage data collection.

## What It Does

This is a small project that connects Claude (via MCP - Model Context Protocol) to help you monitor things like:

- API endpoints and their response times
- Cryptocurrency prices from exchanges  
- GitHub repository activity
- Email inbox changes
- Website uptime
- Database query performance

Instead of complex dashboards, you just chat with Claude to create monitors, check data, and get alerts.

## How It Works

1. **Talk to Claude**: "I want to monitor Bitcoin prices from Binance"
2. **Claude helps**: Asks what you need, guides you through setup
3. **System runs**: Creates a monitor that collects data continuously  
4. **Get insights**: Ask Claude "Show me BTC price trends this week"

## Architecture

- **MCP Server**: Connects to Claude for conversational interface
- **Monitor Containers**: Run data collection in Kubernetes
- **Time-Series Storage**: InfluxDB for historical data
- **Alert System**: Email/Slack notifications when thresholds are hit
- **No Web UI**: Everything happens through conversation with Claude

## Current Status

This is an early-stage project. The core framework is working:
- ✅ Authentication and user management
- ✅ MCP connection to Claude
- ✅ Monitor template system
- ✅ Database infrastructure
- 🚧 Monitor deployment (in progress)
- 🚧 Alert processing (in progress)

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (for MySQL, Redis, InfluxDB)
- Claude Desktop or Claude Code

### Setup

1. **Clone and install**:
   ```bash
   git clone https://github.com/unixsysdev/9bikes.git
   cd 9bikes
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -e .
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URLs and API keys
   ```

3. **Start databases** (using existing setup or new containers):
   ```bash
   # MySQL
   docker run -d --name monitors-mysql -p 3306:3306 \
     -e MYSQL_ROOT_PASSWORD=your_password \
     -e MYSQL_DATABASE=monitors_db \
     mysql:8.0
   
   # Redis  
   docker run -d --name monitors-redis -p 6379:6379 \
     redis:7-alpine --requirepass your_redis_password
   ```

4. **Initialize database**:
   ```bash
   export PYTHONPATH=src:$PYTHONPATH
   python -m monitors_mcp.cli setup
   ```

5. **Start MCP server**:
   ```bash
   python -m monitors_mcp.cli start-mcp-server --transport sse --port 9122
   ```

6. **Connect Claude Desktop**:
   Add to your Claude Desktop MCP config:
   ```json
   {
     "mcpServers": {
       "9bikes": {
         "command": "npx",
         "args": ["-y", "mcp-remote", "http://localhost:9122/sse"]
       }
     }
   }
   ```

## Usage Examples

Once connected to Claude:

- **"Set up a monitor for my website"** - Claude guides you through uptime monitoring
- **"Check my Bitcoin monitor data"** - Shows recent price data and trends
- **"Create an alert if my API response time goes above 500ms"** - Sets up alerting
- **"Show me all my monitors"** - Lists active monitors and their status

## Project Structure

```
src/monitors_mcp/           # Main application code
├── auth/                   # Authentication system
├── database/               # Database connections
├── mcp_server/            # MCP protocol implementation  
├── monitors/              # Monitor templates and capabilities
└── models.py              # Database models

infrastructure/             # Private deployment code
├── alert-engine/          # Background alert processing
├── k8s/                   # Kubernetes manifests
└── docker/                # Container definitions

docs/                      # Technical documentation
```

## Contributing

This is a personal project, but if you find bugs or have suggestions:
1. Open an issue describing the problem
2. For code changes, please discuss first in an issue
3. Keep changes small and focused

## Limitations

- Early stage - expect rough edges
- Limited monitor types currently implemented
- Requires technical setup (Docker, environment config)
- Built for personal/small team use, not enterprise scale

## Philosophy

The goal is to make monitoring conversational and approachable. Instead of learning complex monitoring tools, you just talk to Claude about what you want to track. The system handles the technical details behind the scenes.

## License

MIT License - feel free to fork and adapt for your own use.

## Credits

Built on top of excellent open source projects:
- [Serena](https://github.com/oraios/serena) - The MCP framework foundation
- Various language servers for code analysis
- Standard Python ecosystem (FastAPI, SQLAlchemy, etc.)

---

*A humble monitoring system that tries to get out of your way and let you focus on what matters.*
