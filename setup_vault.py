#!/usr/bin/env python3
"""
Vault Setup Script - Initialize database credentials in Vault
"""
import os
import sys
from dotenv import load_dotenv
from app.vault_client import VaultClient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_vault():
    """Initialize Vault with database credentials."""
    # Load environment variables
    load_dotenv()
    
    # Configuration
    vault_addr = os.getenv('VAULT_ADDR', 'http://localhost:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'myroot')
    db_password = os.getenv('DB_PASSWORD', 'initialpass123')
    
    logger.info(f"Connecting to Vault at {vault_addr}")
    
    # Create a temporary config for the Vault client
    class TempConfig:
        def get(self, key, default=None):
            if key == 'VAULT_ADDR':
                return vault_addr
            elif key == 'VAULT_TOKEN':
                return vault_token
            elif key == 'DB_HOST':
                return os.getenv('DB_HOST', 'localhost')
            elif key == 'DB_PORT':
                return int(os.getenv('DB_PORT', 3307))
            elif key == 'DB_USER':
                return os.getenv('DB_USER', 'testvault')
            elif key == 'DB_NAME':
                return os.getenv('DB_NAME', 'testvault')
            return default
    
    # Mock Flask current_app.config
    import app.vault_client
    original_current_app = getattr(app.vault_client, 'current_app', None)
    
    class MockApp:
        config = TempConfig()
    
    app.vault_client.current_app = MockApp()
    
    try:
        # Initialize Vault client
        vault_client = VaultClient()
        
        # Connect to Vault
        if not vault_client.connect():
            logger.error("Failed to connect to Vault")
            return False
        
        logger.info("✅ Successfully connected to Vault")
        
        # Initialize database credentials in Vault
        logger.info("Storing database credentials in Vault...")
        if vault_client.initialize_database_secret(db_password):
            logger.info("✅ Database credentials stored successfully in Vault")
            
            # Test retrieval
            logger.info("Testing credential retrieval...")
            creds = vault_client.get_database_credentials()
            if creds:
                logger.info(f"✅ Credentials retrieved successfully:")
                logger.info(f"   Host: {creds.get('host')}")
                logger.info(f"   Port: {creds.get('port')}")
                logger.info(f"   User: {creds.get('username')}")
                logger.info(f"   Database: {creds.get('database')}")
                logger.info(f"   Password: {'*' * len(creds.get('password', ''))}")
                return True
            else:
                logger.error("❌ Failed to retrieve stored credentials")
                return False
        else:
            logger.error("❌ Failed to store database credentials")
            return False
            
    except Exception as e:
        logger.error(f"❌ Vault setup failed: {e}")
        return False
    finally:
        # Restore original current_app if it existed
        if original_current_app:
            app.vault_client.current_app = original_current_app

def test_vault_connection():
    """Test basic Vault connectivity."""
    vault_addr = os.getenv('VAULT_ADDR', 'http://localhost:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'myroot')
    
    try:
        import hvac
        client = hvac.Client(url=vault_addr, token=vault_token)
        if client.is_authenticated():
            logger.info(f"✅ Vault is accessible at {vault_addr}")
            return True
        else:
            logger.error(f"❌ Vault authentication failed at {vault_addr}")
            return False
    except Exception as e:
        logger.error(f"❌ Vault connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔐 TestVault Setup - Initializing HashiCorp Vault")
    print("=" * 50)
    
    # Test Vault connection first
    if not test_vault_connection():
        print("\n❌ Vault connection failed. Make sure:")
        print("   1. Docker containers are running: docker compose up -d")
        print("   2. Vault is accessible at http://localhost:8200")
        print("   3. VAULT_TOKEN is set correctly in .env")
        sys.exit(1)
    
    # Setup Vault
    if setup_vault():
        print("\n🎉 Vault setup completed successfully!")
        print("\nNext steps:")
        print("   1. Restart your Flask application")
        print("   2. Test database connection via Vault")
        print("   3. Try rotating the database password")
    else:
        print("\n❌ Vault setup failed!")
        sys.exit(1) 