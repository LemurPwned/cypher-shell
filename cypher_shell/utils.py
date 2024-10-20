import logging

from rich.logging import RichHandler


def get_logger():
    logger_name = "cypher-shell"
    if not logging.getLogger(logger_name).handlers:
        logger = logging.getLogger(logger_name)
        FORMAT = "%(message)s"
        logging.basicConfig(level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
    else:
        logger = logging.getLogger(logger_name)
    return logger
