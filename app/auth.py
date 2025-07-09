"""
Authentication and TOTP service module
"""
import pyotp
import qrcode
import secrets
import bcrypt
import logging
from io import BytesIO
import base64
from datetime import datetime, timedelta
from flask import current_app, session
from app.database import db_manager
from app.vault_client import vault_client
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TOTPService:
    """Handles TOTP generation, QR codes, and verification."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(username: str, secret: str) -> str:
        """Generate QR code for TOTP setup."""
        issuer = current_app.config.get('TOTP_ISSUER', 'TestVault')
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for web display
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_token(secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token with time window tolerance."""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    @staticmethod
    def generate_backup_codes(count: int = 8) -> List[str]:
        """Generate backup codes for account recovery."""
        codes = []
        for _ in range(count):
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes

class AuthService:
    """Handles user authentication, registration, and session management."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def register_user(username: str, email: str, password: str) -> Optional[int]:
        """Register a new user."""
        if not db_manager.connection:
            if not db_manager.connect():
                return None
        
        try:
            # Check if user exists
            with db_manager.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
                if cursor.fetchone():
                    logger.warning(f"User registration failed: {username} already exists")
                    return None
                
                # Create user
                password_hash = AuthService.hash_password(password)
                cursor.execute(
                    """INSERT INTO users (username, email, password_hash) 
                       VALUES (%s, %s, %s)""",
                    (username, email, password_hash)
                )
                db_manager.connection.commit()
                user_id = cursor.lastrowid
                
                logger.info(f"User registered successfully: {username}")
                return user_id
                
        except Exception as e:
            logger.error(f"User registration error: {e}")
            db_manager.connection.rollback()
            return None
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username/password."""
        if not db_manager.connection:
            if not db_manager.connect():
                return None
        
        try:
            with db_manager.connection.cursor() as cursor:
                cursor.execute(
                    """SELECT id, username, email, password_hash, is_active, 
                              totp_enabled, failed_login_attempts, account_locked_until
                       FROM users WHERE username = %s OR email = %s""",
                    (username, username)
                )
                user = cursor.fetchone()
                
                if not user:
                    logger.warning(f"Authentication failed: user not found - {username}")
                    return None
                
                # Check if account is locked
                if (user['account_locked_until'] and 
                    user['account_locked_until'] > datetime.now()):
                    logger.warning(f"Authentication failed: account locked - {username}")
                    return None
                
                # Check if account is active
                if not user['is_active']:
                    logger.warning(f"Authentication failed: account inactive - {username}")
                    return None
                
                # Verify password
                if not AuthService.verify_password(password, user['password_hash']):
                    # Increment failed attempts
                    AuthService._increment_failed_attempts(user['id'])
                    logger.warning(f"Authentication failed: invalid password - {username}")
                    return None
                
                # Reset failed attempts on successful authentication
                AuthService._reset_failed_attempts(user['id'])
                
                # Update last login
                cursor.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = %s",
                    (user['id'],)
                )
                db_manager.connection.commit()
                
                # Remove password hash from returned data
                user.pop('password_hash', None)
                logger.info(f"User authenticated successfully: {username}")
                return user
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    @staticmethod
    def _increment_failed_attempts(user_id: int):
        """Increment failed login attempts and lock account if necessary."""
        try:
            with db_manager.connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE users 
                       SET failed_login_attempts = failed_login_attempts + 1,
                           account_locked_until = CASE 
                               WHEN failed_login_attempts >= 4 
                               THEN DATE_ADD(NOW(), INTERVAL 15 MINUTE)
                               ELSE account_locked_until 
                           END
                       WHERE id = %s""",
                    (user_id,)
                )
                db_manager.connection.commit()
        except Exception as e:
            logger.error(f"Failed to increment login attempts: {e}")
    
    @staticmethod
    def _reset_failed_attempts(user_id: int):
        """Reset failed login attempts."""
        try:
            with db_manager.connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE users 
                       SET failed_login_attempts = 0, account_locked_until = NULL
                       WHERE id = %s""",
                    (user_id,)
                )
                db_manager.connection.commit()
        except Exception as e:
            logger.error(f"Failed to reset login attempts: {e}")
    
    @staticmethod
    def setup_totp(user_id: int) -> Optional[Dict[str, Any]]:
        """Setup TOTP for a user."""
        try:
            # Generate TOTP secret
            secret = TOTPService.generate_secret()
            
            # Store secret in Vault
            if not vault_client.store_secret(f'totp/{user_id}', {'secret': secret}):
                logger.error(f"Failed to store TOTP secret in Vault for user {user_id}")
                return None
            
            # Generate backup codes
            backup_codes = TOTPService.generate_backup_codes()
            
            # Store backup codes in database (hashed)
            if not db_manager.connection:
                if not db_manager.connect():
                    return None
            
            with db_manager.connection.cursor() as cursor:
                # Clear existing backup codes
                cursor.execute("DELETE FROM totp_backup_codes WHERE user_id = %s", (user_id,))
                
                # Insert new backup codes
                for code in backup_codes:
                    code_hash = AuthService.hash_password(code.replace('-', ''))
                    cursor.execute(
                        "INSERT INTO totp_backup_codes (user_id, code_hash) VALUES (%s, %s)",
                        (user_id, code_hash)
                    )
                
                db_manager.connection.commit()
            
            # Get username for QR code
            with db_manager.connection.cursor() as cursor:
                cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                username = user['username'] if user else f"user_{user_id}"
            
            # Generate QR code
            qr_code = TOTPService.generate_qr_code(username, secret)
            
            logger.info(f"TOTP setup completed for user {user_id}")
            return {
                'qr_code': qr_code,
                'backup_codes': backup_codes,
                'secret': secret  # Only return for initial setup
            }
            
        except Exception as e:
            logger.error(f"TOTP setup error for user {user_id}: {e}")
            return None
    
    @staticmethod
    def verify_totp(user_id: int, token: str) -> bool:
        """Verify TOTP token for a user."""
        try:
            # Get TOTP secret from Vault
            totp_data = vault_client.get_secret(f'totp/{user_id}')
            if not totp_data or 'secret' not in totp_data:
                logger.error(f"TOTP secret not found for user {user_id}")
                return False
            
            secret = totp_data['secret']
            return TOTPService.verify_token(secret, token)
            
        except Exception as e:
            logger.error(f"TOTP verification error for user {user_id}: {e}")
            return False
    
    @staticmethod
    def verify_backup_code(user_id: int, code: str) -> bool:
        """Verify and consume a backup code."""
        if not db_manager.connection:
            if not db_manager.connect():
                return False
        
        try:
            # Clean input (remove dashes, spaces)
            clean_code = code.replace('-', '').replace(' ', '')
            
            with db_manager.connection.cursor() as cursor:
                # Get unused backup codes
                cursor.execute(
                    """SELECT id, code_hash FROM totp_backup_codes 
                       WHERE user_id = %s AND used = FALSE""",
                    (user_id,)
                )
                backup_codes = cursor.fetchall()
                
                # Check each code
                for backup_code in backup_codes:
                    if AuthService.verify_password(clean_code, backup_code['code_hash']):
                        # Mark code as used
                        cursor.execute(
                            """UPDATE totp_backup_codes 
                               SET used = TRUE, used_at = NOW() 
                               WHERE id = %s""",
                            (backup_code['id'],)
                        )
                        db_manager.connection.commit()
                        
                        logger.info(f"Backup code used successfully for user {user_id}")
                        return True
                
                logger.warning(f"Invalid backup code for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Backup code verification error for user {user_id}: {e}")
            return False
    
    @staticmethod
    def enable_totp(user_id: int) -> bool:
        """Enable TOTP for a user."""
        if not db_manager.connection:
            if not db_manager.connect():
                return False
        
        try:
            with db_manager.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET totp_enabled = TRUE WHERE id = %s",
                    (user_id,)
                )
                db_manager.connection.commit()
                
                logger.info(f"TOTP enabled for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to enable TOTP for user {user_id}: {e}")
            return False

# Session management functions
def create_session(user_id: int) -> str:
    """Create a new user session."""
    session_token = secrets.token_urlsafe(32)
    session['user_id'] = user_id
    session['session_token'] = session_token
    session['authenticated'] = True
    session['totp_verified'] = False
    session.permanent = True
    
    return session_token

def destroy_session():
    """Destroy current session."""
    session.clear()

def require_auth(f):
    """Decorator to require authentication."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_totp(f):
    """Decorator to require TOTP verification."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('totp_verified'):
            from flask import redirect, url_for
            return redirect(url_for('auth.totp_verify'))
        return f(*args, **kwargs)
    return decorated_function 