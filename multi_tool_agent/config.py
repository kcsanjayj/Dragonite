from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT LOADING
# ============================================================

PACKAGE_DIR = Path(__file__).resolve().parent

ENV_FILES = [
    PACKAGE_DIR / ".env",
    PACKAGE_DIR.parent / ".env",
    Path.cwd() / ".env",
]

for env_file in ENV_FILES:
    if env_file.exists():
        load_dotenv(
            env_file,
            override=False,
        )


# ============================================================
# PROVIDER CONFIGURATION
# ============================================================

PROVIDER_ENV_KEYS = {
    "openai": [
        "OPENAI_API_KEY",
    ],

    "gemini": [
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ],

    "nvidia": [
        "NVIDIA_API_KEY",
        "NVIDIA_NIM_API_KEY",
    ],

    "anthropic": [
        "ANTHROPIC_API_KEY",
    ],

    "xai": [
        "XAI_API_KEY",
        "GROK_API_KEY",
    ],

    "deepseek": [
        "DEEPSEEK_API_KEY",
    ],

    "huggingface": [
        "HUGGINGFACE_API_KEY",
        "HF_TOKEN",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def _clean_value(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    # Defensive support for:
    #
    # NVIDIA_API_KEY="abc123"
    #
    # NVIDIA_API_KEY='abc123'
    #
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1].strip()

    return value or None


def get_provider_api_key(
    provider: str,
) -> str | None:

    provider = provider.lower().strip()

    keys = PROVIDER_ENV_KEYS.get(
        provider,
        [],
    )

    for env_name in keys:

        value = _clean_value(
            os.getenv(env_name)
        )

        if value:
            return value

    return None


# ============================================================
# PROVIDER DISCOVERY
# ============================================================

def get_available_providers() -> list[str]:

    available = []

    for provider in PROVIDER_ENV_KEYS:

        if get_provider_api_key(
            provider
        ):
            available.append(
                provider
            )

    return available


def provider_is_configured(
    provider: str,
) -> bool:

    return (
        get_provider_api_key(
            provider
        )
        is not None
    )


# ============================================================
# STATUS
# ============================================================

def get_provider_status() -> dict[str, dict]:

    result = {}

    for provider in PROVIDER_ENV_KEYS:

        key = get_provider_api_key(
            provider
        )

        result[provider] = {
            "configured": key is not None,
            "key_env_names": PROVIDER_ENV_KEYS[
                provider
            ],
        }

    return result


def print_provider_status() -> None:

    print()
    print("=" * 60)
    print("LLM PROVIDER CONFIGURATION")
    print("=" * 60)

    available = get_available_providers()

    for provider in PROVIDER_ENV_KEYS:

        status = (
            "READY"
            if provider in available
            else "NOT CONFIGURED"
        )

        print(
            f"{provider:<15} : {status}"
        )

    print("-" * 60)

    print(
        "Available providers:",
        available,
    )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print_provider_status()