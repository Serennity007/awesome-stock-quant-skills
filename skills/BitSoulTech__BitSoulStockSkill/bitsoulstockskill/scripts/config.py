import json
import utils
import os
from pathlib import Path
from typing import Optional

g_tmp_logic_path: str = ""

def _parse_dotenv_value(env_file: Path, key: str) -> Optional[str]:
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return None

def get_token() -> str:
    token = os.environ.get("BITSOUL_TOKEN")
    if token:
        return token
    env_file = os.environ.get("BITSOUL_TOKEN_ENV_FILE")
    if env_file:
        token_from_file = _parse_dotenv_value(Path(env_file).expanduser(), "BITSOUL_TOKEN")
        if token_from_file:
            return token_from_file
    return ""

def get_cache_dir() -> str:
    cache_dir = os.environ.get("BITSOUL_CACHE_DIR")
    if cache_dir:
        return cache_dir
    env_file = os.environ.get("BITSOUL_TOKEN_ENV_FILE")
    if env_file:
        cache_from_file = _parse_dotenv_value(Path(env_file).expanduser(), "BITSOUL_CACHE_DIR")
        if cache_from_file:
            return cache_from_file
    return utils.get_skill_work_dir()

def get_local_version() -> str:
    with open(os.path.join(utils.get_skill_assets_dir(), "config.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["version"]

def set_tmp_logic_path(fpath: str):
    global g_tmp_logic_path
    g_tmp_logic_path = fpath

def get_tmp_logic_path() -> str:
    global g_tmp_logic_path
    return g_tmp_logic_path
