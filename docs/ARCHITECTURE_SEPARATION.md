# Architecture Separation - Alert System

## 🏗️ **Correct Architecture**

You're absolutely right! The alert system should be separated into:

### **PUBLIC (Ships with MCP Server)**
- ✅ MCP Tools for alert management (`create_alert_rule`, `list_alerts`, etc.)
- ✅ Database models (`AlertRule`, `Alert`) 
- ✅ Basic alert rule validation and CRUD operations

### **PRIVATE (Our Backend Infrastructure)**
- 🔒 Alert Engine service (`src/monitors_mcp/alert_engine/`)
- 🔒 Notification Manager 
- 🔒 Kubernetes deployments
- 🔒 InfluxDB integration and data polling
- 🔒 Background processing and cooldown management

## 🚀 **Deployment Model**

### **What Users Get (MCP Package)**
```
monitors-mcp/
├── src/monitors_mcp/
│   ├── mcp_server/          # ✅ Ships - Alert management tools
│   ├── models.py            # ✅ Ships - Database schemas
│   ├── auth/                # ✅ Ships - Authentication
│   └── database/            # ✅ Ships - Database management
└── No alert_engine/         # ❌ Does NOT ship
```

### **What We Run (Our Infrastructure)**
```
9bikes-infrastructure/
├── alert-engine/            # 🔒 Our service
├── k8s/                     # 🔒 Our deployments  
├── monitoring/              # 🔒 Our InfluxDB setup
└── notifications/           # 🔒 Our notification channels
```

## 📦 **Package Separation Strategy**

### **Option 1: Move Alert Engine Out**
```bash
# Move alert engine to separate repo/directory
mv src/monitors_mcp/alert_engine/ ../9bikes-alert-engine/
mv k8s/ ../9bikes-alert-engine/
mv docker/ ../9bikes-alert-engine/
```

### **Option 2: Optional Dependencies**
```python
# In pyproject.toml
[project.optional-dependencies]
server = ["influxdb3-python", "aiohttp", "kubernetes"]  # Internal only
```

### **Option 3: Separate Packages**
```
monitors-mcp/          # Public MCP server
monitors-backend/      # Private infrastructure
```

This way:
- **Users** get clean MCP server with alert management
- **We** run the actual alert processing infrastructure
- **Clear separation** between API and implementation

## 🎯 **Benefits**
- ✅ Users don't get unnecessary backend dependencies
- ✅ Our infrastructure stays private
- ✅ Clean separation of concerns
- ✅ Can scale/modify backend without affecting users
- ✅ Simpler deployment for users

## 📋 **Next Steps**
1. Move alert engine to separate infrastructure directory
2. Update MCP server to only include management tools
3. Clean up dependencies in main package
4. Document deployment separation
