from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT / PROJECT PATH
# ============================================================

def find_project_root() -> Path:
    """
    Find the project directory containing .env.

    Expected structure:

        adk-agent/
        ├── .env
        ├── .venv/
        └── multi_tool_agent/
            └── llm_client.py
    """

    current = Path(__file__).resolve()

    # Search from llm_client.py upward.
    for directory in [
        current.parent,
        *current.parents,
    ]:

        env_file = directory / ".env"

        if env_file.is_file():
            return directory

    # Fallback:
    # llm_client.py
    # -> multi_tool_agent
    # -> adk-agent
    return current.parent.parent


PROJECT_ROOT = find_project_root()

ENV_FILE = PROJECT_ROOT / ".env"


# ============================================================
# LOAD .ENV
# ============================================================

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


# ============================================================
# HELPERS
# ============================================================

def _get_env(
    *names: str,
) -> str | None:
    """
    Return the first non-empty environment variable.
    """

    for name in names:

        value = os.getenv(name)

        if value is None:
            continue

        value = value.strip()

        if value:
            return value

    return None


def _clean_key(
    value: str | None,
) -> str | None:
    """
    Clean accidental surrounding quotes.

    Supports:

        NVIDIA_API_KEY=abc

        NVIDIA_API_KEY="abc"

        NVIDIA_API_KEY='abc'
    """

    if not value:
        return None

    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == '"'
        and value[-1] == '"'
    ):
        value = value[1:-1].strip()

    elif (
        len(value) >= 2
        and value[0] == "'"
        and value[-1] == "'"
    ):
        value = value[1:-1].strip()

    return value or None


# ============================================================
# PROVIDER CONFIG
# ============================================================

@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


# ============================================================
# LLM CLIENT
# ============================================================

