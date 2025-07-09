"""
Main application routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.database import db_manager
from app.vault_client import vault_client
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page displaying all books."""
    books = db_manager.get_books()
    return render_template('index.html', books=books)

@main_bp.route('/add_book', methods=['GET', 'POST'])
def add_book():
    """Add a new book to the database."""
    if request.method == 'POST':
        titre = request.form.get('titre', '').strip()
        
        if not titre:
            flash('Le titre du livre est requis.', 'error')
            return render_template('add_book.html')
        
        if db_manager.add_book(titre):
            flash(f'Livre "{titre}" ajouté avec succès!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Erreur lors de l\'ajout du livre.', 'error')
    
    return render_template('add_book.html')

@main_bp.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Test database connection
        books = db_manager.get_books()
        
        # Test Vault connection
        vault_status = "connected" if vault_client.is_authenticated() else "disconnected"
        vault_credentials = vault_client.get_database_credentials() is not None
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'books_count': len(books),
            'vault': {
                'status': vault_status,
                'credentials_available': vault_credentials
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'database': 'disconnected',
            'vault': {'status': 'unknown'},
            'error': str(e)
        }, 500

@main_bp.route('/vault/status')
def vault_status():
    """Vault status and configuration endpoint."""
    try:
        vault_authenticated = vault_client.is_authenticated()
        credentials = vault_client.get_database_credentials()
        
        status = {
            'vault_authenticated': vault_authenticated,
            'credentials_in_vault': credentials is not None,
            'vault_addr': vault_client.client.url if vault_client.client else None
        }
        
        if credentials:
            # Don't expose the actual password
            safe_credentials = {k: v for k, v in credentials.items() if k != 'password'}
            safe_credentials['password'] = '***PROTECTED***'
            status['credentials_preview'] = safe_credentials
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Vault status check failed: {e}")
        return jsonify({
            'error': str(e),
            'vault_authenticated': False,
            'credentials_in_vault': False
        }), 500

@main_bp.route('/vault/test-connection')
def test_vault_connection():
    """Test Vault connection and database credentials."""
    try:
        # Test Vault connection
        if not vault_client.connect():
            return jsonify({
                'success': False,
                'message': 'Failed to connect to Vault'
            }), 500
        
        # Test database credentials from Vault
        credentials = vault_client.get_database_credentials()
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No database credentials found in Vault'
            }), 404
        
        # Test database connection with Vault credentials
        test_connection = db_manager.connect()
        
        return jsonify({
            'success': True,
            'message': 'Vault and database connection successful',
            'vault_authenticated': True,
            'database_connected': test_connection,
            'credentials_source': 'vault'
        })
        
    except Exception as e:
        logger.error(f"Vault connection test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 