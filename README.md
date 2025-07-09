# TestVault - Secure Book Management System 🔐

A comprehensive Flask application demonstrating enterprise-grade security features including HashiCorp Vault integration, TOTP authentication, captcha protection, and anti-replay mechanisms.

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone <your-repo>
cd epsi-secu-by-design-tp

# 2. Start infrastructure
docker-compose up -d

# 3. Setup Python environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run application
python run.py
```

🌐 **Access**: http://localhost:8080 (or 5000 if available)

## 📋 Security Features Overview

### ✅ Implemented Features

| Feature | Status | Description |
|---------|--------|-------------|
| **HashiCorp Vault Integration** | ✅ | Secure credential storage and rotation |
| **TOTP (2FA)** | ✅ | Time-based One-Time Password authentication |
| **Server-side Captcha** | ✅ | Anti-bot protection with image generation |
| **Anti-replay Protection** | ✅ | CSRF tokens, nonces, and timing validation |

### 🛡️ Security Layers

1. **Authentication System**
   - Username/password authentication
   - TOTP 2FA with QR code setup
   - Backup codes for account recovery
   - Session management with secure tokens

2. **Anti-Bot Protection**
   - Server-generated captcha (PIL + CSS fallback)
   - User-Agent analysis
   - Request timing validation
   - Rate limiting per IP address

3. **Anti-Replay Protection**
   - CSRF token validation
   - Request nonce system
   - Form timing validation
   - Duplicate submission prevention

4. **Infrastructure Security**
   - HashiCorp Vault for secrets management
   - Database credential rotation
   - Secure session storage
   - Environment-based configuration

## 🏗️ Project Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask App     │───▶│    MariaDB      │    │  HashiCorp      │
│   (Port 8080)   │    │   (Port 3306)   │    │     Vault       │
│                 │    │                 │    │   (Port 8200)   │
│   • Auth System │    │   • Users       │    │   • DB Creds    │
│   • TOTP        │    │   • Books       │    │   • Secrets     │
│   • Captcha     │    │   • Sessions    │    │   • Rotation    │
│   • Anti-replay │    │   • Rate Limits │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📚 Detailed Setup Guide

### Prerequisites

- **Docker & Docker Compose** (for infrastructure)
- **Python 3.8+** with pip
- **Git** for cloning

### Step 1: Infrastructure Setup

```bash
# Start MariaDB and HashiCorp Vault
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Expected output:**
```
NAME                     COMMAND                  STATUS
testvault-mariadb-1     "docker-entrypoint.s…"   Up
testvault-vault-1       "docker-entrypoint.s…"   Up
```

### Step 2: Vault Configuration

```bash
# Initialize Vault (first time only)
python setup_vault.py

# This script will:
# - Initialize Vault with unseal keys
# - Create AppRole authentication
# - Store database credentials
# - Configure secret rotation
```

### Step 3: Database Setup

The application automatically creates required tables:
- `users` - User accounts and TOTP settings
- `livre` - Book collection
- `rate_limits` - Anti-abuse protection
- `sessions` - Secure session management

### Step 4: Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Application Launch

```bash
# Start Flask application
python run.py

# The app will auto-detect available ports:
# - Tries port 5000 first
# - Falls back to 8080 if 5000 is occupied (common on macOS)
```

## 🎮 User Guide

### Creating Your First Account

1. **Navigate** to the registration page
2. **Fill out** the form with unique username and email
3. **Complete** the captcha challenge
4. **Submit** - your account is created!

### Setting Up 2FA (Recommended)

1. **Login** to your account
2. **Go to Profile** → "Setup TOTP"
3. **Scan QR code** with authenticator app (Google Authenticator, Authy, etc.)
4. **Enter verification code** to activate
5. **Save backup codes** securely

### Adding Books

1. **Login** to your account
2. **Navigate** to "Add Book"
3. **Enter book title** (minimum 2 characters)
4. **Submit** - protected by anti-replay mechanisms

## 🔧 Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Application Settings
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-super-secret-key-here

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=testvault
DB_NAME=testvault

# Vault Configuration
VAULT_ADDR=http://localhost:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id

# Security Settings
STRICT_ANTI_REPLAY=False  # Set to True for production
```

### Security Configurations

**Anti-Replay Settings:**
```python
# In app/anti_replay.py
token_expiry = 3600      # CSRF token validity (1 hour)
nonce_window = 300       # Request nonce window (5 minutes)
min_form_time = 2        # Minimum form fill time (seconds)
max_form_time = 1800     # Maximum form validity (30 minutes)
```

**Rate Limiting:**
```python
# Login attempts: 5 per 15 minutes per IP
# Registration: 3 per 60 minutes per IP
# TOTP attempts: 10 per 15 minutes per user
```

## 🧪 Testing & Verification

### Health Checks

```bash
# Application health
curl http://localhost:8080/health

# Vault status
curl http://localhost:8080/vault/status

