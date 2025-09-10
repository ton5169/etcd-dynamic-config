#!/usr/bin/env python3
"""
Advanced usage example showing dependency injection and custom clients.

This example demonstrates:
1. Creating custom etcd clients
2. Dependency injection in EtcdConfig
3. Multiple client configurations
4. Type coercion customization
"""

import asyncio
import logging
import os
from typing import Dict

from etcd_dynamic_config import BaseEtcdClient, EtcdConfig

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set environment variables
os.environ["USE_LOCAL_CONFIG"] = "true"


class ProductionEtcdClient(BaseEtcdClient):
    """Production-ready etcd client with enhanced type coercion."""

    def get_config_prefix(self) -> str:
        return "/production/myapp"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            f"{base}/DatabaseUrl": "database_url",
            f"{base}/CacheUrl": "cache_url",
            f"{base}/QueueUrl": "queue_url",
            f"{base}/ApiSecret": "api_secret",
            f"{base}/MaxConnections": "max_connections",
            f"{base}/EnableCache": "enable_cache",
            f"{base}/LogLevel": "log_level",
            f"{base}/HealthCheckInterval": "health_check_interval",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            "database_url": "PROD_DATABASE_URL",
            "cache_url": "PROD_CACHE_URL",
            "queue_url": "PROD_QUEUE_URL",
            "api_secret": "PROD_API_SECRET",
            "max_connections": "PROD_MAX_CONNECTIONS",
            "enable_cache": "PROD_ENABLE_CACHE",
            "log_level": "PROD_LOG_LEVEL",
            "health_check_interval": "PROD_HEALTH_CHECK_INTERVAL",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Enhanced type coercion for production environment."""
        if internal_name == "max_connections":
            try:
                return max(1, min(100, int(value))) if value else 10
            except (ValueError, TypeError):
                return 10
        elif internal_name == "enable_cache":
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on", "enabled")
            return bool(value)
        elif internal_name == "health_check_interval":
            try:
                interval = int(value) if value else 30
                return max(5, min(300, interval))  # Between 5 and 300 seconds
            except (ValueError, TypeError):
                return 30
        elif internal_name == "api_secret":
            # Never log secrets
            return str(value) if value else ""

        # Use default coercion for other values
        return super()._coerce_config_value(internal_name, value)


class StagingEtcdClient(BaseEtcdClient):
    """Staging environment client with different defaults."""

    def get_config_prefix(self) -> str:
        return "/staging/myapp"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            f"{base}/DatabaseUrl": "database_url",
            f"{base}/CacheUrl": "cache_url",
            f"{base}/EnableDebug": "enable_debug",
            f"{base}/LogLevel": "log_level",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            "database_url": "STAGING_DATABASE_URL",
            "cache_url": "STAGING_CACHE_URL",
            "enable_debug": "STAGING_ENABLE_DEBUG",
            "log_level": "STAGING_LOG_LEVEL",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Staging-specific coercion with debug defaults."""
        if internal_name == "enable_debug":
            # In staging, debug is enabled by default
            if value is None:
                return True
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on", "enabled")
            return bool(value)

        return super()._coerce_config_value(internal_name, value)


async def demonstrate_dependency_injection():
    """Demonstrate dependency injection with custom clients."""
    print("🚀 Advanced EtcdConfig usage with dependency injection")
    print("=" * 60)

    # Set up environment variables for both environments
    os.environ.update(
        {
            "PROD_DATABASE_URL": "postgresql://prod_user:prod_pass@prod-db:5432/prod_db",
            "PROD_CACHE_URL": "redis://prod-cache:6379",
            "PROD_MAX_CONNECTIONS": "50",
            "PROD_ENABLE_CACHE": "true",
            "PROD_LOG_LEVEL": "WARNING",
            "PROD_HEALTH_CHECK_INTERVAL": "60",
            "STAGING_DATABASE_URL": "postgresql://staging_user:staging_pass@staging-db:5432/staging_db",
            "STAGING_CACHE_URL": "redis://staging-cache:6379",
            "STAGING_LOG_LEVEL": "DEBUG",
        }
    )

    print("\n🏭 PRODUCTION ENVIRONMENT:")
    print("-" * 30)

    # Create production client
    prod_client = ProductionEtcdClient(use_local_config=True)

    # Create EtcdConfig with dependency injection
    prod_config = EtcdConfig(client=prod_client)

    await prod_config.start()
    prod_configs = await prod_config.get_all_configs()

    print("Production configuration:")
    for key, value in prod_configs.items():
        if "secret" in key.lower():
            print(f"  {key}: {'*' * 12}")
        else:
            print(f"  {key}: {value} ({type(value).__name__})")

    await prod_config.stop()

    print("\n🧪 STAGING ENVIRONMENT:")
    print("-" * 30)

    # Create staging client
    staging_client = StagingEtcdClient(use_local_config=True)

    # Create EtcdConfig with staging client
    staging_config = EtcdConfig(client=staging_client)

    await staging_config.start()
    staging_configs = await staging_config.get_all_configs()

    print("Staging configuration:")
    for key, value in staging_configs.items():
        print(f"  {key}: {value} ({type(value).__name__})")

    await staging_config.stop()

    print("\n🎯 COMPARISON:")
    print("-" * 30)

    # Compare configurations
    all_keys = set(prod_configs.keys()) | set(staging_configs.keys())

    for key in sorted(all_keys):
        prod_value = prod_configs.get(key, "Not set")
        staging_value = staging_configs.get(key, "Not set")
        diff = "← Different" if prod_value != staging_value else ""
        print(f"  {key}:")
        print(f"    Prod: {prod_value}")
        print(f"    Staging: {staging_value} {diff}")

    print("\n✅ Dependency injection demonstration completed!")


async def demonstrate_client_switching():
    """Demonstrate switching between different clients at runtime."""
    print("\n🔄 CLIENT SWITCHING DEMONSTRATION:")
    print("=" * 40)

    # Start with production client
    prod_client = ProductionEtcdClient(use_local_config=True)
    config_manager = EtcdConfig(client=prod_client)

    await config_manager.start()
    configs = await config_manager.get_all_configs()
    print(f"With Production client: {len(configs)} config keys")
    print(f"  Max connections: {configs.get('max_connections')}")

    await config_manager.stop()

    # Switch to staging client
    staging_client = StagingEtcdClient(use_local_config=True)
    config_manager = EtcdConfig(client=staging_client)

    await config_manager.start()
    configs = await config_manager.get_all_configs()
    print(f"With Staging client: {len(configs)} config keys")
    print(f"  Debug enabled: {configs.get('enable_debug')}")

    await config_manager.stop()

    print("✅ Client switching demonstration completed!")


async def main():
    """Main demonstration function."""
    await demonstrate_dependency_injection()
    await demonstrate_client_switching()


if __name__ == "__main__":
    asyncio.run(main())
