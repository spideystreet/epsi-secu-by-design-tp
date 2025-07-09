"""
Main application routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.database import db_manager
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
        return {
            'status': 'healthy',
            'database': 'connected',
            'books_count': len(books)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, 500 