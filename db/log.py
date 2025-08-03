import logging


# Configure logging
logging.basicConfig(filename="db.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_logger(name):
    """
    Get a logger with the specified name.
    """
    logger = logging.getLogger(name)
    return logger
