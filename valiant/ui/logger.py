import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO):
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(__file__).parent / "logs" / log_file
        log_path.parent.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Create loggers
fastapi_logger = setup_logger("valiant-fastapi", "fastapi.log")
streamlit_logger = setup_logger("valiant-streamlit", "streamlit.log")