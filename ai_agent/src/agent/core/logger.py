import logging
import os
import sys
from pathlib import Path
from loguru import logger

# Get base directory (ai_agent/src/agent/core/ -> ai_agent)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / "ai_agent.log"

CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <5}</level> | "
    "<magenta>[{extra[X-Request-ID]}]</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <5} | "
    "[{extra[X-Request-ID]}] | "
    "{name}:{function}:{line} - "
    "{message}"
)

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

def inject_context(record):
    """
    Ensure X-Request-ID key exists in log record extra dict to prevent logging format errors.
    """
    record["extra"]["X-Request-ID"] = record["extra"].get("X-Request-ID", "system")

def setup_logging():
    """
    Initialize logging configuration, redirecting console and file outputs to logs/ai_agent.log.
    """
    # Ensure logs directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Remove standard loguru default handler
    logger.remove()

    # Configure patcher
    logger.configure(patcher=inject_context)

    # Configure console handler
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Configure file handler
    logger.add(
        LOG_FILE_PATH,
        format=FILE_FORMAT,
        level="INFO",
        rotation="50 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Intercept standard Python logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    logger.info("Logging system configured successfully for ai_agent.")
    return logger

# Configure logging system automatically on module load
setup_logging()
