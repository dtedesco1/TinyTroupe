import logging

from config import Config


def setup_logger(config: Config) -> logging.Logger:
    logger = logging.getLogger("werewolf")
    logger.setLevel(config.log_level)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)  # Changed from WARNING to DEBUG
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    # File handler
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger
