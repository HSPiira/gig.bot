import logging
import os
from datetime import datetime

# Ensure the logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Define log file name with timestamp
LOG_FILE = os.path.join(LOG_DIR, f"gig_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def setup_logging():
    """
    Configure and return the 'gig_bot' logger to emit INFO-level messages to both the console and the module's timestamped log file.
    
    Returns:
        logging.Logger: The configured logger instance named 'gig_bot' that writes INFO-level (and above) records to the console and to LOG_FILE.
    """
    # Create a logger
    logger = logging.getLogger('gig_bot')
    logger.setLevel(logging.INFO)

    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Create console handler and set level to info
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Create file handler and set level to info
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Initialize logger
logger = setup_logging()

if __name__ == "__main__":
    # Example usage
    logger.info("Logger initialized successfully.")
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")