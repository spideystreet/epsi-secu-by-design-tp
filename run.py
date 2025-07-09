#!/usr/bin/env python3
"""
TestVault Application Runner
"""
from app import create_app
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    app = create_app()
    
    # Development configuration
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('APP_PORT', 8080))
    
    logger.info(f"Starting TestVault application on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    ) 