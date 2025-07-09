"""
Main application routes with authentication integration
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.database import db_manager
from app.vault_client import vault_client
from app.auth import require_auth, require_totp
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - accessible to all."""
    return render_template('index.html')

@main_bp.route('/books')
@require_auth
@require_totp
def books():
    """Books listing page - requires full authentication."""
    if not db_manager.connection:
        if not db_manager.connect():
            flash('Erreur de connexion à la base de données.', 'error')
            return render_template('books.html', books=[])
    
    try:
        with db_manager.connection.cursor() as cursor:
            cursor.execute("SELECT id, titre FROM livre ORDER BY titre")
            books_list = cursor.fetchall()
        
        logger.info(f"Retrieved {len(books_list)} books from database")
        return render_template('books.html', books=books_list)
        
    except Exception as e:
        logger.error(f"Error retrieving books: {e}")
        flash('Erreur lors de la récupération des livres.', 'error')
        return render_template('books.html', books=[])

@main_bp.route('/add_book', methods=['POST'])
@require_auth
@require_totp
def add_book():
    """Add a new book - requires full authentication."""
    titre = request.form.get('titre', '').strip()
    
    if not titre:
        flash('Le titre du livre est requis.', 'error')
        return redirect(url_for('main.books'))
    
    if not db_manager.connection:
        if not db_manager.connect():
            flash('Erreur de connexion à la base de données.', 'error')
            return redirect(url_for('main.books'))
    
    try:
        with db_manager.connection.cursor() as cursor:
            cursor.execute("INSERT INTO livre (titre) VALUES (%s)", (titre,))
            db_manager.connection.commit()
        
        flash(f'Livre "{titre}" ajouté avec succès!', 'success')
        logger.info(f"Book added: {titre}")
        
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        flash('Erreur lors de l\'ajout du livre.', 'error')
        db_manager.connection.rollback()
    
    return redirect(url_for('main.books'))

@main_bp.route('/health')
def health():
    """Health check endpoint - accessible to all."""
    # Database status
    db_status = "connected" if db_manager.test_connection() else "disconnected"
    
    # Vault status
    vault_status = "connected" if vault_client.test_connection() else "disconnected"
    
    # Application status
    app_status = "healthy" if db_status == "connected" else "unhealthy"
    
    status_data = {
        "status": app_status,
        "database": db_status,
        "vault": vault_status,
        "timestamp": "2025-01-09T15:30:00Z"
    }
    
    return jsonify(status_data)

@main_bp.route('/vault/status')
@require_auth
def vault_status():
    """Vault status page - requires authentication."""
    vault_connected = vault_client.test_connection()
    
    vault_info = {
        'connected': vault_connected,
        'url': vault_client.url,
        'status': 'Connecté' if vault_connected else 'Déconnecté'
    }
    
    # Test secret retrieval
    test_result = None
    if vault_connected:
        try:
            secret = vault_client.get_secret('database/testvault')
            test_result = {
                'success': secret is not None,
                'message': 'Secret récupéré avec succès' if secret else 'Secret non trouvé'
            }
        except Exception as e:
            test_result = {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }
    
    return render_template('vault_status.html', vault_info=vault_info, test_result=test_result)

@main_bp.route('/vault/test-connection')
@require_auth
def vault_test_connection():
    """Test Vault connection - requires authentication."""
    vault_connected = vault_client.test_connection()
    
    result = {
        'vault_connected': vault_connected,
        'vault_url': vault_client.url
    }
    
    if vault_connected:
        # Test database credentials retrieval
        try:
            db_credentials = vault_client.get_secret('database/testvault')
            if db_credentials:
                result['db_credentials_available'] = True
                result['message'] = 'Vault connecté et credentials disponibles'
                
                # Test database connection with Vault credentials
                db_test = db_manager.test_connection()
                result['db_connection_test'] = db_test
                result['db_status'] = 'connected' if db_test else 'disconnected'
            else:
                result['db_credentials_available'] = False
                result['message'] = 'Vault connecté mais credentials manquants'
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f'Erreur lors du test Vault: {str(e)}'
    else:
        result['message'] = 'Impossible de se connecter à Vault'
    
    return jsonify(result) 