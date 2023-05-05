import logging

def set_get_logger(name, level=50):
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s', level=level)
    logger = logging.getLogger(name)
    return logger


def get_logger(name):
    return logging.getLogger("root")
