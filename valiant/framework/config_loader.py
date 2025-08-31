import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config = {}

    def load_configurations(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Load configurations with environment-specific overrides"""
        # Load base configuration
        base_config_path = Path(self.config_dir) / "application.yaml"
        if base_config_path.exists():
            self.config = self._load_yaml_file(base_config_path)

        # Load environment-specific configuration
        if environment:
            env_config_path = Path(self.config_dir) / f"application-{environment}.yaml"
            if env_config_path.exists():
                env_config = self._load_yaml_file(env_config_path)
                self._deep_merge(self.config, env_config)

        # Load environment variables (override file configs)
        self._load_environment_variables()

        return self.config

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Error loading config file {file_path}: {e}")
            return {}

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively merge dictionaries"""
        for key, value in update.items():
            if (key in base and isinstance(base[key], dict) and
                    isinstance(value, dict)):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _load_environment_variables(self) -> None:
        """Load environment variables with CONFIG_ prefix"""
        for key, value in os.environ.items():
            if key.startswith("CONFIG_"):
                config_key = key[7:].lower()  # Remove CONFIG_ prefix
                self._set_nested_value(self.config, config_key.split('__'), value)

    def _set_nested_value(self, config_dict: Dict[str, Any], key_path: list, value: Any) -> None:
        """Set nested value using key path (key1__key2__key3)"""
        if not key_path:
            return

        current = config_dict
        for key in key_path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[key_path[-1]] = self._cast_value(value)

    def _cast_value(self, value: str) -> Any:
        """Convert string values to appropriate types"""
        if isinstance(value, str):
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
        return value
