"""Configuration management for deep-mem"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_API_URL = "http://localhost:14243"
DEFAULT_TIMEOUT = 30.0

# Skill installation directory (where .env file is located)
SKILL_DIR = Path(__file__).parent.parent


class ConfigError(Exception):
    """Raised when configuration is invalid"""
    pass


@dataclass
class Config:
    """Configuration for deep-mem search

    Attributes:
        api_url: Nowledge Mem API endpoint
        auth_token: Bearer token for authentication
        timeout: Request timeout in seconds
    """
    api_url: str
    auth_token: str
    timeout: float = field(default=DEFAULT_TIMEOUT)

    def __post_init__(self):
        if not self.auth_token or self.auth_token.strip() == "":
            raise ConfigError(
                "MEM_AUTH_TOKEN is required. "
                "Set via environment variable or .env file in skill directory."
            )

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "Config":
        """Load configuration from environment

        Priority (highest to lowest):
            1. Explicit dotenv_path argument
            2. Existing environment variables
            3. .env file in skill installation directory
        """
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=False)
        else:
            # Load from skill directory .env file
            skill_env = SKILL_DIR / ".env"
            if skill_env.exists():
                load_dotenv(dotenv_path=skill_env, override=False)
            else:
                # Fallback to default dotenv behavior
                load_dotenv(override=False)

        return cls(
            api_url=os.getenv("MEM_API_URL", DEFAULT_API_URL),
            auth_token=os.getenv("MEM_AUTH_TOKEN", "").strip(),
            timeout=float(os.getenv("MEM_TIMEOUT", DEFAULT_TIMEOUT)),
        )
