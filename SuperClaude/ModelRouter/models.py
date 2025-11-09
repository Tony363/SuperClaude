"""
Model configurations and specifications for SuperClaude Framework.

Defines model capabilities, optimal use cases, and configuration management.
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
import logging

try:  # Optional dependency for YAML config handling
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional at runtime
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str
    api_key_env: str
    endpoint: Optional[str] = None
    version: Optional[str] = None
    temperature_default: float = 0.7
    max_tokens_default: int = 4096
    rate_limit_rpm: int = 60  # Requests per minute
    rate_limit_tpm: int = 1000000  # Tokens per minute
    supports_streaming: bool = True
    supports_functions: bool = True
    timeout_seconds: int = 300
    retry_attempts: int = 3
    extra_params: Dict[str, Any] = field(default_factory=dict)


class ModelManager:
    """
    Manages model configurations and capabilities.

    Features:
    - Configuration loading from YAML/JSON
    - Environment variable management
    - API key validation
    - Model capability queries
    """

    DEFAULT_CONFIGS = {
        'gpt-5': ModelConfig(
            name='gpt-5',
            provider='openai',
            api_key_env='OPENAI_API_KEY',
            endpoint='https://api.openai.com/v1',
            version='gpt-5',
            temperature_default=0.7,
            max_tokens_default=50000,
            rate_limit_rpm=50,
            rate_limit_tpm=2000000
        ),
        'gpt-4.1': ModelConfig(
            name='gpt-4.1',
            provider='openai',
            api_key_env='OPENAI_API_KEY',
            endpoint='https://api.openai.com/v1',
            version='gpt-4.1',
            temperature_default=0.7,
            max_tokens_default=50000,
            rate_limit_rpm=100,
            rate_limit_tpm=1000000
        ),
        'gpt-4o': ModelConfig(
            name='gpt-4o',
            provider='openai',
            api_key_env='OPENAI_API_KEY',
            endpoint='https://api.openai.com/v1',
            version='gpt-4o',
            temperature_default=0.7,
            max_tokens_default=4096,
            rate_limit_rpm=500,
            rate_limit_tpm=1000000
        ),
        'gpt-4o-mini': ModelConfig(
            name='gpt-4o-mini',
            provider='openai',
            api_key_env='OPENAI_API_KEY',
            endpoint='https://api.openai.com/v1',
            version='gpt-4o-mini',
            temperature_default=0.7,
            max_tokens_default=4096,
            rate_limit_rpm=500,
            rate_limit_tpm=500000
        ),
        'claude-opus-4.1': ModelConfig(
            name='claude-opus-4.1',
            provider='anthropic',
            api_key_env='ANTHROPIC_API_KEY',
            endpoint='https://api.anthropic.com/v1',
            version='claude-opus-4-1-20250805',
            temperature_default=0.7,
            max_tokens_default=4096,
            rate_limit_rpm=100,
            rate_limit_tpm=400000
        ),
        'gemini-2.5-pro': ModelConfig(
            name='gemini-2.5-pro',
            provider='google',
            api_key_env='GOOGLE_API_KEY',
            endpoint='https://generativelanguage.googleapis.com/v1beta',
            version='gemini-2.5-pro',
            temperature_default=0.7,
            max_tokens_default=8192,
            rate_limit_rpm=60,
            rate_limit_tpm=2000000
        ),
        'grok-4': ModelConfig(
            name='grok-4',
            provider='xai',
            api_key_env='XAI_API_KEY',
            endpoint='https://api.x.ai/v1',
            version='grok-4',
            temperature_default=0.7,
            max_tokens_default=8192,
            rate_limit_rpm=100,
            rate_limit_tpm=500000
        ),
        'grok-code-fast-1': ModelConfig(
            name='grok-code-fast-1',
            provider='xai',
            api_key_env='XAI_API_KEY',
            endpoint='https://api.x.ai/v1',
            version='grok-code-fast-1',
            temperature_default=0.5,
            max_tokens_default=4096,
            rate_limit_rpm=200,
            rate_limit_tpm=500000
        )
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize model manager.

        Args:
            config_path: Path to configuration file
        """
        self.configs: Dict[str, ModelConfig] = {}
        self.config_path = config_path

        # Load default configurations
        self.configs.update(self.DEFAULT_CONFIGS.copy())

        # Load user configurations
        if config_path:
            self.load_config(config_path)
        else:
            # Try to load from standard locations
            self._load_standard_configs()

    def _load_standard_configs(self) -> None:
        """Load configurations from standard locations."""
        config_locations = [
            Path.home() / '.claude' / 'models.yaml',
            Path.home() / '.claude' / 'models.json',
            Path.cwd() / 'models.yaml',
            Path.cwd() / 'models.json',
            Path('/etc/superclaud') / 'models.yaml'
        ]

        for location in config_locations:
            if location.exists():
                try:
                    self.load_config(str(location))
                    logger.info(f"Loaded model config from {location}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load config from {location}: {e}")

    def load_config(self, path: str) -> None:
        """
        Load configuration from file.

        Args:
            path: Path to configuration file (YAML or JSON)
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, 'r') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                if yaml is None:
                    raise RuntimeError("PyYAML is required to load YAML model configs")
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Parse configurations
        if 'models' in data:
            for model_name, model_data in data['models'].items():
                config = ModelConfig(
                    name=model_name,
                    provider=model_data.get('provider', 'unknown'),
                    api_key_env=model_data.get('api_key_env', f'{model_name.upper()}_API_KEY'),
                    endpoint=model_data.get('endpoint'),
                    version=model_data.get('version'),
                    temperature_default=model_data.get('temperature_default', 0.7),
                    max_tokens_default=model_data.get('max_tokens_default', 4096),
                    rate_limit_rpm=model_data.get('rate_limit_rpm', 60),
                    rate_limit_tpm=model_data.get('rate_limit_tpm', 1000000),
                    supports_streaming=model_data.get('supports_streaming', True),
                    supports_functions=model_data.get('supports_functions', True),
                    timeout_seconds=model_data.get('timeout_seconds', 300),
                    retry_attempts=model_data.get('retry_attempts', 3),
                    extra_params=model_data.get('extra_params', {})
                )
                self.configs[model_name] = config

        # Load environment overrides
        if 'environment' in data:
            self._apply_environment_overrides(data['environment'])

    def _apply_environment_overrides(self, env_config: Dict[str, Any]) -> None:
        """Apply environment-based configuration overrides."""
        current_env = os.getenv('SUPERCLAUD_ENV', 'development')

        if current_env in env_config:
            overrides = env_config[current_env]
            for model_name, model_overrides in overrides.items():
                if model_name in self.configs:
                    config = self.configs[model_name]
                    for key, value in model_overrides.items():
                        if hasattr(config, key):
                            setattr(config, key, value)

    def get_config(self, model_name: str) -> Optional[ModelConfig]:
        """
        Get configuration for a model.

        Args:
            model_name: Name of the model

        Returns:
            ModelConfig or None if not found
        """
        return self.configs.get(model_name)

    def has_api_key(self, model_name: str) -> bool:
        """
        Check if API key is available for model.

        Args:
            model_name: Name of the model

        Returns:
            True if API key is set
        """
        config = self.get_config(model_name)
        if not config:
            return False

        return bool(os.getenv(config.api_key_env))

    def get_available_models(self) -> List[str]:
        """
        Get list of models with available API keys.

        Returns:
            List of available model names
        """
        available = []
        for model_name, config in self.configs.items():
            if self.has_api_key(model_name):
                available.append(model_name)
        return available

    def get_provider_models(self, provider: str) -> List[str]:
        """
        Get all models from a specific provider.

        Args:
            provider: Provider name (openai, anthropic, google, xai)

        Returns:
            List of model names from provider
        """
        models = []
        for model_name, config in self.configs.items():
            if config.provider.lower() == provider.lower():
                models.append(model_name)
        return models

    def update_config(self, model_name: str, **kwargs) -> None:
        """
        Update configuration for a model.

        Args:
            model_name: Name of the model
            **kwargs: Configuration parameters to update
        """
        if model_name not in self.configs:
            raise ValueError(f"Model {model_name} not found")

        config = self.configs[model_name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                config.extra_params[key] = value

    def save_config(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to file.

        Args:
            path: Path to save configuration (defaults to loaded path)
        """
        save_path = path or self.config_path
        if not save_path:
            save_path = str(Path.home() / '.claude' / 'models.yaml')

        # Convert configs to dictionary
        config_dict = {'models': {}}
        for model_name, config in self.configs.items():
            config_dict['models'][model_name] = asdict(config)

        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Save based on extension
        with open(save_path, 'w') as f:
            if save_path.endswith('.yaml') or save_path.endswith('.yml'):
                if yaml is None:
                    raise RuntimeError("PyYAML is required to save YAML model configs")
                yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)

        logger.info(f"Configuration saved to {save_path}")

    def validate_configs(self) -> Dict[str, List[str]]:
        """
        Validate all configurations.

        Returns:
            Dictionary of model names to list of issues
        """
        issues = {}

        for model_name, config in self.configs.items():
            model_issues = []

            # Check API key
            if not self.has_api_key(model_name):
                model_issues.append(f"API key not set ({config.api_key_env})")

            # Check endpoint
            if not config.endpoint:
                model_issues.append("Endpoint not configured")

            # Check rate limits
            if config.rate_limit_rpm <= 0:
                model_issues.append("Invalid rate limit (RPM)")

            if config.rate_limit_tpm <= 0:
                model_issues.append("Invalid rate limit (TPM)")

            # Check token limits
            if config.max_tokens_default <= 0:
                model_issues.append("Invalid max tokens")

            if model_issues:
                issues[model_name] = model_issues

        return issues

    def export_manifest(self) -> Dict[str, Any]:
        """
        Export configuration manifest.

        Returns:
            Dictionary with all model configurations
        """
        manifest = {
            'version': '1.0.0',
            'total_models': len(self.configs),
            'providers': {},
            'models': {}
        }

        # Group by provider
        for model_name, config in self.configs.items():
            provider = config.provider
            if provider not in manifest['providers']:
                manifest['providers'][provider] = []
            manifest['providers'][provider].append(model_name)

            # Add model details
            manifest['models'][model_name] = {
                'provider': config.provider,
                'has_api_key': self.has_api_key(model_name),
                'endpoint': config.endpoint,
                'max_tokens': config.max_tokens_default,
                'rate_limits': {
                    'rpm': config.rate_limit_rpm,
                    'tpm': config.rate_limit_tpm
                }
            }

        return manifest
