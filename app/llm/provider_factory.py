"""
Provider factory for auto/manual model selection.
Manages provider initialization and model selection logic.
"""

from typing import Any, Dict, Optional
from .client import LLMProvider, OpenAIProvider, AnthropicProvider, NVIDIAProvider, GeminiProvider, HuggingFaceProvider, GrokProvider, llm_client
from ..core.config import config


class ProviderFactory:
    """
    Factory for creating and managing LLM providers.
    Supports auto and manual model selection.
    """
    
    def __init__(self):
        """Initialize provider factory."""
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all configured providers."""
        if self._initialized:
            return
        
        providers_config = config.get_all_providers()
        models_config = config.get_all_models()
        
        for provider_name, provider_config in providers_config.items():
            self._create_provider(provider_name, provider_config, models_config)
        
        self._initialized = True
    
    def _create_provider(self, name: str, provider_config: Dict[str, Any], models_config: Dict[str, Any]) -> None:
        """
        Create and register a provider.
        
        Args:
            name: Provider name
            provider_config: Provider configuration
            models_config: Available models configuration
        """
        provider_type = provider_config.get("type", "openai")
        api_key = provider_config.get("api_key")
        default_model = provider_config.get("default_model")
        
        if not api_key:
            print(f"Warning: No API key configured for provider '{name}', skipping")
            return
        
        # Get model-specific configuration if available
        model_config = models_config.get(default_model, {})
        
        # Create provider based on type
        if provider_type.lower() == "openai":
            provider = OpenAIProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        elif provider_type.lower() == "anthropic":
            provider = AnthropicProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        elif provider_type.lower() == "nvidia":
            provider = NVIDIAProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        elif provider_type.lower() == "gemini":
            provider = GeminiProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        elif provider_type.lower() == "huggingface":
            provider = HuggingFaceProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        elif provider_type.lower() == "grok":
            provider = GrokProvider(
                api_key=api_key,
                model=default_model,
                **model_config
            )
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        # Register as default if specified
        set_default = provider_config.get("default", False)
        llm_client.register_provider(name, provider, set_default=set_default)
    
    def auto_select_provider(self, task_type: str = "general") -> str:
        """
        Automatically select the best provider for a task type.
        
        Args:
            task_type: Type of task (general, code, analysis, etc.)
            
        Returns:
            Selected provider name
        """
        providers = llm_client.list_providers()
        
        if not providers:
            raise RuntimeError("No providers available")
        
        # Simple selection logic - can be enhanced
        # For now, return the default provider
        return llm_client.default_provider or providers[0]
    
    def auto_select_model(self, provider_name: str, task_type: str = "general") -> str:
        """
        Automatically select the best model for a task type.
        
        Args:
            provider_name: Provider name
            task_type: Type of task (general, code, analysis, etc.)
            
        Returns:
            Selected model name
        """
        provider = llm_client.get_provider(provider_name)
        return provider.model
    
    def get_provider_for_task(self, task_type: str = "general") -> LLMProvider:
        """
        Get the best provider for a task type.
        
        Args:
            task_type: Type of task (general, code, analysis, etc.)
            
        Returns:
            Provider instance
        """
        provider_name = self.auto_select_provider(task_type)
        return llm_client.get_provider(provider_name)
    
    def reload_providers(self) -> None:
        """Reload all providers from configuration."""
        # Clear existing providers
        llm_client.providers.clear()
        llm_client.default_provider = None
        
        # Reload configuration
        config.reload()
        
        # Reinitialize
        self._initialized = False
        self.initialize()
    
    def add_provider(self, name: str, provider_type: str, api_key: str, model: str, set_default: bool = False) -> None:
        """
        Add a new provider dynamically.
        
        Args:
            name: Provider name
            provider_type: Type of provider (openai, anthropic, nvidia, gemini, huggingface, grok)
            api_key: API key
            model: Model name
            set_default: Whether to set as default
        """
        # Reuse _create_provider logic to avoid duplication
        self._create_provider(
            name=name,
            provider_config={
                "type": provider_type,
                "api_key": api_key,
                "default_model": model,
                "default": set_default
            },
            models_config={}
        )
    
    def remove_provider(self, name: str) -> None:
        """
        Remove a provider.
        
        Args:
            name: Provider name to remove
        """
        if name in llm_client.providers:
            del llm_client.providers[name]
            
            if llm_client.default_provider == name:
                # Set a new default if available
                remaining = list(llm_client.providers.keys())
                llm_client.default_provider = remaining[0] if remaining else None


# Global provider factory instance
provider_factory = ProviderFactory()