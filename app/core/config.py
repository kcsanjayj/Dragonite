"""
System configuration for the autonomous agent system.
Manages configuration settings, model providers, and workflow definitions.
"""

import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path


class Config:
    """
    System configuration manager.
    Loads and manages configuration from JSON files.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager."""
        if config_dir is None:
            # Default to config directory relative to project root
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self.providers: Dict[str, Any] = {}
        self.models: Dict[str, Any] = {}
        self.workflows: Dict[str, Any] = {}
        self.settings: Dict[str, Any] = {}
        
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load all configuration files."""
        try:
            # Load providers
            providers_file = self.config_dir / "providers.json"
            if providers_file.exists():
                with open(providers_file, 'r') as f:
                    self.providers = json.load(f)
            
            # Load models
            models_file = self.config_dir / "models.json"
            if models_file.exists():
                with open(models_file, 'r') as f:
                    self.models = json.load(f)
            
            # Load workflows
            workflow_file = self.config_dir / "workflow.json"
            if workflow_file.exists():
                with open(workflow_file, 'r') as f:
                    self.workflows = json.load(f)
            
            # Load settings from environment or defaults
            self.settings = {
                "max_replan_attempts": int(os.getenv("MAX_REPLAN_ATTEMPTS", "3")),
                "execution_timeout": int(os.getenv("EXECUTION_TIMEOUT", "300")),
                "tool_timeout": int(os.getenv("TOOL_TIMEOUT", "30")),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "enable_tracing": os.getenv("ENABLE_TRACING", "true").lower() == "true",
                "llm_temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
                "llm_max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
                "api_host": os.getenv("API_HOST", "localhost"),
                "api_port": int(os.getenv("API_PORT", "8000")),
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider configuration."""
        return self.providers.get(provider_name)
    
    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model configuration."""
        return self.models.get(model_name)
    
    def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow configuration."""
        return self.workflows.get(workflow_name)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def apply_temporary_config(self, config_data: Dict[str, Any]) -> None:
        """Apply temporary configuration from UI (API key, provider, model)."""
        provider = config_data.get('provider')
        api_key = config_data.get('api_key')
        model = config_data.get('model')
        
        if provider and api_key:
            # Update the provider with the API key
            if provider in self.providers:
                self.providers[provider]['api_key'] = api_key
                # Also set as env var for this session
                env_var_map = {
                    'openai': 'OPENAI_API_KEY',
                    'anthropic': 'ANTHROPIC_API_KEY',
                    'nvidia': 'NVIDIA_API_KEY',
                    'gemini': 'GEMINI_API_KEY',
                    'grok': 'GROK_API_KEY',
                    'huggingface': 'HUGGINGFACE_API_KEY'
                }
                env_var = env_var_map.get(provider)
                if env_var:
                    os.environ[env_var] = api_key
            
            # Update default model if provided
            if model and provider in self.models:
                self.models[provider]['default_model'] = model
    
    def get_all_providers(self) -> Dict[str, Any]:
        """Get all provider configurations."""
        return self.providers.copy()
    
    def get_all_models(self) -> Dict[str, Any]:
        """Get all model configurations."""
        return self.models.copy()
    
    def get_all_workflows(self) -> Dict[str, Any]:
        """Get all workflow configurations."""
        return self.workflows.copy()
    
    def reload(self) -> None:
        """Reload all configuration files."""
        self._load_configs()
    
    def validate(self) -> bool:
        """Validate configuration."""
        # Check that at least one provider is configured
        if not self.providers:
            raise ValueError("No providers configured")
        
        # Check that at least one model is configured
        if not self.models:
            raise ValueError("No models configured")
        
        # Check that at least one workflow is configured
        if not self.workflows:
            raise ValueError("No workflows configured")
        
        return True


# Global configuration instance
config = Config()