import os
import configparser
from pathlib import Path

from loguru import logger

# Get project base directory path
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Determine active environment (default to 'dev')
APP_ENV = os.getenv("APP_ENV", "dev").lower()

# Resolve configuration file path
# 1. Check if explicit CONFIG_PATH is set in environment
config_path_str = os.getenv("CONFIG_PATH")
if config_path_str:
    CONFIG_FILE_PATH = Path(config_path_str)
else:
    # 2. Check config_{APP_ENV}.ini in root folder
    CONFIG_FILE_PATH = BASE_DIR / f"config_{APP_ENV}.ini"
    # 3. Fallback to default config.ini if the env-specific file is missing
    if not CONFIG_FILE_PATH.exists():
        CONFIG_FILE_PATH = BASE_DIR / "config.ini"

CONFIG_FILE_PATH = str(CONFIG_FILE_PATH)


class Settings(object):
    """
    Application settings parsed from config.ini.
    """
    def __init__(self, config_path: str, app_env: str):
        self.APP_ENV = app_env
        self._config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            logger.error(
                "API Server configuration file does not exist: config_path={}",
                config_path,
            )
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        self._config.read(config_path, encoding="utf-8")


        # Server configurations
        self.SERVER_HOST = self._config.get("server", "host", fallback="0.0.0.0")
        self.SERVER_PORT = self._config.getint("server", "port", fallback=8000)
        self.SERVER_DEBUG = self._config.getboolean("server", "debug", fallback=False)
        self.SERVER_WORKERS = self._config.getint("server", "workers", fallback=1)
        self.SERVER_RELOAD = self._config.getboolean(
            "server",
            "reload",
            fallback=app_env == "dev",
        )
        reload_dirs = self._config.get("server", "reload_dirs", fallback="")
        self.SERVER_RELOAD_DIRS = [
            path.strip()
            for path in reload_dirs.split(",")
            if path.strip()
        ]


        # Database configurations
        self.DB_FILE = self._config.get("database", "db_file", fallback="db.sqlite3")

        # Authentication configurations
        self.SESSION_EXPIRE_SECONDS = self._config.getint("auth", "session_expire_seconds", fallback=2592000)
        self.SESSION_COOKIE_SECURE = self._config.getboolean("auth", "session_cookie_secure", fallback=True)

        # Storage configurations
        self.STORAGE_DIR = self._config.get("storage", "storage_dir", fallback="data/files")
        self.FILE_STORAGE_TYPE = self._config.get("storage", "storage_type", fallback="local").lower()

        # AI Agent configurations
        self.AI_AGENT_URL = self._config.get("ai_agent", "url", fallback=None)




settings = Settings(CONFIG_FILE_PATH, APP_ENV)