class LLMClient:
    """
    Multi-provider LLM client.

    Supported providers:

        NVIDIA
        OpenAI
        Gemini
        Hugging Face
        xAI
        Anthropic
        DeepSeek

    IMPORTANT:

    The user only needs ONE provider key.

    Example:

        NVIDIA_API_KEY="..."

    is enough.

    If multiple providers are configured, the client
    automatically attempts them in priority order.
    """

    # --------------------------------------------------------
    # DEFAULT MODELS
    # --------------------------------------------------------

    DEFAULT_MODELS = {

        "nvidia":
            "meta/llama-3.1-8b-instruct",

        "openai":
            "gpt-4o-mini",

        "gemini":
            "gemini-2.0-flash",

        "huggingface":
            "meta-llama/Llama-3.1-8B-Instruct",

        "grok":
            "grok-3-mini",

        "anthropic":
            "claude-3-5-haiku-latest",

        "deepseek":
            "deepseek-chat",
    }

    # --------------------------------------------------------
    # PROVIDER PRIORITY
    # --------------------------------------------------------

    PROVIDER_ORDER = [
        "nvidia",
        "openai",
        "gemini",
        "huggingface",
        "grok",
        "anthropic",
        "deepseek",
    ]

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        candidates: list[ProviderConfig] | None = None,
    ) -> None:

        # Reload the exact .env we discovered.
        load_dotenv(
            dotenv_path=ENV_FILE,
            override=False,
        )

        if candidates is not None:

            self.candidates = candidates

        else:

            self.candidates = (
                self._detect_providers()
            )

        if not self.candidates:

            raise RuntimeError(
                "No supported LLM providers are configured.\n"
                "\n"
                f"Expected .env file:\n"
                f"{ENV_FILE}\n"
                "\n"
                f".env exists: "
                f"{ENV_FILE.exists()}\n"
                "\n"
                "Supported keys:\n"
                "  NVIDIA_API_KEY\n"
                "  OPENAI_API_KEY\n"
                "  GEMINI_API_KEY\n"
                "  HF_TOKEN\n"
                "  XAI_API_KEY\n"
                "  ANTHROPIC_API_KEY\n"
                "  DEEPSEEK_API_KEY"
            )

        print(
            "[LLM Client] Configured providers: "
            f"{[p.provider for p in self.candidates]}"
        )

        print(
            "[LLM Client] Primary provider: "
            f"{self.candidates[0].provider}"
        )

        print(
            "[LLM Client] Primary model: "
            f"{self.candidates[0].model}"
        )

    # ========================================================
    # PROVIDER DETECTION
    # ========================================================

    def _detect_providers(
        self,
    ) -> list[ProviderConfig]:

        providers: list[
            ProviderConfig
        ] = []

        # ====================================================
        # NVIDIA
        # ====================================================

        key = _clean_key(
            _get_env(
                "NVIDIA_API_KEY",
                "NVIDIA_NIM_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="nvidia",
                    api_key=key,
                    model=(
                        _get_env(
                            "NVIDIA_MODEL"
                        )
                        or self.DEFAULT_MODELS[
                            "nvidia"
                        ]
                    ),
                    base_url=(
                        _get_env(
                            "NVIDIA_BASE_URL"
                        )
                        or
                        "https://integrate.api.nvidia.com/v1"
                    ),
                )
            )

        # ====================================================
        # OPENAI
        # ====================================================

        key = _clean_key(
            _get_env(
                "OPENAI_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="openai",
                    api_key=key,
                    model=(
                        _get_env(
                            "OPENAI_MODEL"
                        )
                        or self.DEFAULT_MODELS[
                            "openai"
                        ]
                    ),
                    base_url=_get_env(
                        "OPENAI_BASE_URL"
                    ),
                )
            )

        # ====================================================
        # GEMINI
        # ====================================================

        key = _clean_key(
            _get_env(
                "GEMINI_API_KEY",
                "GOOGLE_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="gemini",
                    api_key=key,
                    model=(
                        _get_env(
                            "GEMINI_MODEL"
                        )
                        or self.DEFAULT_MODELS[
                            "gemini"
                        ]
                    ),
                )
            )

        # ====================================================
        # HUGGING FACE
        # ====================================================

        key = _clean_key(
            _get_env(
                "HF_TOKEN",
                "HUGGINGFACE_API_KEY",
                "HUGGINGFACE_TOKEN",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="huggingface",
                    api_key=key,
                    model=(
                        _get_env(
                            "HF_MODEL",
                            "HUGGINGFACE_MODEL",
                        )
                        or self.DEFAULT_MODELS[
                            "huggingface"
                        ]
                    ),
                    base_url=_get_env(
                        "HUGGINGFACE_BASE_URL"
                    ),
                )
            )

        # ====================================================
        # XAI / GROK
        # ====================================================

        key = _clean_key(
            _get_env(
                "XAI_API_KEY",
                "GROK_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="grok",
                    api_key=key,
                    model=(
                        _get_env(
                            "XAI_MODEL",
                            "GROK_MODEL",
                        )
                        or self.DEFAULT_MODELS[
                            "grok"
                        ]
                    ),
                    base_url=(
                        _get_env(
                            "XAI_BASE_URL"
                        )
                        or
                        "https://api.x.ai/v1"
                    ),
                )
            )

        # ====================================================
        # ANTHROPIC
        # ====================================================

        key = _clean_key(
            _get_env(
                "ANTHROPIC_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="anthropic",
                    api_key=key,
                    model=(
                        _get_env(
                            "ANTHROPIC_MODEL"
                        )
                        or self.DEFAULT_MODELS[
                            "anthropic"
                        ]
                    ),
                )
            )

        # ====================================================
        # DEEPSEEK
        # ====================================================

        key = _clean_key(
            _get_env(
                "DEEPSEEK_API_KEY",
            )
        )

        if key:

            providers.append(
                ProviderConfig(
                    provider="deepseek",
                    api_key=key,
                    model=(
                        _get_env(
                            "DEEPSEEK_MODEL"
                        )
                        or self.DEFAULT_MODELS[
                            "deepseek"
                        ]
                    ),
                    base_url=(
                        _get_env(
                            "DEEPSEEK_BASE_URL"
                        )
                        or
                        "https://api.deepseek.com"
                    ),
                )
            )

        # ====================================================
        # SORT BY PRIORITY
        # ====================================================

        priority = {
            provider: index
            for index, provider
            in enumerate(
                self.PROVIDER_ORDER
            )
        }

        providers.sort(
            key=lambda item:
                priority.get(
                    item.provider,
                    999,
                )
        )

        return providers

    # ========================================================
    # STATUS
    # ========================================================

    def status(
        self,
    ) -> dict[str, Any]:

        return {

            "configured":
                bool(self.candidates),

            "providers":
                [
                    provider.provider
                    for provider
                    in self.candidates
                ],

            "primary_provider":
                (
                    self.candidates[0].provider
                    if self.candidates
                    else None
                ),

            "primary_model":
                (
                    self.candidates[0].model
                    if self.candidates
                    else None
                ),

            "project_root":
                str(PROJECT_ROOT),

            "env_file":
                str(ENV_FILE),

            "env_exists":
                ENV_FILE.exists(),
        }

    # ========================================================
    # PROVIDERS PROPERTY
    # ========================================================

    @property
    def providers(
        self,
    ) -> list[str]:

        return [
            provider.provider
            for provider
            in self.candidates
        ]

    # ========================================================
    # GENERATE
    # ========================================================

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:

        if not self.candidates:

            raise RuntimeError(
                "No configured LLM providers."
            )

        print()
        print(
            "[LLM Client] Starting generation"
        )

        errors: list[str] = []

        total = len(
            self.candidates
        )

        for attempt, provider in enumerate(
            self.candidates,
            start=1,
        ):

            print(
                f"[LLM Client] Attempt "
                f"{attempt}/{total}"
            )

            print(
                "[LLM Client] Provider: "
                f"{provider.provider}"
            )

            print(
                "[LLM Client] Model: "
                f"{provider.model}"
            )

            try:

                result = (
                    self._generate_with_provider(
                        provider,
                        system_prompt,
                        user_prompt,
                        **kwargs,
                    )
                )

                if result is None:

                    raise RuntimeError(
                        "Provider returned None."
                    )

                result = str(
                    result
                ).strip()

                if not result:

                    raise RuntimeError(
                        "Provider returned empty response."
                    )

                print(
                    "[LLM Client] SUCCESS: "
                    f"{provider.provider}"
                )

                return result

            except Exception as exc:

                error = str(exc)

                errors.append(
                    f"{provider.provider}: {error}"
                )

                print(
                    "[LLM Client] FAILED: "
                    f"{provider.provider}"
                )

                print(
                    "[LLM Client] Error: "
                    f"{error}"
                )

                if attempt < total:

                    print(
                        "[LLM Client] "
                        "Failing over..."
                    )

        last_error = (
            errors[-1]
            if errors
            else "Unknown error"
        )

        raise RuntimeError(
            "All configured LLM providers failed. "
            f"Last error: {last_error}"
        )

    # ========================================================
    # PROVIDER DISPATCH
    # ========================================================

    def _generate_with_provider(
        self,
        provider: ProviderConfig,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:

        if provider.provider in {
            "nvidia",
            "openai",
            "huggingface",
            "grok",
            "deepseek",
        }:

            return (
                self._generate_openai_compatible(
                    provider,
                    system_prompt,
                    user_prompt,
                    **kwargs,
                )
            )

        if provider.provider == "gemini":

            return self._generate_gemini(
                provider,
                system_prompt,
                user_prompt,
                **kwargs,
            )

        if provider.provider == "anthropic":

            return self._generate_anthropic(
                provider,
                system_prompt,
                user_prompt,
                **kwargs,
            )

        raise RuntimeError(
            f"Unsupported provider: "
            f"{provider.provider}"
        )

    # ========================================================
    # OPENAI-COMPATIBLE PROVIDERS
    # ========================================================

    def _generate_openai_compatible(
        self,
        provider: ProviderConfig,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:

        try:

            from openai import OpenAI

        except ImportError as exc:

            raise RuntimeError(
                "The openai package is not installed.\n"
                "Run:\n"
                "pip install openai"
            ) from exc

        client_kwargs: dict[str, Any] = {

            "api_key":
                provider.api_key,
        }

        if provider.base_url:

            client_kwargs[
                "base_url"
            ] = provider.base_url

        client = OpenAI(
            **client_kwargs
        )

        request: dict[str, Any] = {

            "model":
                provider.model,

            "messages": [

                {
                    "role":
                        "system",

                    "content":
                        system_prompt,
                },

                {
                    "role":
                        "user",

                    "content":
                        user_prompt,
                },
            ],
        }

        if "temperature" in kwargs:

            request[
                "temperature"
            ] = kwargs["temperature"]

        if "max_tokens" in kwargs:

            request[
                "max_tokens"
            ] = kwargs["max_tokens"]

        if "top_p" in kwargs:

            request[
                "top_p"
            ] = kwargs["top_p"]

        response = (
            client.chat.completions.create(
                **request
            )
        )

        choices = getattr(
            response,
            "choices",
            None,
        )

        if not choices:

            raise RuntimeError(
                "Provider returned no choices."
            )

        message = getattr(
            choices[0],
            "message",
            None,
        )

        if message is None:

            raise RuntimeError(
                "Provider returned no message."
            )

        content = getattr(
            message,
            "content",
            None,
        )

        if content is None:

            raise RuntimeError(
                "Provider returned empty content."
            )

        return str(content)

    # ========================================================
    # GEMINI
    # ========================================================

    def _generate_gemini(
        self,
        provider: ProviderConfig,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:

        try:

            from google import genai

        except ImportError as exc:

            raise RuntimeError(
                "The google-genai package is not installed.\n"
                "Run:\n"
                "pip install google-genai"
            ) from exc

        client = genai.Client(
            api_key=provider.api_key
        )

        prompt = (
            system_prompt
            + "\n\n"
            + user_prompt
        )

        response = (
            client.models.generate_content(
                model=provider.model,
                contents=prompt,
            )
        )

        text = getattr(
            response,
            "text",
            None,
        )

        if not text:

            raise RuntimeError(
                "Gemini returned empty response."
            )

        return str(text)

    # ========================================================
    # ANTHROPIC
    # ========================================================

    def _generate_anthropic(
        self,
        provider: ProviderConfig,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:

        try:

            import anthropic

        except ImportError as exc:

            raise RuntimeError(
                "The anthropic package is not installed.\n"
                "Run:\n"
                "pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(
            api_key=provider.api_key
        )

        response = (
            client.messages.create(
                model=provider.model,

                max_tokens=int(
                    kwargs.get(
                        "max_tokens",
                        2048,
                    )
                ),

                system=system_prompt,

                messages=[
                    {
                        "role":
                            "user",

                        "content":
                            user_prompt,
                    }
                ],
            )
        )

        content = getattr(
            response,
            "content",
            None,
        )

        if not content:

            raise RuntimeError(
                "Anthropic returned empty content."
            )

        output: list[str] = []

        for block in content:

            text = getattr(
                block,
                "text",
                None,
            )

            if text:

                output.append(
                    str(text)
                )

        if not output:

            raise RuntimeError(
                "Anthropic returned no text."
            )

        return "\n".join(output)

    # ========================================================
    # RELOAD
    # ========================================================

    def reload_providers(
        self,
    ) -> dict[str, Any]:

        load_dotenv(
            dotenv_path=ENV_FILE,
            override=False,
        )

        self.candidates = (
            self._detect_providers()
        )

        return self.status()


# ============================================================
# DIAGNOSTIC MODE
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("LLM CLIENT DIAGNOSTIC")
    print("=" * 70)

    print(
        "PROJECT ROOT:"
    )

    print(
        PROJECT_ROOT
    )

    print()

    print(
        ".ENV FILE:"
    )

    print(
        ENV_FILE
    )

    print()

    print(
        ".ENV EXISTS:"
    )

    print(
        ENV_FILE.exists()
    )

    # Explicitly reload the discovered .env.
    load_dotenv(
        dotenv_path=ENV_FILE,
        override=True,
    )

    print()

    # --------------------------------------------------------
    # Do NOT print API key.
    # --------------------------------------------------------

    providers_to_check = {

        "NVIDIA_API_KEY":
            _clean_key(
                os.getenv(
                    "NVIDIA_API_KEY"
                )
            ),

        "OPENAI_API_KEY":
            _clean_key(
                os.getenv(
                    "OPENAI_API_KEY"
                )
            ),

        "GEMINI_API_KEY":
            _clean_key(
                os.getenv(
                    "GEMINI_API_KEY"
                )
            ),

        "HF_TOKEN":
            _clean_key(
                os.getenv(
                    "HF_TOKEN"
                )
            ),

        "XAI_API_KEY":
            _clean_key(
                os.getenv(
                    "XAI_API_KEY"
                )
            ),

        "ANTHROPIC_API_KEY":
            _clean_key(
                os.getenv(
                    "ANTHROPIC_API_KEY"
                )
            ),

        "DEEPSEEK_API_KEY":
            _clean_key(
                os.getenv(
                    "DEEPSEEK_API_KEY"
                )
            ),
    }

    print(
        "CONFIGURED KEYS:"
    )

    for name, key in (
        providers_to_check.items()
    ):

        print(
            f"  {name}: "
            f"{'PRESENT' if key else 'NOT PRESENT'}"
        )

    print()
    print("=" * 70)

    try:

        client = LLMClient()

        print()
        print(
            "CLIENT STATUS:"
        )

        print(
            client.status()
        )

        print()
        print(
            "LLM CLIENT INITIALIZATION PASSED"
        )

    except Exception as exc:

        print()
        print(
            "CLIENT INITIALIZATION FAILED:"
        )

        print(
            str(exc)
        )