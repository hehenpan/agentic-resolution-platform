import os
import configparser
from pathlib import Path

# Get project base directory path (ai_agent/src/agent/core/ -> ai_agent)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Determine active environment (default to 'dev')
APP_ENV = os.getenv("APP_ENV", "dev").lower()

# Resolve configuration file path
config_path_str = os.getenv("CONFIG_PATH")
if config_path_str:
    CONFIG_FILE_PATH = Path(config_path_str)
else:
    CONFIG_FILE_PATH = BASE_DIR / f"config_{APP_ENV}.ini"
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
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        self._config.read(config_path, encoding="utf-8")

        # Database configurations
        self.DB_FILE = self._config.get("database", "db_file", fallback="db.sqlite3")

settings = Settings(CONFIG_FILE_PATH, APP_ENV)
