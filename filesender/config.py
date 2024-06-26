from configparser import ConfigParser
from pathlib import Path
from typing import TypedDict

CONFIG_PATH = Path.home() / ".filesender" / "filesender.py.ini"

class Defaults(TypedDict, total=False):
    base_url: str
    username: str
    apikey: str

def get_defaults() -> Defaults:
    defaults: Defaults = {}
    if CONFIG_PATH.exists():
        parser = ConfigParser()
        parser.read(CONFIG_PATH)
        if parser.has_option("system", "base_url"):
            defaults["base_url"] = parser.get("system", "base_url")
        if parser.has_option("user", "username"):
            defaults["username"] = parser.get("user", "username")
        if parser.has_option("user", "apikey"):
            defaults["apikey"] = parser.get("user", "apikey")


    return defaults
