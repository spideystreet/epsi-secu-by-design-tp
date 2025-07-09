"""
Database connection and operations module
"""
import pymysql
from flask import current_app
import logging
from app.vault_client import vault_client

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.connection = None
    
    def connect(self, password=None):
        """Establish database connection using Vault credentials."""
        try:
            # Try to get credentials from Vault first
            if not password:
                vault_credentials = vault_client.get_database_credentials()
                if vault_credentials:
                    db_host = vault_credentials.get('host', current_app.config['DB_HOST'])
                    db_port = vault_credentials.get('port', current_app.config['DB_PORT'])
                    db_user = vault_credentials.get('username', current_app.config['DB_USER'])
                    db_password = vault_credentials.get('password')
                    db_name = vault_credentials.get('database', current_app.config['DB_NAME'])
                    logger.info("Using database credentials from Vault")
                else:
                    # Fallback to environment config
                    db_host = current_app.config['DB_HOST']
                    db_port = current_app.config['DB_PORT']
                    db_user = current_app.config['DB_USER']
                    db_password = current_app.config.get('DB_PASSWORD', 'initialpass123')
                    db_name = current_app.config['DB_NAME']
                    logger.warning("Vault credentials not available, using environment config")
            else:
                # Use provided password (manual override)
                db_host = current_app.config['DB_HOST']
                db_port = current_app.config['DB_PORT']
                db_user = current_app.config['DB_USER']
                db_password = password
                db_name = current_app.config['DB_NAME']
            
            self.connection = pymysql.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_password,
                database=db_name,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Database connection established to {db_host}:{db_port}")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def get_books(self):
        """Retrieve all books from the livre table."""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id, titre, created_at FROM livre ORDER BY id")
                books = cursor.fetchall()
                logger.info(f"Retrieved {len(books)} books from database")
                return books
        except Exception as e:
            logger.error(f"Error retrieving books: {e}")
            return []
    
    def add_book(self, titre):
        """Add a new book to the livre table."""
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO livre (titre) VALUES (%s)", (titre,))
                self.connection.commit()
                logger.info(f"Added book: {titre}")
                return True
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager() 