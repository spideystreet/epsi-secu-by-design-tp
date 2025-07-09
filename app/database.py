"""
Database connection and operations module
"""
import pymysql
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.connection = None
    
    def connect(self, password=None):
        """Establish database connection."""
        try:
            # Use provided password or get from config (will later come from Vault)
            db_password = password or current_app.config.get('DB_PASSWORD', 'initialpass123')
            
            self.connection = pymysql.connect(
                host=current_app.config['DB_HOST'],
                port=current_app.config['DB_PORT'],
                user=current_app.config['DB_USER'],
                password=db_password,
                database=current_app.config['DB_NAME'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Database connection established")
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