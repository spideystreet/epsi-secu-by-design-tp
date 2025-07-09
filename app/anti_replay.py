"""
Anti-replay protection system for preventing request replay attacks
"""
import hashlib
import hmac
import secrets
import time
import logging
from datetime import datetime, timedelta
from flask import session, request, current_app
from functools import wraps
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class AntiReplayService:
    """Handles anti-replay protection through CSRF tokens and nonce validation."""
    
    def __init__(self):
        self.token_expiry = 3600  # 1 hour
        self.nonce_window = 300   # 5 minutes
        self.max_nonce_cache = 1000  # Maximum nonces to keep in memory
        
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token for the current session."""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
            session['csrf_generated'] = time.time()
        
        # Check if token has expired
        elif time.time() - session.get('csrf_generated', 0) > self.token_expiry:
            session['csrf_token'] = secrets.token_urlsafe(32)
            session['csrf_generated'] = time.time()
        
        return session['csrf_token']
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token against session."""
        try:
            session_token = session.get('csrf_token')
            if not session_token or not token:
                logger.warning("Missing CSRF token")
                return False
            
            # Check expiry
            if time.time() - session.get('csrf_generated', 0) > self.token_expiry:
                logger.warning("CSRF token expired")
                return False
            
            # Constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(session_token, token):
                logger.warning("CSRF token mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"CSRF validation error: {e}")
            return False
    
    def generate_request_nonce(self) -> str:
        """Generate a unique nonce for this request."""
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(16)
        
        # Create nonce with timestamp and random component
        nonce_data = f"{timestamp}:{random_part}:{request.remote_addr}"
        nonce = hashlib.sha256(nonce_data.encode()).hexdigest()[:32]
        
        # Store nonce with metadata
        self._store_nonce(nonce, {
            'timestamp': timestamp,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')[:100],
            'endpoint': request.endpoint
        })
        
        return nonce
    
    def validate_request_nonce(self, nonce: str) -> bool:
        """Validate that nonce hasn't been used and is within time window."""
        try:
            if not nonce:
                logger.warning("Missing request nonce")
                return False
            
            # Get nonce metadata
            nonce_data = self._get_nonce(nonce)
            if not nonce_data:
                logger.warning(f"Nonce not found or already used: {nonce[:8]}...")
                return False
            
            # Validate timestamp
            nonce_time = int(nonce_data['timestamp'])
            current_time = int(time.time())
            
            if current_time - nonce_time > self.nonce_window:
                logger.warning(f"Nonce expired: {nonce[:8]}...")
                self._remove_nonce(nonce)
                return False
            
            # Validate IP and User-Agent (optional strict checking)
            if current_app.config.get('STRICT_ANTI_REPLAY', False):
                if nonce_data['ip'] != request.remote_addr:
                    logger.warning(f"Nonce IP mismatch: {nonce[:8]}...")
                    return False
                
                current_ua = request.headers.get('User-Agent', '')[:100]
                if nonce_data['user_agent'] != current_ua:
                    logger.warning(f"Nonce User-Agent mismatch: {nonce[:8]}...")
                    return False
            
            # Mark nonce as used (remove it)
            self._remove_nonce(nonce)
            logger.info(f"Nonce validated and consumed: {nonce[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Nonce validation error: {e}")
            return False
    
    def _store_nonce(self, nonce: str, metadata: Dict[str, Any]):
        """Store nonce in session or database."""
        try:
            # For now, use session storage. In production, use Redis or database
            if 'used_nonces' not in session:
                session['used_nonces'] = {}
            
            # Clean old nonces first
            self._cleanup_old_nonces()
            
            session['used_nonces'][nonce] = metadata
            session.modified = True
            
        except Exception as e:
            logger.error(f"Error storing nonce: {e}")
    
    def _get_nonce(self, nonce: str) -> Optional[Dict[str, Any]]:
        """Retrieve nonce metadata."""
        try:
            return session.get('used_nonces', {}).get(nonce)
        except Exception as e:
            logger.error(f"Error retrieving nonce: {e}")
            return None
    
    def _remove_nonce(self, nonce: str):
        """Remove nonce to mark as used."""
        try:
            if 'used_nonces' in session and nonce in session['used_nonces']:
                del session['used_nonces'][nonce]
                session.modified = True
        except Exception as e:
            logger.error(f"Error removing nonce: {e}")
    
    def _cleanup_old_nonces(self):
        """Clean up expired nonces from session."""
        try:
            if 'used_nonces' not in session:
                return
            
            current_time = int(time.time())
            expired_nonces = []
            
            for nonce, metadata in session['used_nonces'].items():
                nonce_time = int(metadata.get('timestamp', 0))
                if current_time - nonce_time > self.nonce_window:
                    expired_nonces.append(nonce)
            
            # Remove expired nonces
            for nonce in expired_nonces:
                del session['used_nonces'][nonce]
            
            # Limit total nonces in memory
            if len(session['used_nonces']) > self.max_nonce_cache:
                # Remove oldest nonces
                sorted_nonces = sorted(
                    session['used_nonces'].items(),
                    key=lambda x: int(x[1].get('timestamp', 0))
                )
                
                for nonce, _ in sorted_nonces[:len(sorted_nonces) - self.max_nonce_cache]:
                    del session['used_nonces'][nonce]
            
            if expired_nonces:
                session.modified = True
                logger.info(f"Cleaned up {len(expired_nonces)} expired nonces")
                
        except Exception as e:
            logger.error(f"Error cleaning up nonces: {e}")
    
    def generate_form_tokens(self) -> Dict[str, str]:
        """Generate both CSRF token and request nonce for forms."""
        return {
            'csrf_token': self.generate_csrf_token(),
            'request_nonce': self.generate_request_nonce()
        }
    
    def validate_form_tokens(self, csrf_token: str, nonce: str) -> bool:
        """Validate both CSRF token and request nonce."""
        csrf_valid = self.validate_csrf_token(csrf_token)
        nonce_valid = self.validate_request_nonce(nonce)
        
        if not csrf_valid:
            logger.warning("CSRF token validation failed")
        if not nonce_valid:
            logger.warning("Request nonce validation failed")
        
        return csrf_valid and nonce_valid

# Global service instance
anti_replay_service = AntiReplayService()

def require_csrf(f):
    """Decorator to require CSRF token validation."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            
            if not csrf_token:
                from flask import flash, redirect
                flash('Token de sécurité manquant. Veuillez réessayer.', 'error')
                return redirect(request.url)
            
            if not anti_replay_service.validate_csrf_token(csrf_token):
                from flask import flash, redirect
                flash('Token de sécurité invalide. Veuillez recharger la page.', 'error')
                return redirect(request.url)
        
        return f(*args, **kwargs)
    return decorated_function

def require_anti_replay(f):
    """Decorator to require full anti-replay protection (CSRF + nonce)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            csrf_token = request.form.get('csrf_token')
            nonce = request.form.get('request_nonce')
            
            if not csrf_token or not nonce:
                from flask import flash, redirect
                flash('Tokens de sécurité manquants. Veuillez réessayer.', 'error')
                return redirect(request.url)
            
            if not anti_replay_service.validate_form_tokens(csrf_token, nonce):
                from flask import flash, redirect
                flash('Tokens de sécurité invalides. Cette requête a peut-être été rejouée.', 'error')
                return redirect(request.url)
        
        return f(*args, **kwargs)
    return decorated_function

def prevent_duplicate_submission(f):
    """Decorator to prevent duplicate form submissions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            submission_id = request.form.get('submission_id')
            
            if not submission_id:
                from flask import flash, redirect
                flash('ID de soumission manquant.', 'error')
                return redirect(request.url)
            
            # Check if this submission was already processed
            if 'processed_submissions' not in session:
                session['processed_submissions'] = []
            
            if submission_id in session['processed_submissions']:
                from flask import flash, redirect
                flash('Cette requête a déjà été traitée.', 'error')
                return redirect(request.url)
            
            # Process the request
            result = f(*args, **kwargs)
            
            # Mark as processed if successful (no redirect with error)
            if hasattr(result, 'status_code') and result.status_code == 302:
                # Check if it's a redirect due to success (you may need to customize this logic)
                session['processed_submissions'].append(submission_id)
                session.modified = True
                
                # Limit the number of stored submission IDs
                if len(session['processed_submissions']) > 50:
                    session['processed_submissions'] = session['processed_submissions'][-25:]
            
            return result
        
        return f(*args, **kwargs)
    return decorated_function

# Template context processor to make tokens available in templates
def inject_anti_replay_tokens():
    """Inject anti-replay tokens into template context."""
    try:
        tokens = anti_replay_service.generate_form_tokens()
        return {
            'csrf_token': tokens['csrf_token'],
            'request_nonce': tokens['request_nonce'],
            'submission_id': secrets.token_urlsafe(16)
        }
    except Exception as e:
        logger.error(f"Error injecting anti-replay tokens: {e}")
        return {
            'csrf_token': '',
            'request_nonce': '',
            'submission_id': ''
        }

# Request timing validation
class RequestTimingValidator:
    """Validates request timing to detect automated attacks."""
    
    def __init__(self):
        self.min_form_time = 2  # Minimum time to fill a form (seconds)
        self.max_form_time = 1800  # Maximum time before form expires (30 minutes)
    
    def mark_form_start(self, form_id: str):
        """Mark when a form was first loaded."""
        if 'form_start_times' not in session:
            session['form_start_times'] = {}
        
        session['form_start_times'][form_id] = time.time()
        session.modified = True
    
    def validate_form_timing(self, form_id: str) -> bool:
        """Validate that form submission timing is reasonable."""
        try:
            if 'form_start_times' not in session:
                logger.warning(f"No form start time for {form_id}")
                return False
            
            start_time = session['form_start_times'].get(form_id)
            if not start_time:
                logger.warning(f"Form start time not found for {form_id}")
                return False
            
            elapsed_time = time.time() - start_time
            
            if elapsed_time < self.min_form_time:
                logger.warning(f"Form submitted too quickly: {elapsed_time:.2f}s for {form_id}")
                return False
            
            if elapsed_time > self.max_form_time:
                logger.warning(f"Form expired: {elapsed_time:.2f}s for {form_id}")
                return False
            
            # Clean up after successful validation
            del session['form_start_times'][form_id]
            session.modified = True
            
            return True
            
        except Exception as e:
            logger.error(f"Form timing validation error: {e}")
            return False

timing_validator = RequestTimingValidator()

def require_form_timing(form_id: str):
    """Decorator to require valid form timing."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'POST':
                if not timing_validator.validate_form_timing(form_id):
                    from flask import flash, redirect
                    flash('Soumission de formulaire suspecte détectée.', 'error')
                    return redirect(request.url)
            elif request.method == 'GET':
                # Mark form start time on GET request
                timing_validator.mark_form_start(form_id)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Combined decorator for complete protection
def secure_form(form_id: str = None):
    """Complete anti-replay protection: CSRF + nonce + timing + duplicates."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate form ID if not provided
            if form_id is None:
                current_form_id = f"{f.__name__}_{request.endpoint}"
            else:
                current_form_id = form_id
            
            if request.method == 'GET':
                # Mark form start time
                timing_validator.mark_form_start(current_form_id)
            
            elif request.method == 'POST':
                # Validate CSRF token
                csrf_token = request.form.get('csrf_token')
                if not csrf_token or not anti_replay_service.validate_csrf_token(csrf_token):
                    from flask import flash, redirect
                    flash('Token de sécurité invalide. Veuillez recharger la page.', 'error')
                    return redirect(request.url)
                
                # Validate nonce
                nonce = request.form.get('request_nonce')
                if not nonce or not anti_replay_service.validate_request_nonce(nonce):
                    from flask import flash, redirect
                    flash('Cette requête a peut-être été rejouée. Veuillez réessayer.', 'error')
                    return redirect(request.url)
                
                # Validate timing
                if not timing_validator.validate_form_timing(current_form_id):
                    from flask import flash, redirect
                    flash('Soumission de formulaire suspecte détectée.', 'error')
                    return redirect(request.url)
                
                # Validate duplicate submission
                submission_id = request.form.get('submission_id')
                if submission_id:
                    if 'processed_submissions' not in session:
                        session['processed_submissions'] = []
                    
                    if submission_id in session['processed_submissions']:
                        from flask import flash, redirect
                        flash('Cette requête a déjà été traitée.', 'error')
                        return redirect(request.url)
                    
                    # Process the request
                    result = f(*args, **kwargs)
                    
                    # Mark as processed if successful
                    session['processed_submissions'].append(submission_id)
                    session.modified = True
                    
                    # Limit stored submissions
                    if len(session['processed_submissions']) > 50:
                        session['processed_submissions'] = session['processed_submissions'][-25:]
                    
                    return result
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator 