#!/usr/bin/env python3
"""
Example of creating a custom etcd client for your application.

This example shows how to extend BaseEtcdClient to create a client
with your own configuration keys and mappings.
"""

import asyncio
import os
from typing import Dict

# Configure logging with ECS formatting first
from etcd_dynamic_config.core.logging import setup_logging

setup_logging(level="INFO")

from etcd_dynamic_config import BaseEtcdClient


class MyAppEtcdClient(BaseEtcdClient):
    """Custom etcd client for MyApp with specific configuration keys."""

    def get_config_prefix(self) -> str:
        """Get the etcd key prefix for MyApp."""
        env = os.getenv("ENVIRONMENT", "dev")
        return f"/apps/myapp/{env}"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        """Build etcd key mappings for MyApp."""
        base = self.get_config_prefix()
        return {
            f"{base}/DatabaseUrl": "database_url",
            f"{base}/RedisUrl": "redis_url",
            f"{base}/ApiKey": "api_key",
            f"{base}/DebugMode": "debug_mode",
            f"{base}/MaxWorkers": "max_workers",
            f"{base}/LogLevel": "log_level",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        """Build environment variable mappings for MyApp."""
        return {
            "database_url": "MYAPP_DATABASE_URL",
            "redis_url": "MYAPP_REDIS_URL",
            "api_key": "MYAPP_API_KEY",
            "debug_mode": "MYAPP_DEBUG_MODE",
            "max_workers": "MYAPP_MAX_WORKERS",
            "log_level": "MYAPP_LOG_LEVEL",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Apply MyApp-specific type coercion."""
        # Custom type coercion for your application
        if internal_name == "debug_mode":
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)
        elif internal_name == "max_workers":
            try:
                return int(value) if value is not None else 4
            except (ValueError, TypeError):
                return 4
        elif internal_name in ("database_url", "redis_url"):
            return str(value) if value is not None else ""

        # For other values, use default behavior
        return super()._coerce_config_value(internal_name, value)


async def main():
    """Demonstrate custom client usage."""
    print("🚀 Starting custom etcd client example...")

    # Create custom client
    client = MyAppEtcdClient(
        endpoint="http://localhost:2379",
        use_local_config=True,  # Use env vars for demo
    )

    # Show key mappings
    print("\n🔑 Etcd Key Mappings:")
    for etcd_key, internal_name in client.get_etcd_key_map().items():
        print(f"  {etcd_key} -> {internal_name}")

    print("\n🔧 Environment Variable Mappings:")
    for internal_name, env_var in client.get_env_var_map().items():
        print(f"  {internal_name} -> {env_var}")

    # Set some example environment variables
    os.environ["MYAPP_DATABASE_URL"] = "postgresql://user:pass@localhost:5432/myapp"
    os.environ["MYAPP_REDIS_URL"] = "redis://localhost:6379"
    os.environ["MYAPP_API_KEY"] = "sk-1234567890abcdef"
    os.environ["MYAPP_DEBUG_MODE"] = "true"
    os.environ["MYAPP_MAX_WORKERS"] = "8"
    os.environ["MYAPP_LOG_LEVEL"] = "INFO"

    # Get configuration
    print("\n📋 Loading configuration...")
    config = client.get_config()

    print("\n🔍 Configuration values:")
    for key, value in config.items():
        if "key" in key.lower() or "token" in key.lower():
            # Mask sensitive values
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")

    # Demonstrate custom type coercion
    print("\n✅ Type coercion examples:")
    print(
        f"  debug_mode: {config.get('debug_mode')} (type: {type(config.get('debug_mode'))})"
    )
    print(
        f"  max_workers: {config.get('max_workers')} (type: {type(config.get('max_workers'))})"
    )
    print(
        f"  database_url: {config.get('database_url')} (type: {type(config.get('database_url'))})"
    )

    print("\n✅ Custom client example completed!")


if __name__ == "__main__":
    asyncio.run(main())