# Database connection test
curl http://localhost:8080/vault/test-connection
```

### Security Testing

1. **CSRF Protection Test:**
   ```bash
   # This should fail (missing CSRF token)
   curl -X POST http://localhost:8080/auth/login \
        -d "username=test&password=test"
   ```

2. **Rate Limiting Test:**
   ```bash
   # Multiple rapid requests should be blocked
   for i in {1..10}; do
     curl -X POST http://localhost:8080/auth/login \
          -d "username=test&password=wrong" &
   done
   ```

3. **Captcha Test:**
   - Try submitting forms without captcha
   - Verify image/HTML captcha generation
   - Test captcha refresh functionality

## 📊 API Endpoints

### Public Endpoints
- `GET /` - Home page with book listing
- `GET /health` - Application health check
- `GET /vault/status` - Vault connection status

### Authentication Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout
- `POST /auth/totp/verify` - TOTP verification
- `GET /auth/totp/setup` - TOTP configuration

### Protected Endpoints (Require Auth)
- `GET /books` - Books listing
- `POST /add_book` - Add new book
- `GET /auth/profile` - User profile

### API Endpoints
- `GET /auth/api/check-username` - Username availability
- `POST /auth/api/captcha/refresh` - Generate new captcha
- `POST /auth/api/captcha/validate` - Validate captcha
- `GET /auth/api/totp/status` - TOTP status

## 🛠️ Development

### Project Structure

```
epsi-secu-by-design-tp/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── routes.py            # Main routes
│   ├── auth_routes.py       # Authentication routes
│   ├── auth.py              # Auth service
│   ├── database.py          # Database manager
│   ├── vault_client.py      # Vault integration
│   ├── captcha.py           # Captcha system
│   ├── anti_replay.py       # Anti-replay protection
│   └── templates/           # Jinja2 templates
├── sql/                     # Database schemas
├── docker-compose.yml       # Infrastructure
├── setup_vault.py          # Vault initialization
├── run.py                  # Application entry point
└── requirements.txt        # Python dependencies
```

### Adding New Features

1. **New Routes**: Add to `app/routes.py` or `app/auth_routes.py`
2. **Security Protection**: Use `@secure_form()` decorator
3. **Database**: Add tables to `sql/` directory
4. **Templates**: Create in `app/templates/`

### Database Migrations

```bash
# Connect to MariaDB
docker exec -it testvault-mariadb-1 mysql -u testvault -p testvault

# Run SQL from sql/ directory
source /path/to/sql/new_migration.sql;
```

## 🚨 Troubleshooting

### Common Issues

**Port 5000 Already in Use (macOS):**
```bash
# Disable AirPlay Receiver in System Preferences
# OR the app will automatically use port 8080
```

**Database Connection Failed:**
```bash
# Check if MariaDB is running
docker-compose ps

# Restart if needed
docker-compose restart mariadb

# Check logs
docker-compose logs mariadb
```

**Vault Sealed/Unavailable:**
```bash
# Re-run Vault setup
python setup_vault.py

# Check Vault logs
docker-compose logs vault
```

**PIL/Pillow Issues:**
```bash
# The app includes fallback CSS captcha
# But to use image captcha:
pip install --upgrade Pillow
```

### Debug Mode

```bash
# Enable detailed logging
export FLASK_ENV=development
export DEBUG=True
python run.py
```

### Reset Everything

```bash
# Stop services
docker-compose down -v

# Remove data
docker volume prune

# Restart fresh
docker-compose up -d
python setup_vault.py
```

## 🔒 Security Best Practices

### Production Deployment

1. **Environment Variables:**
   ```env
   FLASK_ENV=production
   DEBUG=False
   STRICT_ANTI_REPLAY=True
   ```

2. **Reverse Proxy:**
   - Use Nginx/Apache with HTTPS
   - Configure rate limiting
   - Hide server headers

3. **Vault Security:**
   - Use TLS for Vault communication
   - Rotate AppRole credentials regularly
   - Monitor Vault audit logs

4. **Database Security:**
   - Use connection pooling
   - Enable SSL connections
   - Regular credential rotation

### Monitoring

- **Application Logs**: Check Flask logs for security events
- **Vault Audit**: Monitor Vault access patterns
- **Database Logs**: Watch for suspicious queries
- **Rate Limiting**: Monitor blocked requests

## 📖 Educational Value

This project demonstrates:

- **Real-world Security**: Enterprise security patterns
- **Integration Skills**: Multiple technologies working together
- **Best Practices**: Industry-standard implementations
- **Defensive Programming**: Multiple layers of protection

Perfect for learning:
- Web application security
- Identity and access management
- Secret management
- Defense in depth strategies

## 👥 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-security-feature`
3. Commit changes: `git commit -am 'Add new security feature'`
4. Push branch: `git push origin feature/new-security-feature`
5. Submit pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🎓 EPSI Security by Design TP Project**  
**All security features implemented and tested**