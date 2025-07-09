"""
HashiCorp Vault client for secret management
"""
import hvac
import logging
from flask import current_app
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VaultClient:
    """Manages HashiCorp Vault operations for secret storage and retrieval."""
    
    def __init__(self):
        self.client = None
        self._authenticated = False
    
    def connect(self) -> bool:
        """Initialize connection to Vault server."""
        try:
            vault_addr = current_app.config.get('VAULT_ADDR', 'http://localhost:8200')
            vault_token = current_app.config.get('VAULT_TOKEN')
            
            if not vault_token:
                logger.error("VAULT_TOKEN not configured")
                return False
            
            self.client = hvac.Client(url=vault_addr, token=vault_token)
            
            # Test authentication
            if self.client.is_authenticated():
                self._authenticated = True
                logger.info(f"Successfully connected to Vault at {vault_addr}")
                return True
            else:
                logger.error("Vault authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Vault connection failed: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if Vault client is authenticated."""
        return self._authenticated and self.client and self.client.is_authenticated()
    
    def store_secret(self, path: str, secret_data: Dict[str, Any]) -> bool:
        """Store a secret in Vault KV store."""
        if not self.is_authenticated():
            if not self.connect():
                return False
        
        try:
            # Using KV v2 secret engine
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret_data
            )
            logger.info(f"Secret stored successfully at path: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret at {path}: {e}")
            return False
    
    def get_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """Retrieve a secret from Vault KV store."""
        if not self.is_authenticated():
            if not self.connect():
                return None
        
        try:
            # Using KV v2 secret engine
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            secret_data = response['data']['data']
            logger.info(f"Secret retrieved successfully from path: {path}")
            return secret_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret from {path}: {e}")
            return None
    
    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve database credentials from Vault."""
        return self.get_secret('database/testvault')
    
    def initialize_database_secret(self, password: str) -> bool:
        """Initialize database credentials in Vault."""
        db_config = {
            'host': current_app.config.get('DB_HOST', 'localhost'),
            'port': current_app.config.get('DB_PORT', 3307),
            'username': current_app.config.get('DB_USER', 'testvault'),
            'password': password,
            'database': current_app.config.get('DB_NAME', 'testvault')
        }
        
        return self.store_secret('database/testvault', db_config)
    
    def rotate_database_password(self, new_password: str) -> bool:
        """Update database password in Vault."""
        current_config = self.get_database_credentials()
        if not current_config:
            logger.error("Could not retrieve current database config")
            return False
        
        current_config['password'] = new_password
        return self.store_secret('database/testvault', current_config)

# Global Vault client instance
vault_client = VaultClient() 