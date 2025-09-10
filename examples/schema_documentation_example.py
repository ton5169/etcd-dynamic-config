#!/usr/bin/env python3
"""
Example showing how to document your custom configuration schema.

This example demonstrates:
1. Creating a custom client with your own configuration keys
2. Proper type coercion for different value types
3. Documentation of your configuration schema
4. Environment variable mapping
"""

import os
from typing import Dict

from etcd_dynamic_config import BaseEtcdClient


class SensitiveValue:
    """Wrapper for sensitive configuration values that should not be logged in plain text."""

    def __init__(self, value: str):
        self._value = value
        self._sensitive = True

    def __str__(self):
        # Return masked value for logging/display
        if len(self._value) <= 4:
            return "****"
        return "****" + self._value[-4:]

    def __repr__(self):
        return self.__str__()

    def get_value(self) -> str:
        """Get the actual sensitive value."""
        return self._value

    @property
    def sensitive(self) -> bool:
        """Check if this value is sensitive."""
        return self._sensitive


# Set up environment variables for demo
os.environ.update(
    {
        "USE_LOCAL_CONFIG": "true",
        "MYAPP_DB_HOST": "prod-database.company.com",
        "MYAPP_DB_PORT": "5432",
        "MYAPP_DB_NAME": "myapp_prod",
        "MYAPP_REDIS_URL": "redis://cache.company.com:6379",
        "MYAPP_API_SECRET": "sk-1234567890abcdef",
        "MYAPP_ENABLE_CACHE": "true",
        "MYAPP_LOG_LEVEL": "WARNING",
        "MYAPP_MAX_WORKERS": "10",
        "MYAPP_HEALTH_CHECK_INTERVAL": "30",
    }
)


