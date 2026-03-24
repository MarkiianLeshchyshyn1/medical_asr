import logging


DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)

    logger.propagate = False
    return logger
