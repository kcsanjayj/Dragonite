"""
Unified multi-provider LLM client gateway.
Supports multiple LLM providers (OpenAI, Anthropic, etc.) with a unified interface.
"""

import json
import functools
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod
from ..core.config import config
from ..core.state import state
from ..utils.observability import token_tracker
from .adaptive_router import adaptive_router, TaskComplexity

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize the provider."""
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response from chat messages."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        """Initialize OpenAI provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **kwargs
        )
        content = response.choices[0].message.content
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", **kwargs):
        """Initialize Anthropic provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("Anthropic package not installed. Install with: pip install anthropic")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.content[0].text
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        content = response.content[0].text
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            **kwargs
        )
        return response.content[0].text


class NVIDIAProvider(LLMProvider):
    """NVIDIA (NIM) provider implementation."""
    
    def __init__(self, api_key: str, model: str = "meta/llama-3.1-405b-instruct", **kwargs):
        """Initialize NVIDIA provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
        self.base_url = "https://integrate.api.nvidia.com/v1"
    
    def _get_client(self):
        """Lazy initialization of NVIDIA client using OpenAI SDK."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **kwargs
        )
        content = response.choices[0].message.content
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", **kwargs):
        """Initialize Gemini provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                self._client = self._genai_client
            except ImportError:
                raise RuntimeError("Google GenAI package not installed. Install with: pip install google-genai")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        result = await client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"temperature": temperature, "max_output_tokens": max_tokens}
        )
        return result.text
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        result = await client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"temperature": temperature, "max_output_tokens": max_tokens}
        )
        content = result.text
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg["role"] == "user":
                contents.append({"role": "user", "parts": [msg["content"]]})
            else:
                contents.append({"role": "model", "parts": [msg["content"]]})
        
        result = await client.models.generate_content(
            model=self.model,
            contents=contents,
            config={"temperature": temperature, "max_output_tokens": max_tokens}
        )
        return result.text


class HuggingFaceProvider(LLMProvider):
    """HuggingFace provider implementation."""
    
    def __init__(self, api_key: str, model: str = "mistralai/Mistral-7B-Instruct-v0.3", **kwargs):
        """Initialize HuggingFace provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
        self.base_url = "https://api-inference.huggingface.co/models"
    
    def _get_client(self):
        """Lazy initialization of HuggingFace client using OpenAI SDK."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=f"{self.base_url}/{self.model}"
                )
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        content = response.choices[0].message.content
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content


class GrokProvider(LLMProvider):
    """xAI Grok provider implementation."""
    
    def __init__(self, api_key: str, model: str = "grok-2-latest", **kwargs):
        """Initialize Grok provider."""
        super().__init__(api_key, model, **kwargs)
        self._client = None
        self.base_url = "https://api.x.ai/v1"
    
    def _get_client(self):
        """Lazy initialization of Grok client using OpenAI SDK."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def generate_json(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """Generate JSON from a prompt."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **kwargs
        )
        content = response.choices[0].message.content
        return json.loads(content)
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate response from chat messages."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content


class LLMClient:
    """
    Unified LLM client gateway.
    Manages multiple providers and provides a single interface.
    """
    
    def __init__(self):
        """Initialize LLM client."""
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
    
    def register_provider(self, name: str, provider: LLMProvider, set_default: bool = False) -> None:
        """
        Register a provider.
        
        Args:
            name: Name of the provider
            provider: Provider instance
            set_default: Whether to set as default provider
        """
        self.providers[name] = provider
        if set_default or self.default_provider is None:
            self.default_provider = name
    
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """
        Get a provider by name.
        
        Args:
            name: Provider name (uses default if None)
            
        Returns:
            Provider instance
        """
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
        return self.providers[provider_name]
    
    async def generate(self, prompt: str, provider: Optional[str] = None, agent: str = "unknown", **kwargs) -> str:
        """
        Generate text using a provider with token tracking.

        Args:
            prompt: Input prompt
            provider: Provider name (uses default if None)
            agent: Name of the agent making the call (for token tracking)
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        llm_provider = self.get_provider(provider)
        provider_name = provider or self.default_provider or "unknown"

        # Track tokens
        input_tokens = len(prompt) // 4
        result = await llm_provider.generate(prompt, **kwargs)
        output_tokens = len(result) // 4

        token_tracker.record_usage(provider_name, agent, input_tokens, output_tokens)
        token_tracker.check_limits()

        return result

    async def generate_json(self, prompt: str, provider: Optional[str] = None, agent: str = "unknown", **kwargs) -> Dict[str, Any]:
        """
        Generate JSON using a provider with token tracking.

        Args:
            prompt: Input prompt
            provider: Provider name (uses default if None)
            agent: Name of the agent making the call (for token tracking)
            **kwargs: Additional parameters

        Returns:
            Generated JSON as dictionary
        """
        llm_provider = self.get_provider(provider)
        provider_name = provider or self.default_provider or "unknown"

        # Track tokens
        input_tokens = len(prompt) // 4
        result = await llm_provider.generate_json(prompt, **kwargs)
        output_tokens = len(json.dumps(result)) // 4

        token_tracker.record_usage(provider_name, agent, input_tokens, output_tokens)
        token_tracker.check_limits()

        return result

    async def chat(self, messages: List[Dict[str, str]], provider: Optional[str] = None, agent: str = "unknown", **kwargs) -> str:
        """
        Generate response from chat messages with token tracking.

        Args:
            messages: List of message dictionaries
            provider: Provider name (uses default if None)
            agent: Name of the agent making the call (for token tracking)
            **kwargs: Additional parameters

        Returns:
            Generated response
        """
        llm_provider = self.get_provider(provider)
        provider_name = provider or self.default_provider or "unknown"

        # Track tokens
        input_text = "\n".join([m.get("content", "") for m in messages])
        input_tokens = len(input_text) // 4
        result = await llm_provider.chat(messages, **kwargs)
        output_tokens = len(result) // 4

        token_tracker.record_usage(provider_name, agent, input_tokens, output_tokens)
        token_tracker.check_limits()

        return result

    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self.providers.keys())

    def get_token_summary(self) -> Dict[str, Any]:
        """Get token usage summary."""
        return token_tracker.get_summary()

    def check_token_limits(self, max_tokens: int = 100000, max_cost: float = 1.0) -> bool:
        """Check if within token and cost limits."""
        return token_tracker.check_limits(max_tokens, max_cost)


# Global LLM client instance
llm_client = LLMClient()