"""
Server-side captcha generation and validation system
"""
import random
import string
import secrets
import logging
import base64
from datetime import datetime, timedelta
from flask import session
from typing import Optional, Tuple
import html

logger = logging.getLogger(__name__)

# Try to import PIL, if not available use text fallback
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL (Pillow) not available. Using text-based captcha fallback.")

class CaptchaService:
    """Handles server-side captcha generation and validation."""
    
    def __init__(self):
        self.width = 200
        self.height = 80
        self.font_size = 36
        self.char_count = 5
        # Use characters that are easily distinguishable
        self.characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        
    def generate_captcha_text(self) -> str:
        """Generate random captcha text."""
        return ''.join(random.choices(self.characters, k=self.char_count))
    
    def create_captcha_image(self, text: str) -> str:
        """Create captcha image and return as base64 string or HTML."""
        if PIL_AVAILABLE:
            return self._create_pil_captcha(text)
        else:
            return self._create_text_captcha(text)
    
    def _create_pil_captcha(self, text: str) -> str:
        """Create captcha image using PIL."""
        try:
            # Create image
            image = Image.new('RGB', (self.width, self.height), color='white')
            draw = ImageDraw.Draw(image)
            
            # Add background noise - lines
            for _ in range(random.randint(5, 8)):
                x1 = random.randint(0, self.width)
                y1 = random.randint(0, self.height)
                x2 = random.randint(0, self.width)
                y2 = random.randint(0, self.height)
                color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
                draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
            
            # Add background noise - dots
            for _ in range(random.randint(20, 40)):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height)
                color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
                draw.point((x, y), fill=color)
            
            # Calculate text positioning
            char_width = self.width // len(text)
            
            # Draw each character with randomization
            for i, char in enumerate(text):
                # Random color (dark)
                color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                
                # Random position within character space
                x = i * char_width + random.randint(5, char_width - 25)
                y = random.randint(10, 20)
                
                # Try to use a system font, fallback to default
                try:
                    # Try common system fonts
                    font_paths = [
                        "/System/Library/Fonts/Arial.ttf",  # macOS
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                        "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                    ]
                    
                    font = None
                    for font_path in font_paths:
                        try:
                            font = ImageFont.truetype(font_path, self.font_size)
                            break
                        except:
                            continue
                    
                    if font is None:
                        # Fallback to default font
                        font = ImageFont.load_default()
                        
                except Exception:
                    font = ImageFont.load_default()
                
                # Draw character
                draw.text((x, y), char, font=font, fill=color)
                
                # Add slight rotation effect (simulated with multiple draws)
                for offset in range(1, 3):
                    offset_color = (color[0] + 20, color[1] + 20, color[2] + 20)
                    if random.choice([True, False]):
                        draw.text((x + offset, y), char, font=font, fill=offset_color)
            
            # Add more noise - random lines over text
            for _ in range(random.randint(2, 4)):
                x1 = random.randint(0, self.width)
                y1 = random.randint(0, self.height)
                x2 = random.randint(0, self.width)
                y2 = random.randint(0, self.height)
                color = (random.randint(100, 150), random.randint(100, 150), random.randint(100, 150))
                draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
            
            # Apply slight blur filter
            image = image.filter(ImageFilter.BLUR)
            
            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"Error creating PIL captcha image: {e}")
            # Fallback to text captcha
            return self._create_text_captcha(text)
    
    def _create_text_captcha(self, text: str) -> str:
        """Create a text-based captcha as fallback when PIL is not available."""
        # Create stylized text display with HTML/CSS
        styled_chars = []
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
        
        for i, char in enumerate(text):
            color = random.choice(colors)
            # Random transformations
            rotation = random.randint(-15, 15)
            size = random.randint(20, 30)
            x_offset = random.randint(-5, 5)
            y_offset = random.randint(-10, 10)
            
            styled_char = f'''
                <span style="
                    color: {color};
                    font-size: {size}px;
                    font-weight: bold;
                    display: inline-block;
                    transform: rotate({rotation}deg) translate({x_offset}px, {y_offset}px);
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                    margin: 0 2px;
                    font-family: 'Courier New', monospace;
                ">{html.escape(char)}</span>
            '''
            styled_chars.append(styled_char)
        
        # Create noise characters
        noise_chars = []
        for _ in range(random.randint(3, 6)):
            noise_char = random.choice('!@#$%&*+-=?')
            color = '#E0E0E0'
            rotation = random.randint(-30, 30)
            size = random.randint(12, 18)
            x_pos = random.randint(10, 90)
            y_pos = random.randint(10, 90)
            
            noise_chars.append(f'''
                <span style="
                    color: {color};
                    font-size: {size}px;
                    position: absolute;
                    left: {x_pos}%;
                    top: {y_pos}%;
                    transform: rotate({rotation}deg);
                    opacity: 0.3;
                ">{html.escape(noise_char)}</span>
            ''')
        
        # Combine everything
        captcha_html = f'''
            <div style="
                width: {self.width}px;
                height: {self.height}px;
                background: linear-gradient(45deg, #f0f0f0, #e0e0e0);
                border: 2px solid #ccc;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
                margin: 0 auto;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    z-index: 2;
                    position: relative;
                ">
                    {''.join(styled_chars)}
                </div>
                {''.join(noise_chars)}
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: repeating-linear-gradient(
                        90deg,
                        transparent,
                        transparent 2px,
                        rgba(255,255,255,0.1) 2px,
                        rgba(255,255,255,0.1) 4px
                    );
                    z-index: 1;
                "></div>
            </div>
        '''
        
        return captcha_html
    
    def generate_captcha(self) -> Tuple[str, str]:
        """Generate captcha text and image, store in session."""
        text = self.generate_captcha_text()
        image_data = self.create_captcha_image(text)
        
        # Store in session with timestamp
        session['captcha_text'] = text
        session['captcha_timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Generated captcha: {text}")
        return text, image_data
    
    def validate_captcha(self, user_input: str) -> bool:
        """Validate user input against stored captcha."""
        try:
            stored_text = session.get('captcha_text')
            timestamp_str = session.get('captcha_timestamp')
            
            if not stored_text or not timestamp_str:
                logger.warning("No captcha in session")
                return False
            
            # Check expiration (5 minutes)
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.now() - timestamp > timedelta(minutes=5):
                logger.warning("Captcha expired")
                self.clear_captcha()
                return False
            
            # Case-insensitive comparison
            is_valid = stored_text.upper() == user_input.upper().strip()
            
            if is_valid:
                logger.info("Captcha validation successful")
                self.clear_captcha()  # Clear after successful validation
            else:
                logger.warning(f"Captcha validation failed: expected {stored_text}, got {user_input}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Captcha validation error: {e}")
            return False
    
    def clear_captcha(self):
        """Clear captcha from session."""
        session.pop('captcha_text', None)
        session.pop('captcha_timestamp', None)
    
    def refresh_captcha(self) -> Tuple[str, str]:
        """Generate new captcha (for refresh functionality)."""
        self.clear_captcha()
        return self.generate_captcha()

# Global captcha service instance
captcha_service = CaptchaService()

def require_captcha(f):
    """Decorator to require captcha validation for routes."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, flash, redirect, url_for
        
        if request.method == 'POST':
            captcha_input = request.form.get('captcha', '').strip()
            
            if not captcha_input:
                flash('Veuillez saisir le code captcha.', 'error')
                return redirect(request.url)
            
            if not captcha_service.validate_captcha(captcha_input):
                flash('Code captcha incorrect. Veuillez réessayer.', 'error')
                return redirect(request.url)
        
        return f(*args, **kwargs)
    return decorated_function

# Anti-bot protection functions
def detect_bot_behavior(request) -> bool:
    """Detect potential bot behavior based on request patterns."""
    try:
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Common bot indicators
        bot_indicators = [
            'bot', 'crawler', 'spider', 'scraper', 'automated',
            'curl', 'wget', 'python-requests', 'mechanize'
        ]
        
        for indicator in bot_indicators:
            if indicator in user_agent:
                logger.warning(f"Potential bot detected: {user_agent}")
                return True
        
        # Check for missing common headers
        if not request.headers.get('Accept'):
            logger.warning("Missing Accept header - potential bot")
            return True
        
        # Check for suspicious form submission speed (too fast)
        if 'form_start_time' in session:
            try:
                start_time = datetime.fromisoformat(session['form_start_time'])
                if datetime.now() - start_time < timedelta(seconds=2):
                    logger.warning("Form submitted too quickly - potential bot")
                    return True
            except:
                pass
        
        return False
        
    except Exception as e:
        logger.error(f"Bot detection error: {e}")
        return False

def mark_form_start():
    """Mark the start time of form interaction."""
    session['form_start_time'] = datetime.now().isoformat()

def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """Check if identifier has exceeded rate limit."""
    try:
        from app.database import db_manager
        
        if not db_manager.connection:
            if not db_manager.connect():
                return True  # Allow if can't check
        
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=window_minutes)
        
        with db_manager.connection.cursor() as cursor:
            # Clean old attempts
            cursor.execute(
                "DELETE FROM rate_limits WHERE created_at < %s",
                (window_start,)
            )
            
            # Count recent attempts
            cursor.execute(
                """SELECT COUNT(*) as attempt_count FROM rate_limits 
                   WHERE identifier = %s AND created_at >= %s""",
                (identifier, window_start)
            )
            
            result = cursor.fetchone()
            attempt_count = result['attempt_count'] if result else 0
            
            if attempt_count >= max_attempts:
                logger.warning(f"Rate limit exceeded for {identifier}")
                return False
            
            # Record this attempt
            cursor.execute(
                "INSERT INTO rate_limits (identifier, created_at) VALUES (%s, %s)",
                (identifier, current_time)
            )
            db_manager.connection.commit()
            
            return True
            
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True  # Allow if error checking

# Create rate limits table if needed
def ensure_rate_limits_table():
    """Ensure rate limits table exists."""
    try:
        from app.database import db_manager
        
        if not db_manager.connection:
            if not db_manager.connect():
                return
        
        with db_manager.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    identifier VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_identifier_time (identifier, created_at)
                )
            """)
            db_manager.connection.commit()
            logger.info("Rate limits table ensured")
            
    except Exception as e:
        logger.error(f"Error ensuring rate limits table: {e}") 