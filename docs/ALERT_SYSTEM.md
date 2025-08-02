# Alert System Documentation

## 🚨 Overview

The Claude Monitor System now includes a **complete alerting infrastructure** that runs independently in Kubernetes, separate from Claude sessions and the MCP server. This enables 24/7 continuous alert evaluation and multi-channel notifications.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitor Pod   │───▶│    InfluxDB      │◀───│  Alert Engine   │
│  (Collects Data)│    │ (Time Series DB) │    │   (Evaluates)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    MySQL DB     │◀───│ Notification Svc │◀───│   Alert Rules   │
│  (Alert Records)│    │  (Delivers Msgs) │    │   (Conditions)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Key Components**

1. **Alert Engine** (`src/monitors_mcp/alert_engine/engine.py`)
   - Continuous background service
   - Polls InfluxDB every 30 seconds
   - Evaluates alert rules against monitor data
   - Respects cooldown periods
   - Generates Alert records

2. **Notification Manager** (`src/monitors_mcp/alert_engine/notification_manager.py`)
   - Multi-channel delivery system
   - Email via SendGrid
   - Slack, Discord, Teams webhooks
   - Delivery status tracking

3. **MCP Alert Tools** (in `src/monitors_mcp/mcp_server/__init__.py`)
   - `create_alert_rule()` - Define alert conditions
   - `list_alert_rules()` - View all rules
   - `list_alerts()` - See recent alerts
   - `acknowledge_alert()` - Mark alerts as handled
   - `update_alert_rule()` - Modify existing rules
   - `delete_alert_rule()` - Remove rules

## 🚀 Deployment

### **Kubernetes Deployment**
```bash
# Build the alert engine image
./scripts/build_alert_engine.sh

# Deploy to Kubernetes
./scripts/build_alert_engine.sh deploy

# Check status
kubectl get pods -n monitors
kubectl logs -n monitors -l app=alert-engine
```

### **Local Development**
```bash
# Start alert engine locally
venv/bin/python -m monitors_mcp.cli start-alert-engine

# Or use the standalone script
python scripts/start_alert_engine.py
```

## 📋 Usage Examples

### **1. Create Alert Rules via Claude**

```
"Create an alert rule for my Bitcoin monitor. Alert me if the price goes above $60,000."

Claude uses: create_alert_rule(
  monitor_id="mon_abc123",
  title="Bitcoin High Price Alert",
  condition={
    "type": "threshold",
    "field": "price", 
    "operator": ">",
    "value": 60000,
    "aggregation": "latest"
  },
  severity="medium",
  cooldown_minutes=15
)
```

### **2. Website Uptime Monitoring**

```
"Alert me if my website goes down."

Claude uses: create_alert_rule(
  monitor_id="mon_def456",
  title="Website Down Alert",
  condition={
    "type": "threshold",
    "field": "is_up",
    "operator": "==",
    "value": 0,
    "aggregation": "latest"
  },
  severity="critical",
  cooldown_minutes=5
)
```

### **3. View Recent Alerts**

```
"Show me recent alerts for my monitors."

Claude uses: list_alerts(limit=20)
```

## 🔧 Alert Rule Conditions

### **Condition Format**
```json
{
  "type": "threshold",
  "field": "price",           // Field to monitor
  "operator": ">",            // >, <, >=, <=, ==, !=
  "value": 50000,            // Threshold value
  "aggregation": "latest"     // latest, avg, max, min
}
```

### **Common Examples**

**Price Alerts:**
```json
{
  "type": "threshold",
  "field": "price",
  "operator": ">",
  "value": 70000,
  "aggregation": "latest"
}
```

**Response Time Alerts:**
```json
{
  "type": "threshold", 
  "field": "response_time",
  "operator": ">",
  "value": 5000,
  "aggregation": "avg"
}
```

**Uptime Alerts:**
```json
{
  "type": "threshold",
  "field": "is_up", 
  "operator": "==",
  "value": 0,
  "aggregation": "latest"
}
```

## 📧 Notification Channels

### **Email Notifications**
- **Provider**: SendGrid
- **Format**: Rich HTML emails with alert details
- **Always enabled**: Default notification method

### **Slack Integration**
```bash
# Set webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Or add to Kubernetes secrets
kubectl patch secret monitors-secrets -n monitors -p '{"stringData":{"slack-webhook-url":"https://hooks.slack.com/..."}}'
```

