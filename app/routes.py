"""
Main application routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.database import db_manager
from app.vault_client import vault_client
from app.auth import require_auth
from app.anti_replay import secure_form
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page with books listing."""
    books = []
    db_error = None
    
    try:
        if db_manager.connect():
            with db_manager.connection.cursor() as cursor:
                cursor.execute("SELECT id, titre, created_at FROM livre ORDER BY created_at DESC")
                books = cursor.fetchall()
                logger.info(f"Retrieved {len(books)} books from database")
        else:
            db_error = "Impossible de se connecter à la base de données"
            
    except Exception as e:
        logger.error(f"Error fetching books: {e}")
        db_error = f"Erreur lors de la récupération des livres: {str(e)}"
    
    return render_template('index.html', books=books, db_error=db_error)

@main_bp.route('/books')
def books():
    """Dedicated books listing page."""
    books = []
    db_error = None
    
    try:
        if db_manager.connect():
            with db_manager.connection.cursor() as cursor:
                cursor.execute("SELECT id, titre, created_at FROM livre ORDER BY created_at DESC")
                books = cursor.fetchall()
                logger.info(f"Retrieved {len(books)} books from database")
        else:
            db_error = "Impossible de se connecter à la base de données"
            
    except Exception as e:
        logger.error(f"Error fetching books: {e}")
        db_error = f"Erreur lors de la récupération des livres: {str(e)}"
    
    return render_template('books.html', books=books, db_error=db_error)

@main_bp.route('/add_book', methods=['GET', 'POST'])
@require_auth
@secure_form('add_book')
def add_book():
    """Add a new book with anti-replay protection."""
    if request.method == 'POST':
        titre = request.form.get('titre', '').strip()
        
        if not titre:
            flash('Le titre du livre est requis.', 'error')
            return render_template('add_book.html')
        
        if len(titre) < 2:
            flash('Le titre doit contenir au moins 2 caractères.', 'error')
            return render_template('add_book.html')
        
        try:
            if db_manager.connect():
                with db_manager.connection.cursor() as cursor:
                    cursor.execute("INSERT INTO livre (titre) VALUES (%s)", (titre,))
                    db_manager.connection.commit()
                    flash(f'Livre "{titre}" ajouté avec succès!', 'success')
                    logger.info(f"Book added: {titre}")
                    return redirect(url_for('main.books'))
            else:
                flash('Erreur de connexion à la base de données.', 'error')
                
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            flash(f'Erreur lors de l\'ajout du livre: {str(e)}', 'error')
    
    return render_template('add_book.html')

@main_bp.route('/health')
def health():
    """Health check endpoint."""
    status = {
        'app': 'running',
        'database': 'disconnected',
        'vault': 'disconnected'
    }
    
    # Check database
    try:
        if db_manager.connect():
            with db_manager.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            status['database'] = 'connected'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        status['database'] = f'error: {str(e)}'
    
    # Check Vault
    try:
        if vault_client.connect():
            status['vault'] = 'connected'
    except Exception as e:
        logger.error(f"Vault health check failed: {e}")
        status['vault'] = f'error: {str(e)}'
    
    return status

@main_bp.route('/vault/status')
def vault_status():
    """Vault status page."""
    vault_status = {
        'connected': False,
        'sealed': None,
        'version': None,
        'error': None
    }
    
    try:
        if vault_client.connect():
            vault_status['connected'] = True
            
            # Get vault status
            client = vault_client.client
            status_response = client.sys.read_health_status()
            vault_status['sealed'] = status_response.get('sealed', True)
            vault_status['version'] = status_response.get('version', 'Unknown')
            
            # Test secret retrieval
            secret = vault_client.get_secret('database/testvault')
            vault_status['secret_access'] = bool(secret)
            
    except Exception as e:
        logger.error(f"Vault status error: {e}")
        vault_status['error'] = str(e)
    
    return render_template('vault_status.html', vault_status=vault_status)

@main_bp.route('/vault/test-connection')
def test_vault_connection():
    """Test Vault connection and database credentials."""
    result = {
        'vault_connected': False,
        'secret_retrieved': False,
        'db_connection_test': False,
        'error': None
    }
    
    try:
        # Test Vault connection
        if vault_client.connect():
            result['vault_connected'] = True
            
            # Test secret retrieval
            secret = vault_client.get_secret('database/testvault')
            if secret:
                result['secret_retrieved'] = True
                
                # Test database connection with Vault credentials
                if db_manager.connect():
                    result['db_connection_test'] = True
                    
    except Exception as e:
        logger.error(f"Vault connection test error: {e}")
        result['error'] = str(e)
    
    return result 