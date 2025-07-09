"""
Authentication routes for login, registration, and TOTP
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from app.auth import AuthService, TOTPService, create_session, destroy_session, require_auth
from app.captcha import captcha_service, require_captcha, detect_bot_behavior, mark_form_start, check_rate_limit, ensure_rate_limits_table
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Ensure rate limits table exists
ensure_rate_limits_table()

@auth_bp.route('/register', methods=['GET', 'POST'])
@require_captcha
def register():
    """User registration with captcha protection."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Check for bot behavior
        if detect_bot_behavior(request):
            flash('Activité suspecte détectée. Veuillez réessayer plus tard.', 'error')
            return render_template('auth/register.html')
        
        # Check rate limiting
        identifier = request.remote_addr
        if not check_rate_limit(identifier, max_attempts=3, window_minutes=60):
            flash('Trop de tentatives d\'inscription. Veuillez attendre avant de réessayer.', 'error')
            return render_template('auth/register.html')
        
        # Validation
        if not username or not email or not password:
            flash('Tous les champs sont requis.', 'error')
            return render_template('auth/register.html')
        
        if len(username) < 3:
            flash('Le nom d\'utilisateur doit contenir au moins 3 caractères.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('auth/register.html')
        
        # Register user
        user_id = AuthService.register_user(username, email, password)
        if user_id:
            flash('Compte créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Erreur lors de la création du compte. L\'utilisateur existe peut-être déjà.', 'error')
    
    # Generate captcha for GET request or failed POST
    if request.method == 'GET':
        mark_form_start()
    
    captcha_text, captcha_image = captcha_service.generate_captcha()
    return render_template('auth/register.html', captcha_image=captcha_image)

@auth_bp.route('/login', methods=['GET', 'POST'])
@require_captcha
def login():
    """User login with captcha protection."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Check for bot behavior
        if detect_bot_behavior(request):
            flash('Activité suspecte détectée. Veuillez réessayer plus tard.', 'error')
            return render_template('auth/login.html')
        
        # Check rate limiting
        identifier = f"login_{request.remote_addr}"
        if not check_rate_limit(identifier, max_attempts=5, window_minutes=15):
            flash('Trop de tentatives de connexion. Veuillez attendre avant de réessayer.', 'error')
            return render_template('auth/login.html')
        
        if not username or not password:
            flash('Nom d\'utilisateur et mot de passe requis.', 'error')
            return render_template('auth/login.html')
        
        # Authenticate user
        user = AuthService.authenticate_user(username, password)
        if user:
            # Create session
            create_session(user['id'])
            session['username'] = user['username']
            session['user_email'] = user['email']
            
            # Check if TOTP is enabled
            if user['totp_enabled']:
                session['requires_totp'] = True
                flash('Connexion réussie! Veuillez saisir votre code TOTP.', 'info')
                return redirect(url_for('auth.totp_verify'))
            else:
                session['totp_verified'] = True
                flash(f'Bienvenue, {user["username"]}!', 'success')
                return redirect(url_for('main.index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    
    # Generate captcha for GET request or failed POST
    if request.method == 'GET':
        mark_form_start()
    
    captcha_text, captcha_image = captcha_service.generate_captcha()
    return render_template('auth/login.html', captcha_image=captcha_image)

@auth_bp.route('/totp/verify', methods=['GET', 'POST'])
@require_auth
def totp_verify():
    """TOTP token verification."""
    if not session.get('requires_totp'):
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        backup_code = request.form.get('backup_code', '').strip()
        
        user_id = session.get('user_id')
        
        # Check rate limiting for TOTP attempts
        identifier = f"totp_{user_id}"
        if not check_rate_limit(identifier, max_attempts=10, window_minutes=15):
            flash('Trop de tentatives TOTP. Veuillez attendre avant de réessayer.', 'error')
            return render_template('auth/totp_verify.html')
        
        if token:
            # Verify TOTP token
            if AuthService.verify_totp(user_id, token):
                session['totp_verified'] = True
                session['requires_totp'] = False
                flash('Authentification à deux facteurs réussie!', 'success')
                return redirect(url_for('main.index'))
            else:
                flash('Code TOTP invalide.', 'error')
        
        elif backup_code:
            # Verify backup code
            if AuthService.verify_backup_code(user_id, backup_code):
                session['totp_verified'] = True
                session['requires_totp'] = False
                flash('Code de sauvegarde utilisé avec succès!', 'success')
                return redirect(url_for('main.index'))
            else:
                flash('Code de sauvegarde invalide.', 'error')
        
        else:
            flash('Veuillez saisir un code TOTP ou un code de sauvegarde.', 'error')
    
    return render_template('auth/totp_verify.html')

@auth_bp.route('/totp/setup', methods=['GET', 'POST'])
@require_auth
def totp_setup():
    """TOTP setup for a user."""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            # Generate TOTP setup
            totp_data = AuthService.setup_totp(user_id)
            if totp_data:
                session['totp_setup'] = {
                    'qr_code': totp_data['qr_code'],
                    'backup_codes': totp_data['backup_codes']
                }
                flash('Configuration TOTP générée! Scannez le code QR avec votre application d\'authentification.', 'info')
            else:
                flash('Erreur lors de la génération de la configuration TOTP.', 'error')
        
        elif action == 'verify':
            # Verify TOTP setup
            token = request.form.get('token', '').strip()
            if token:
                if AuthService.verify_totp(user_id, token):
                    # Enable TOTP for user
                    if AuthService.enable_totp(user_id):
                        session['totp_verified'] = True
                        session.pop('totp_setup', None)
                        flash('TOTP activé avec succès! Votre compte est maintenant protégé par l\'authentification à deux facteurs.', 'success')
                        return redirect(url_for('main.index'))
                    else:
                        flash('Erreur lors de l\'activation de TOTP.', 'error')
                else:
                    flash('Code TOTP invalide. Veuillez réessayer.', 'error')
            else:
                flash('Veuillez saisir un code TOTP.', 'error')
    
    totp_setup_data = session.get('totp_setup')
    return render_template('auth/totp_setup.html', totp_data=totp_setup_data)

@auth_bp.route('/logout')
def logout():
    """User logout."""
    username = session.get('username', 'Utilisateur')
    destroy_session()
    flash(f'À bientôt, {username}!', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@require_auth
def profile():
    """User profile page."""
    return render_template('auth/profile.html')

# API endpoints for AJAX requests
@auth_bp.route('/api/check-username')
def check_username():
    """Check if username is available."""
    username = request.args.get('username', '').strip()
    
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Trop court'})
    
    # Check in database
    from app.database import db_manager
    if not db_manager.connection:
        if not db_manager.connect():
            return jsonify({'available': False, 'message': 'Erreur serveur'})
    
    try:
        with db_manager.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'available': False, 'message': 'Déjà utilisé'})
            else:
                return jsonify({'available': True, 'message': 'Disponible'})
    except Exception:
        return jsonify({'available': False, 'message': 'Erreur serveur'})

@auth_bp.route('/api/totp/status')
@require_auth
def totp_status():
    """Get TOTP status for current user."""
    user_id = session.get('user_id')
    
    from app.database import db_manager
    if not db_manager.connection:
        if not db_manager.connect():
            return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with db_manager.connection.cursor() as cursor:
            cursor.execute("SELECT totp_enabled FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if user:
                return jsonify({
                    'totp_enabled': user['totp_enabled'],
                    'authenticated': session.get('authenticated', False),
                    'totp_verified': session.get('totp_verified', False)
                })
            else:
                return jsonify({'error': 'User not found'}), 404
                
    except Exception as e:
        logger.error(f"TOTP status error: {e}")
        return jsonify({'error': 'Server error'}), 500

# Captcha API endpoints
@auth_bp.route('/api/captcha/refresh')
def refresh_captcha():
    """Refresh captcha image."""
    try:
        captcha_text, captcha_image = captcha_service.refresh_captcha()
        return jsonify({
            'success': True,
            'captcha_image': captcha_image
        })
    except Exception as e:
        logger.error(f"Captcha refresh error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate new captcha'
        }), 500

@auth_bp.route('/api/captcha/validate', methods=['POST'])
def validate_captcha_api():
    """Validate captcha via API."""
    try:
        data = request.get_json()
        user_input = data.get('captcha', '').strip() if data else ''
        
        if not user_input:
            return jsonify({
                'valid': False,
                'message': 'Code captcha requis'
            })
        
        is_valid = captcha_service.validate_captcha(user_input)
        
        return jsonify({
            'valid': is_valid,
            'message': 'Code captcha valide' if is_valid else 'Code captcha incorrect'
        })
        
    except Exception as e:
        logger.error(f"Captcha validation API error: {e}")
        return jsonify({
            'valid': False,
            'message': 'Erreur de validation'
        }), 500 