### **Discord Integration**
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/WEBHOOK"
```

### **Microsoft Teams Integration**
```bash
export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/YOUR/WEBHOOK"
```

## 🔄 Alert Lifecycle

### **1. Rule Evaluation**
- Alert Engine queries InfluxDB every 30 seconds
- Evaluates all active alert rules
- Checks cooldown periods to prevent spam

### **2. Alert Generation**
- Creates Alert record in MySQL
- Includes trigger data and context
- Sets status to "pending"

### **3. Notification Delivery**
- Sends notifications via configured channels
- Updates delivery status in database
- Tracks successful/failed deliveries

### **4. Alert Management**
- Users can acknowledge alerts via Claude
- Acknowledged alerts marked as "acknowledged"
- Alert history preserved for analysis

## 🛠️ Configuration

### **Environment Variables**
```bash
# Core settings
ALERT_EVALUATION_INTERVAL=30      # Seconds between evaluations
LOG_LEVEL=INFO                    # Logging level

# Database connections
DATABASE_URL=mysql+pymysql://...
REDIS_URL=redis://...
INFLUXDB_URL=http://...
INFLUXDB_TOKEN=...

# Notification services
SENDGRID_API_KEY=SG.xxx
SLACK_WEBHOOK_URL=https://...     # Optional
DISCORD_WEBHOOK_URL=https://...   # Optional
TEAMS_WEBHOOK_URL=https://...     # Optional
```

### **Kubernetes Resources**
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi" 
    cpu: "500m"
```

## 🔍 Monitoring & Health Checks

### **Health Endpoints**
- `GET /health` - Liveness probe
- `GET /ready` - Readiness probe (checks DB/Redis)
- `GET /status` - Extended status information

### **Kubernetes Probes**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
```

### **Log Monitoring**
```bash
# View alert engine logs
kubectl logs -n monitors -l app=alert-engine -f

# Check specific pod
kubectl logs -n monitors alert-engine-xxxx-xxxx
```

## 🎯 Alert Severities

- **`low`** - Informational alerts, minor issues
- **`medium`** - Warning conditions that should be addressed
- **`high`** - Significant issues requiring attention
- **`critical`** - Service-affecting problems requiring immediate action

## 📊 Sample Alert Rules

### **Crypto Trading**
```json
{
  "title": "Bitcoin Price Spike",
  "condition": {
    "type": "threshold",
    "field": "price",
    "operator": ">", 
    "value": 75000,
    "aggregation": "latest"
  },
  "severity": "high",
  "cooldown_minutes": 30
}
```

### **Website Monitoring**
```json
{
  "title": "High Response Time",
  "condition": {
    "type": "threshold",
    "field": "response_time",
    "operator": ">",
    "value": 3000,
    "aggregation": "avg"
  },
  "severity": "medium", 
  "cooldown_minutes": 10
}
```

### **API Monitoring**
```json
{
  "title": "API Error Rate",
  "condition": {
    "type": "threshold",
    "field": "status_code",
    "operator": ">=",
    "value": 500,
    "aggregation": "latest"
  },
  "severity": "critical",
  "cooldown_minutes": 5
}
```

## 🔧 Troubleshooting

### **Common Issues**

**Alert Engine Not Starting:**
```bash
# Check database connections
kubectl exec -n monitors deploy/alert-engine -- python -c "
from src.monitors_mcp.database import db_manager
print(db_manager.test_connections())
"
```

**No Alerts Being Generated:**
```bash
# Check if rules exist
kubectl logs -n monitors -l app=alert-engine | grep "active alert rules"

# Verify monitor data
kubectl logs -n monitors -l app=alert-engine | grep "recent data"
```

**Notifications Not Delivered:**
```bash
# Check SendGrid configuration
kubectl get secret monitors-secrets -n monitors -o yaml | grep sendgrid

# Verify webhook URLs
kubectl logs -n monitors -l app=alert-engine | grep "notification"
```

## 🚀 Next Steps

### **Current Status: ✅ FULLY IMPLEMENTED**
- ✅ Alert Engine service
- ✅ Notification delivery system
- ✅ MCP tools for alert management
- ✅ Kubernetes deployment
- ✅ Health checks and monitoring

### **Future Enhancements**
- [ ] Alert templates for common scenarios
- [ ] Escalation policies (if not acknowledged in X minutes)
- [ ] Alert correlation and grouping
- [ ] SMS notifications via Twilio
- [ ] Push notifications for mobile apps
- [ ] Alert analytics and reporting
- [ ] Custom notification templates
- [ ] Alert scheduling (business hours only)

## 💡 Usage Tips

1. **Start with medium severity** and adjust based on alert frequency
2. **Use appropriate cooldowns** to avoid alert fatigue
3. **Test alert rules** with temporary low thresholds
4. **Acknowledge alerts promptly** to maintain clean alert history
5. **Monitor alert engine logs** to ensure smooth operation
6. **Set up multiple notification channels** for redundancy

The alert system is now **production-ready** and provides comprehensive monitoring capabilities with reliable notification delivery! 🎉
