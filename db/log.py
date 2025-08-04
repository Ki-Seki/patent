import logging
import sys


# Configure logging with both file and console output
def setup_logging():
    """
    Set up logging configuration for both file and console output.
    """
    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create file handler
    file_handler = logging.FileHandler("db.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# Initialize logging configuration
setup_logging()


def get_logger(name):
    """
    Get a logger with the specified name.
    """
    logger = logging.getLogger(name)
    return logger
