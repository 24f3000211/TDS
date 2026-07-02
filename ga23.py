import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 12,
    "debug": False,
    "log_level": "warning",
    "api_key": "default-secret-000",
}


def coerce_value(key: str, value: Any) -> Any:
    if key in {"port", "workers"}:
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}

    return str(value)


def load_yaml_config() -> Dict[str, Any]:
    path = Path("config.development.yaml")
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def load_dotenv_config() -> Dict[str, Any]:
    env_path = Path(".env")
    if not env_path.exists():
        return {}

    raw = dotenv_values(".env")
    cfg = {}

    for k, v in raw.items():
        if v is None:
            continue
        if k == "APP_PORT":
            cfg["port"] = v
        elif k == "APP_DEBUG":
            cfg["debug"] = v
        elif k == "APP_LOG_LEVEL":
            cfg["log_level"] = v
        elif k == "NUM_WORKERS":
            cfg["workers"] = v
        elif k.startswith("APP_"):
            cfg[k.removeprefix("APP_").lower()] = v

    return cfg


def load_os_env_config() -> Dict[str, Any]:
    cfg = {}
    for k, v in os.environ.items():
        if not k.startswith("APP_"):
            continue

        name = k.removeprefix("APP_").lower()
        cfg[name] = v

    return cfg


def merge_config() -> Dict[str, Any]:
    merged = dict(DEFAULTS)

    yaml_cfg = load_yaml_config()
    merged.update(yaml_cfg)

    dotenv_cfg = load_dotenv_config()
    merged.update(dotenv_cfg)

    os_cfg = load_os_env_config()
    merged.update(os_cfg)

    for k in list(merged.keys()):
        if k in {"port", "workers", "debug", "log_level", "api_key"}:
            merged[k] = coerce_value(k, merged[k])

    return merged


@app.get("/effective-config")
def effective_config(set: Optional[List[str]] = Query(default=None)):
    cfg = merge_config()

    if set:
        for item in set:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in cfg:
                cfg[key] = coerce_value(key, value)
            else:
                cfg[key] = value

    cfg["api_key"] = "****"

    return {
        "port": int(cfg["port"]),
        "workers": int(cfg["workers"]),
        "debug": bool(cfg["debug"]),
        "log_level": str(cfg["log_level"]),
        "api_key": "****",
    }
