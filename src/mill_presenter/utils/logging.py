import logging
import sys

def setup_logging(name="MillPresenter", level=logging.INFO):
    """Configures the application-wide logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

def get_logger(name="MillPresenter"):
    return logging.getLogger(name)
