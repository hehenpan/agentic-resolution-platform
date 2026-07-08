import logging
import os
import sys
from pathlib import Path
from loguru import logger
from starlette_context import context


# Unified log output formats (terminal with color, file without color to keep clean)
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

# Log storage path, relative to the api_server directory
LOG_DIR = Path("logs")
LOG_FILE_PATH = LOG_DIR / "api_server.log"

class InterceptHandler(logging.Handler):
    """
    Intercept standard Python logging logs and forward them to loguru.
    """
    def emit(self, record):
        # Try to get corresponding loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller's frame to report correct file and line number
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())



def inject_starlette_context(record):
    """
    Triggered whenever loguru is about to emit a log record.
    Checks if starlette-context exists and, if so, injects its data into loguru's extra dictionary.
    """
    # Check if currently within the lifecycle of an HTTP request (coroutine context)
    if context.exists():
        # Retrieve all data from the starlette-context dictionary (including Request ID, etc.)
        # and store them in loguru's record["extra"] dict
        record["extra"].update(context.data)
    else:
        # If not in request context (e.g. during application startup, cron jobs), provide a default value to prevent formatting errors
        record["extra"]["X-Request-ID"] = "system"




def setup_logging():
    """
    Initialize logging configuration, intercept uvicorn/fastapi logs, and output to stdout and log files.
    """
    # Ensure the log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Remove standard loguru default handler
    logger.remove()

    # 2. Configure patcher to dynamically add request_id context to log records
    logger.configure(patcher=inject_starlette_context)

    # 3. Configure stdout (console) handler
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 4. Configure file handler
    logger.add(
        LOG_FILE_PATH,

        format=FILE_FORMAT,
        level="INFO",
        rotation="50 MB",       # Rotate file when it reaches 50 MB
        retention="14 days",    # Keep logs for 14 days
        compression="zip",      # Compress historical logs in zip format
        encoding="utf-8",
        enqueue=True,           # Write asynchronously to improve I/O performance under high concurrency
        backtrace=True,
        diagnose=True,
    )

    # 4. Intercept uvicorn/fastapi default standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Force redirect uvicorn loggers to InterceptHandler
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    logger.info("Logging system configured successfully. Output directed to stdout and file.")
    return logger
