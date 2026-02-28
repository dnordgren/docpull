"""Configuration management for docpull."""

import json
import os
from pathlib import Path
from typing import Dict, Optional

DEFAULT_CONFIG = {
    "default_account": "personal",
    "accounts": {
        "personal": {
            "email": "",
            "image_dir": "~/Documents/docpull-images/personal"
        }
    }
}


class Config:
    """Manages configuration file and account settings."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path).expanduser()
        else:
            self.config_path = Path.home() / ".config" / "docpull.json"

        self.config = self._load_or_create()

    def _load_or_create(self) -> Dict:
        """Load existing config or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                self._validate_config(config)
                return config
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Invalid config file at {self.config_path}: {e}")
        else:
            return self._create_default_config()

    def _create_default_config(self) -> Dict:
        """Create default config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config = DEFAULT_CONFIG.copy()

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Created default config at {self.config_path}")
        print("Please edit the config file to set your email and image directory.")

        return config

    def _validate_config(self, config: Dict) -> None:
        """Validate config structure."""
        if "accounts" not in config:
            raise ValueError("Config missing 'accounts' key")

        if "default_account" not in config:
            raise ValueError("Config missing 'default_account' key")

        if config["default_account"] not in config["accounts"]:
            raise ValueError(f"Default account '{config['default_account']}' not found in accounts")

        for account_name, account_info in config["accounts"].items():
            if "image_dir" not in account_info:
                raise ValueError(f"Account '{account_name}' missing 'image_dir'")

    def get_account(self, account_name: Optional[str] = None) -> Dict:
        """Get account configuration.

        Args:
            account_name: Account name, or None to use default

        Returns:
            Account configuration dict

        Raises:
            ValueError: If account not found
        """
        if account_name is None:
            account_name = self.config["default_account"]

        if account_name not in self.config["accounts"]:
            available = ", ".join(self.config["accounts"].keys())
            raise ValueError(f"Account '{account_name}' not found. Available: {available}")

        return {
            "name": account_name,
            **self.config["accounts"][account_name]
        }

    def get_image_dir(self, account_name: Optional[str] = None) -> Path:
        """Get expanded image directory path for account."""
        account = self.get_account(account_name)
        return Path(account["image_dir"]).expanduser()

    def get_credentials_path(self, account_name: Optional[str] = None) -> Path:
        """Get path to credentials file for account."""
        account = self.get_account(account_name)
        creds_dir = Path.home() / ".config" / "docpull"
        creds_dir.mkdir(parents=True, exist_ok=True)
        return creds_dir / f"credentials-{account['name']}.json"
