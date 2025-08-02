# Database and Infrastructure Setup

## 🗄️ Database Configuration

### MySQL Database
- **Container**: `pstack-mysql` (existing container, port 3306)
- **Database**: `monitors_db` (separate from pstack database)  
- **User**: `monitors` / `your_database_password`
- **URL**: `mysql+pymysql://monitors:your_database_password@localhost:3306/monitors_db`

### Redis Cache
- **Container**: `pstack-redis` (existing container, port 6379)
- **Database**: Index `1` (pstack uses index `0` - no conflicts)
- **Password**: `your_redis_password`
- **URL**: `redis://:your_redis_password@localhost:6379/1`

### InfluxDB (Time-Series)
- **Status**: Currently stopped (not needed yet)
- **Will add back**: When implementing actual monitor data storage
- **Purpose**: Store time-series data from running monitors

## 📊 Database Tables Created

```sql
-- Core tables in monitors_db:
users              # User accounts and authentication
sessions           # JWT sessions and tokens  
monitors           # Monitor configurations and status
secrets            # Encrypted user secrets (API keys, etc.)
alert_rules        # User-defined alert conditions
alerts             # Generated alerts and notifications
```

## 🔐 Authentication Flow

1. **Email/OTP**: User provides email → receives OTP via SendGrid
2. **User Creation**: First login creates account in `users` table
3. **Session Management**: JWT tokens stored in `sessions` table
4. **Local Caching**: Sessions cached locally for MCP client persistence
5. **Redis Cache**: Session data cached in Redis for fast validation

## 📧 Email Integration
- **SendGrid API**: Configured and working
- **API Key**: `SG.n3n7pEVSSW-iDEc24...` (69 characters)
- **Email Template**: Branded OTP delivery emails
- **Fallback**: Console output for testing when SendGrid unavailable

## ⚙️ Environment Configuration
```bash
# Core database connections
DATABASE_URL=mysql+pymysql://monitors:your_database_password@localhost:3306/monitors_db
REDIS_URL=redis://:your_redis_password@localhost:6379/1

# Email service
SENDGRID_API_KEY=your_sendgrid_api_key_here

# Security (needs production values)
MASTER_KEY=your-master-encryption-key-here
JWT_SECRET=your-jwt-secret-here
```

## 🧪 Testing Commands
```bash
# Test all connections
venv/bin/python -m monitors_mcp.cli test-connections

# Initialize database
venv/bin/python -m monitors_mcp.cli setup

# Test authentication flow
venv/bin/python test_auth_flow.py

# Check database contents
docker exec pstack-mysql mysql -u monitors -pyour_database_password monitors_db -e "SELECT id, email, tier FROM users;"
```

## ✅ Current Status
- **MySQL**: ✅ Connected, tables created, test user exists
- **Redis**: ✅ Connected, session caching working
- **SendGrid**: ✅ Configured, real email delivery working
- **Authentication**: ✅ Complete flow tested and working

## 🔄 No Conflicts with Pstack
- Different database names (`monitors_db` vs `pstack`)
- Different Redis database indexes (`1` vs `0`)
- Different user credentials (`monitors` vs `pstack`)
- Completely isolated from existing pstack infrastructure