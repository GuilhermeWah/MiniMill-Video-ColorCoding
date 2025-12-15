import logging
import sys

def setup_logging(name="MillPresenter", level=logging.INFO):
    """Configures the application-wide logger."""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Configure root so all module loggers inherit the same level/handler.
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        root_logger.addHandler(ch)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(level)
            if handler.formatter is None:
                handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True
    return logger

def get_logger(name="MillPresenter"):
    return logging.getLogger(name)
