"""
TestVault - Secure Flask Application with Vault Integration
"""
from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    """Create and configure the Flask application."""
    load_dotenv()
    
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    app.config['DB_PORT'] = int(os.getenv('DB_PORT', 3306))
    app.config['DB_USER'] = os.getenv('DB_USER', 'testvault')
    app.config['DB_NAME'] = os.getenv('DB_NAME', 'testvault')
    app.config['VAULT_ADDR'] = os.getenv('VAULT_ADDR', 'http://localhost:8200')
    app.config['VAULT_TOKEN'] = os.getenv('VAULT_TOKEN', 'myroot')
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 