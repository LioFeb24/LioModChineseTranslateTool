DEFAULT_BASE_URL = "https://api.deepseek.com"

_RUNTIME_CONFIG = {
    "api_key": "",
    "base_url": DEFAULT_BASE_URL,
}


def get_config() -> dict:
    return {
        "api_key": _RUNTIME_CONFIG.get("api_key", ""),
        "base_url": _RUNTIME_CONFIG.get("base_url", DEFAULT_BASE_URL),
    }


def save_config(config: dict) -> None:
    _RUNTIME_CONFIG["api_key"] = str(config.get("api_key", "")).strip()
    _RUNTIME_CONFIG["base_url"] = str(config.get("base_url", DEFAULT_BASE_URL)).strip() or DEFAULT_BASE_URL
