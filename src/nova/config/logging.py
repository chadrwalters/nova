"""Logging configuration for Nova."""

import os
import logging

def setup_logging():
    """Set up logging configuration."""
    # Get log level from environment variable
    log_level = os.getenv('NOVA_LOG_LEVEL', 'INFO').upper()
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)-8s %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set log level for all nova loggers
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith('nova'):
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
            # Ensure the logger propagates to the root logger
            logger.propagate = True 