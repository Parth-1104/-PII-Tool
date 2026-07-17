import logging
import sys
from typing import Optional

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Configures application-wide structured colored logging.
    """
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if COLORLOG_AVAILABLE:
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    else:
        formatter = logging.Formatter(
            "[{asctime}] [{levelname}] [{name}]: {message}",
            datefmt="%H:%M:%S",
            style="{",
        )
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "[{asctime}] [{levelname}] [{name}]: {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for a given module name.
    """
    return logging.getLogger(name)
