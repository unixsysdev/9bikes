# 📦 Package Architecture - Separation of Concerns

## 🎯 **Current Architecture (FIXED)**

We've properly separated the alert system into public and private components:

### **PUBLIC MCP Package** (`src/monitors_mcp/`)
**What ships to users:**
- ✅ **MCP Alert Tools** - 6 tools for alert management via Claude
- ✅ **Database Models** - AlertRule & Alert schemas  
- ✅ **Authentication** - User/session management
- ✅ **Core Dependencies** - Only essential MCP, database, auth libs

**Clean dependencies:**
```toml
dependencies = [
    "mcp>=1.12.3",           # MCP protocol
    "sqlalchemy>=2.0.23",    # Database ORM
    "pymysql>=1.1.0",        # MySQL driver  
    "redis>=5.0.1",          # Session caching
    "cryptography>=41.0.7",  # Secret encryption
    "fastapi>=0.104.0",      # Web framework
    "pydantic>=2.10.6",      # Data validation
    "httpx>=0.25.2",         # HTTP client (for MCP)
    # No Kubernetes, InfluxDB, notification dependencies!
]
```

### **PRIVATE Infrastructure** (`infrastructure/`)
**What we run internally:**
- 🔒 **Alert Engine** - Continuous InfluxDB monitoring & evaluation
- 🔒 **Notification Manager** - Multi-channel delivery (email/Slack/Discord/Teams)
- 🔒 **Kubernetes Deployments** - Production container orchestration
- 🔒 **Docker Images** - Alert engine service containers
- 🔒 **Heavy Dependencies** - Kubernetes, InfluxDB, notification services

**Infrastructure dependencies:**
```txt
influxdb3-python>=0.14.0    # Time-series data queries
kubernetes>=28.1.0           # Container orchestration  
sendgrid>=6.10.0            # Email notifications
aiohttp>=3.12.0             # Health check endpoints
asyncio-mqtt>=0.13.0        # WebSocket monitoring
```

## 🚀 **Deployment Model**

### **For External Users**
```bash
pip install monitors-mcp
# Gets: Clean MCP server with alert management tools
# No backend processing, no infrastructure dependencies
```

### **For 9bikes (Our Infrastructure)**
```bash
cd infrastructure/
./scripts/build_alert_engine.sh deploy
# Deploys: Background alert processing to our Kubernetes cluster
```

## 🔄 **Data Flow**

```
1. User: "Alert me if Bitcoin > $70k" 
   └─> Claude calls create_alert_rule() (PUBLIC MCP tool)
   └─> Saves to MySQL alert_rules table

2. Alert Engine (PRIVATE service):
   └─> Reads alert_rules from MySQL
   └─> Polls InfluxDB for Bitcoin price data
   └─> Evaluates: current_price > $70,000 
   └─> Creates alert record in MySQL
   └─> Sends notifications via SendGrid/Slack

3. User: "Show me recent alerts"
   └─> Claude calls list_alerts() (PUBLIC MCP tool)  
   └─> Reads from MySQL alerts table
   └─> Returns alert history
```

## ✅ **Benefits Achieved**

### **For Users**
- ✅ **Lightweight package** - No unnecessary dependencies
- ✅ **Simple deployment** - Just install MCP server
- ✅ **Clean API** - Only alert management, no backend complexity
- ✅ **Fast installation** - No Kubernetes/InfluxDB/notification deps

### **For 9bikes**  
- ✅ **Private implementation** - Alert processing logic stays internal
- ✅ **Scalable backend** - Can scale/modify infrastructure independently
- ✅ **Secure credentials** - Notification keys stay in our infrastructure
- ✅ **Competitive advantage** - Users get API, we keep implementation

### **For Architecture**
- ✅ **Clear separation** - API layer vs processing layer
- ✅ **Microservices pattern** - Independent services with clean interfaces
- ✅ **Independent scaling** - MCP server vs alert engine scale separately
- ✅ **Maintainable** - Changes to backend don't affect user experience

## 📊 **Package Size Comparison**

### **Before (Monolithic)**
```
monitors-mcp: 50+ dependencies
├── MCP tools ✅
├── Alert engine 🔒  
├── Kubernetes client 🔒
├── InfluxDB client 🔒  
├── Notification services 🔒
└── Health check endpoints 🔒
= BLOATED user package
```

### **After (Separated)**
```
monitors-mcp: ~15 dependencies        infrastructure/: ~20 dependencies
├── MCP tools ✅                     ├── Alert engine 🔒
├── Database models ✅               ├── Kubernetes client 🔒  
├── Authentication ✅                ├── InfluxDB client 🔒
└── Core dependencies ✅             ├── Notification services 🔒
= CLEAN user package                 └── Health check endpoints 🔒
                                     = PRIVATE infrastructure
```

## 🎯 **Result**

**Perfect separation achieved!** 

- **Users** get a clean, focused MCP server for alert management
- **9bikes** runs sophisticated backend infrastructure privately  
- **Both** benefit from clear APIs and independent scaling
- **Architecture** follows microservices best practices

This is the **correct** way to build SaaS products - clean public APIs with private implementation details.
