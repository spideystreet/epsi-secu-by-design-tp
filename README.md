# TestVault - Secure Book Management System

A secure Flask application demonstrating HashiCorp Vault integration with advanced security features including TOTP, captcha, and anti-replay protection.

## 🎯 Project Objectives

- **Database**: MariaDB with secure connection handling
- **Vault Integration**: HashiCorp Vault for credential management (8 points)
- **TOTP**: Time-based One-Time Password for 2FA (5 points)
- **Captcha**: Server-side captcha protection (5 points)
- **Anti-replay**: Request replay attack prevention (2 points)

**Total Score: 20 points**

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+

### 1. Clone and Setup
```bash
git clone <your-repo>
cd epsi-secu-by-design-tp
```

### 2. Start Infrastructure
```bash
docker-compose up -d
```

This starts:
- MariaDB on port 3306
- HashiCorp Vault on port 8200

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python run.py
```

Access the application at: http://localhost:5000

## 📋 Features

### Current Features ✅
- ✅ MariaDB database with `livre` table
- ✅ Basic Flask application
- ✅ Book listing and adding functionality
- ✅ Docker Compose setup
- ✅ Health check endpoint

### In Development 🚧
- 🚧 Vault integration for credential storage
- 🚧 User authentication system
- 🚧 TOTP implementation
- 🚧 Server-side captcha
- 🚧 Anti-replay protection

## 🗄️ Database Schema

```sql
CREATE TABLE livre (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Configuration

Environment variables in `.env`:
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME` - Database connection
- `DB_PASSWORD` - Will be moved to Vault
- `VAULT_ADDR`, `VAULT_TOKEN` - Vault connection
- `FLASK_ENV`, `SECRET_KEY` - Application settings

## 🧪 Testing

### Health Check
```bash
curl http://localhost:5000/health
```

### Database Test
```bash
curl http://localhost:5000/
```

## 🔒 Security Features (Coming Soon)

1. **TOTP (5 points)**: Two-factor authentication
2. **Captcha (5 points)**: Server-side validation
3. **Anti-replay (2 points)**: Request replay prevention
4. **Vault Integration (8 points)**: Secure credential storage

## 📚 API Endpoints

- `GET /` - List all books
- `GET /add_book` - Show add book form
- `POST /add_book` - Add new book
- `GET /health` - Health check

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask App     │───▶│    MariaDB      │    │  HashiCorp      │
│   (Port 5000)   │    │   (Port 3306)   │    │     Vault       │
│                 │    │                 │    │   (Port 8200)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 👥 Development Team

EPSI Security by Design TP Project