class MyApplicationClient(BaseEtcdClient):
    """Custom etcd client for MyApplication with full schema documentation.

    Configuration Schema:
    =====================

    Etcd Keys -> Internal Names -> Environment Variables
    ---------------------------------------------------

    /myapp/prod/Database/Host      -> db_host          -> MYAPP_DB_HOST
    /myapp/prod/Database/Port      -> db_port          -> MYAPP_DB_PORT
    /myapp/prod/Database/Name      -> db_name          -> MYAPP_DB_NAME
    /myapp/prod/Cache/RedisUrl     -> redis_url        -> MYAPP_REDIS_URL
    /myapp/prod/API/SecretKey      -> api_secret       -> MYAPP_API_SECRET
    /myapp/prod/Features/Cache     -> enable_cache     -> MYAPP_ENABLE_CACHE
    /myapp/prod/Monitoring/LogLevel-> log_level        -> MYAPP_LOG_LEVEL
    /myapp/prod/Workers/MaxCount   -> max_workers      -> MYAPP_MAX_WORKERS
    /myapp/prod/HealthCheck/Interval-> health_interval -> MYAPP_HEALTH_CHECK_INTERVAL

    Types and Defaults:
    ------------------
    - db_host: str, default="localhost"
    - db_port: int, default=5432, range=[1024, 65535]
    - db_name: str, default="myapp"
    - redis_url: str, required
    - api_secret: str, sensitive (masked in logs)
    - enable_cache: bool, default=False
    - log_level: str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    - max_workers: int, default=4, range=[1, 100]
    - health_interval: int, default=60, range=[10, 300], unit=seconds
    """

    def get_config_prefix(self) -> str:
        """Get the etcd key prefix for MyApplication production environment."""
        return "/myapp/prod"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        """Map etcd keys to internal configuration names."""
        base = self.get_config_prefix()
        return {
            f"{base}/Database/Host": "db_host",
            f"{base}/Database/Port": "db_port",
            f"{base}/Database/Name": "db_name",
            f"{base}/Cache/RedisUrl": "redis_url",
            f"{base}/API/SecretKey": "api_secret",
            f"{base}/Features/Cache": "enable_cache",
            f"{base}/Monitoring/LogLevel": "log_level",
            f"{base}/Workers/MaxCount": "max_workers",
            f"{base}/HealthCheck/Interval": "health_interval",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        """Map internal names to environment variable names."""
        return {
            "db_host": "MYAPP_DB_HOST",
            "db_port": "MYAPP_DB_PORT",
            "db_name": "MYAPP_DB_NAME",
            "redis_url": "MYAPP_REDIS_URL",
            "api_secret": "MYAPP_API_SECRET",
            "enable_cache": "MYAPP_ENABLE_CACHE",
            "log_level": "MYAPP_LOG_LEVEL",
            "max_workers": "MYAPP_MAX_WORKERS",
            "health_interval": "MYAPP_HEALTH_CHECK_INTERVAL",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Apply type coercion with validation for MyApplication configuration."""
        if internal_name == "db_port":
            # Validate port range
            port = int(value) if value else 5432
            if not (1024 <= port <= 65535):
                raise ValueError(
                    f"Database port {port} is out of valid range [1024, 65535]"
                )
            return port

        elif internal_name == "max_workers":
            # Validate worker count
            workers = int(value) if value else 4
            if not (1 <= workers <= 100):
                raise ValueError(
                    f"Max workers {workers} is out of valid range [1, 100]"
                )
            return workers

        elif internal_name == "health_interval":
            # Validate health check interval
            interval = int(value) if value else 60
            if not (10 <= interval <= 300):
                raise ValueError(
                    f"Health check interval {interval} is out of valid range [10, 300] seconds"
                )
            return interval

        elif internal_name == "enable_cache":
            # Boolean conversion
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on", "enabled")
            return bool(value)

        elif internal_name == "log_level":
            # Validate log level
            if value:
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                level = str(value).upper()
                if level not in valid_levels:
                    raise ValueError(
                        f"Log level '{value}' is not valid. Use: {', '.join(valid_levels)}"
                    )
                return level
            return "INFO"

        elif internal_name == "api_secret":
            # Handle sensitive data - don't log in plain text
            secret = str(value) if value else ""
            # Return a special wrapper for sensitive data
            if secret:
                return SensitiveValue(secret)
            return secret

        elif internal_name in ("db_host", "db_name", "redis_url"):
            # String values with defaults
            if internal_name == "db_host":
                return str(value) if value else "localhost"
            elif internal_name == "db_name":
                return str(value) if value else "myapp"
            else:  # redis_url
                return str(value) if value else ""

        # Use default coercion for any other values
        return super()._coerce_config_value(internal_name, value)


def demonstrate_schema_documentation():
    """Demonstrate the custom client with full schema documentation."""
    print("📋 MyApplication Configuration Schema Documentation")
    print("=" * 60)

    # Create and configure client
    client = MyApplicationClient(use_local_config=True)

    print("\n🔑 Etcd Key Mappings:")
    print("-" * 30)
    for etcd_key, internal_name in client.get_etcd_key_map().items():
        print(f"  {etcd_key}")
        print(f"    → {internal_name}")

    print("\n🔧 Environment Variable Mappings:")
    print("-" * 35)
    for internal_name, env_var in client.get_env_var_map().items():
        print(f"  {internal_name} → {env_var}")

    print("\n📊 Configuration Values:")
    print("-" * 25)

    # Get configuration
    config = client.get_config()

    # Display configuration with types and descriptions
    schema_info = {
        "db_host": ("Database Host", "str", "localhost"),
        "db_port": ("Database Port", "int", "5432"),
        "db_name": ("Database Name", "str", "myapp"),
        "redis_url": ("Redis URL", "str", "required"),
        "api_secret": ("API Secret", "str", "sensitive"),
        "enable_cache": ("Enable Cache", "bool", "false"),
        "log_level": ("Log Level", "str", "INFO"),
        "max_workers": ("Max Workers", "int", "4"),
        "health_interval": ("Health Check Interval", "int", "60"),
    }

    for key, (description, expected_type, default_value) in schema_info.items():
        value = config.get(key, f"Not set (default: {default_value})")
        value_type = type(value).__name__

        # Handle sensitive data
        if isinstance(value, SensitiveValue):
            display_value = str(value)
            actual_value = value.get_value()
        else:
            display_value = str(value)
            actual_value = value

        print(f"  {description}:")
        print(f"    Value: {display_value}")
        print(f"    Type: {value_type} (expected: {expected_type})")
        print(f"    Key: {key}")
        print()

    print("✅ Schema documentation example completed!")


if __name__ == "__main__":
    demonstrate_schema_documentation()
