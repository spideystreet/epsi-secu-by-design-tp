"""
Flask application factory with authentication and session management
"""
import os
import logging
from datetime import timedelta
from flask import Flask, session
from flask_session import Session

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'testvault:'
    app.config['SESSION_FILE_THRESHOLD'] = 100
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)
    
    # TOTP Configuration
    app.config['TOTP_ISSUER'] = 'TestVault Security Platform'
    
    # Initialize session management
    Session(app)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    from app.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    
    # Context processor for authentication status
    @app.context_processor
    def inject_auth_status():
        """Inject authentication status into all templates."""
        return {
            'is_authenticated': session.get('authenticated', False),
            'totp_verified': session.get('totp_verified', False),
            'username': session.get('username'),
            'requires_totp': session.get('requires_totp', False)
        }
    
    # Before request handler for authentication
    @app.before_request
    def check_auth():
        """Check authentication status before each request."""
        from flask import request, redirect, url_for
        
        # Allow access to authentication routes and static files
        if (request.endpoint and 
            (request.endpoint.startswith('auth.') or 
             request.endpoint.startswith('static') or
             request.endpoint in ['main.index', 'main.health', 'main.vault_status'])):
            return
        
        # Check if user is authenticated
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        
        # Check if TOTP verification is required
        if session.get('requires_totp') and not session.get('totp_verified'):
            return redirect(url_for('auth.totp_verify'))
    
    return app 