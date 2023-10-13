from configparser import ConfigParser
from pathlib import Path

CONFIG_PATH = Path.home() / ".filesender" / "filesender.py.ini"

def get_defaults() -> dict:
    defaults = {}
    if CONFIG_PATH.exists():
        parser = ConfigParser()
        parser.read(CONFIG_PATH)
        if parser.has_option("system", "base_url"):
            defaults["base_url"] = parser.get("system", "base_url")
        if parser.has_option("system", "default_transfer_days_valid"):
            defaults["default_transfer_days_valid"] = parser.get("system", "default_transfer_days_valid")
        if parser.has_option("user", "username"):
            defaults["username"] = parser.get("user", "username")
        if parser.has_option("user", "apikey"):
            defaults["apikey"] = parser.get("user", "apikey")


    return defaults
