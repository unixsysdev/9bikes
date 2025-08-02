# 🔒 Monitoring Infrastructure (Private Backend)

This directory contains the **private backend infrastructure** for the 9bikes monitoring system. 

**⚠️ IMPORTANT: This code does NOT ship with the public MCP server!**

## 🏗️ Architecture Separation

### **PUBLIC (Ships with MCP Package)**
```
src/monitors_mcp/
├── mcp_server/          ✅ Alert management MCP tools
├── models.py            ✅ AlertRule & Alert database models  
├── auth/                ✅ Authentication system
└── database/            ✅ Database management
```

### **PRIVATE (This Infrastructure)**
```
infrastructure/
├── alert-engine/        🔒 Continuous alert evaluation service
├── k8s/                 🔒 Kubernetes deployment manifests
├── docker/              🔒 Docker images and health checks
└── scripts/             🔒 Deployment automation
```

## 🎯 What Each Component Does

### **Public MCP Tools (src/monitors_mcp/)**
- `create_alert_rule()` - Claude creates alert conditions
- `list_alert_rules()` - View user's alert rules
- `list_alerts()` - See recent alerts
- `acknowledge_alert()` - Mark alerts as handled
- `update_alert_rule()` / `delete_alert_rule()` - Manage rules

### **Private Infrastructure (infrastructure/)**
- **Alert Engine** - Polls InfluxDB every 30s, evaluates conditions
- **Notification Manager** - Sends emails/Slack/Discord/Teams notifications  
- **Kubernetes Services** - Production deployment with health checks
- **Health Monitoring** - Service status and readiness probes

## 📦 Deployment Model

### **For Users (Public Package)**
```bash
pip install monitors-mcp
# Gets: MCP server + alert management tools
# No backend dependencies, no infrastructure code
```

### **For Us (Infrastructure)**
```bash
cd infrastructure/
./scripts/build_alert_engine.sh deploy
# Deploys: Alert processing backend to our Kubernetes
```

## 🚀 Quick Infrastructure Setup

### **Prerequisites** 
```bash
# Required services (from main project)
docker run -d --name pstack-mysql ...     # User data & alert rules
docker run -d --name pstack-redis ...     # Session cache & cooldowns  
docker run -d --name pstack-influxdb ...  # Time-series monitor data
```

### **Deploy Alert Engine**
```bash
cd infrastructure/
chmod +x scripts/build_alert_engine.sh
./scripts/build_alert_engine.sh deploy
```

### **Local Development**
```bash
cd infrastructure/
pip install -r requirements.txt
python scripts/start_alert_engine.py
```

## 🔗 Integration Flow

```
1. User creates alert via Claude → MCP tools → MySQL (alert_rules table)
2. Alert Engine reads rules → Polls InfluxDB → Evaluates conditions  
3. Alert triggered → Creates record in MySQL → Sends notifications
4. User sees alert via Claude → MCP tools → Acknowledges via MySQL
```

## 🔒 Security Separation

### **Why This Separation Matters**
- ✅ **Clean Public API** - Users get simple MCP server
- ✅ **Private Infrastructure** - Our alert processing stays internal
- ✅ **No Secret Leakage** - Notification credentials stay private
- ✅ **Scalable** - Can modify backend without affecting users
- ✅ **Maintainable** - Clear separation of concerns

### **What Users Don't Get**
- ❌ Alert engine implementation
- ❌ Kubernetes deployment configs  
- ❌ Notification service credentials
- ❌ Infrastructure dependencies (kubernetes, influxdb3-python, etc.)

## 📋 Files in This Directory

```
infrastructure/
├── alert-engine/
│   ├── engine.py               # Main alert evaluation logic
│   ├── notification_manager.py # Multi-channel notifications
│   └── __init__.py
├── k8s/
│   └── alert-engine-deployment.yaml  # Production K8s deployment
├── docker/
│   ├── alert-engine.Dockerfile       # Service container image
│   └── alert-engine-health.py        # Health check endpoints
├── scripts/
│   ├── start_alert_engine.py         # Local development runner
│   └── build_alert_engine.sh         # Build & deploy automation
└── README.md                          # This file
```

## 🎯 Benefits of This Architecture

1. **Users get clean MCP package** - No infrastructure bloat
2. **Our backend stays private** - Competitive advantage & security
3. **Independent scaling** - Backend can scale without affecting MCP server
4. **Clear responsibilities** - API vs implementation separation
5. **Easier maintenance** - Can update infrastructure without user impact

This follows the **microservices pattern** where the MCP server is the API layer and the alert engine is the processing service.
