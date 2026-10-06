"""
CareMind Database Environment Configuration.

Loads Supabase connection parameters safely from environment variables without exposing secrets.
Automatically loads project root .env using python-dotenv.
"""

import os
from pathlib import Path
from typing import Optional

# Automatically locate and load project root .env
try:
    from dotenv import load_dotenv
    root_dir = Path(__file__).resolve().parent.parent.parent
    env_file = root_dir / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()
except ImportError:
    pass


class DatabaseConfig:
    """Database configuration container."""

    def __init__(self):
        self.supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
        self.supabase_key: Optional[str] = os.getenv("SUPABASE_KEY")
        self.supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    @property
    def is_supabase_configured(self) -> bool:
        """Returns True if valid Supabase URL and Key are configured."""
        return bool(
            self.supabase_url 
            and self.supabase_key 
            and "your-supabase-project" not in self.supabase_url
        )
