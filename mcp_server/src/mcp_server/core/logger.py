import logging
import sys
from pathlib import Path
from loguru import logger
from mcp_server.config import settings, BASE_DIR

CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <5}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <5} | "
    "{name}:{function}:{line} - "
    "{message}"
)

LOG_DIR = BASE_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / "mcp_server.log"


class InterceptHandler(logging.Handler):
    """
    Intercept standard Python logging logs and forward them to loguru.
    """
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """
    Initialize logging configuration, intercept standard loggers, and write to stdout/file.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Remove standard loguru default handler
    logger.remove()

    # Configure stdout console handler
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=settings.SERVER_DEBUG,
    )

    # Configure file handler
    logger.add(
        LOG_FILE_PATH,
        format=FILE_FORMAT,
        level=settings.LOG_LEVEL,
        rotation="50 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.SERVER_DEBUG,
    )

    # Redirect standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    logger.info("MCP Logger system configured successfully.")
    return logger
