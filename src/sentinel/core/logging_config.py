import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("/var/log/sentinel")
LOG_FILE = LOG_DIR / "sentinel.log"

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging once, at process startup, for whichever interface
    (CLI or API) is running. Every module below this just does
    logging.getLogger(__name__) and gets file+console output for free
    via propagation up to root.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)