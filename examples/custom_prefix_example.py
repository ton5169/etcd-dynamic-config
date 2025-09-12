#!/usr/bin/env python3
"""
Examples of different ways to work with custom prefixes in etcd.

Shows how to use different prefixes for different configuration groups.
"""

import os
from typing import Dict

from etcd_dynamic_config.core.control_unit import ControlUnitEtcdClient


class CustomPrefixClient(ControlUnitEtcdClient):
    """Client with fully custom prefix."""

    def get_config_prefix(self) -> str:
        """Override the prefix completely."""
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"
        # Use our custom prefix instead of /APPS/ControlUnit
        custom_prefix = os.getenv("CUSTOM_PREFIX", "/MyApp/Config")
        custom_prefix = custom_prefix.strip()

        if not custom_prefix.startswith("/"):
            custom_prefix = f"/{custom_prefix}"
        custom_prefix = custom_prefix.rstrip("/")

        return f"{'/dev' if dev_enabled else ''}{custom_prefix}"


class MultiPrefixClient(ControlUnitEtcdClient):
    """Client with support for multiple prefixes for different configuration groups."""

    def __init__(self, *args, **kwargs):
        # Define additional prefixes BEFORE calling super().__init__
        self._feature_prefix = "/Features"
        self._service_prefix = "/Services"
        super().__init__(*args, **kwargs)

    def get_feature_prefix(self) -> str:
        """Prefix for feature configurations."""
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"
        base = self.get_config_prefix()
        return f"{base}{self._feature_prefix}"

    def get_service_prefix(self) -> str:
        """Prefix for service configurations."""
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"
        base = self.get_config_prefix()
        return f"{base}{self._service_prefix}"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base_map = super()._build_etcd_key_map()
        base = self.get_config_prefix()

        # Regular configs (use main prefix)
        regular_configs = {
            f"{base}/CustomSetting": "custom_setting",
            f"{base}/AppVersion": "app_version",
        }

        # Feature configs (use feature prefix)
        feature_base = self.get_feature_prefix()
        feature_configs = {
            f"{feature_base}/EnableNewUI": "enable_new_ui",
            f"{feature_base}/BetaFeatures": "beta_features",
            f"{feature_base}/ExperimentalMode": "experimental_mode",
        }

        # Service configs (use service prefix)
        service_base = self.get_service_prefix()
        service_configs = {
            f"{service_base}/DatabaseHost": "database_host",
            f"{service_base}/RedisUrl": "redis_url",
            f"{service_base}/QueueName": "queue_name",
        }

        # Combine all mappings
        base_map.update(regular_configs)
        base_map.update(feature_configs)
        base_map.update(service_configs)

        return base_map

    def _build_env_var_map(self) -> Dict[str, str]:
        base_map = super()._build_env_var_map()

        new_env_vars = {
            # Regular configs
            "custom_setting": "CUSTOM_SETTING",
            "app_version": "APP_VERSION",
            # Feature configs
            "enable_new_ui": "ENABLE_NEW_UI",
            "beta_features": "BETA_FEATURES",
            "experimental_mode": "EXPERIMENTAL_MODE",
            # Service configs
            "database_host": "DATABASE_HOST",
            "redis_url": "REDIS_URL",
            "queue_name": "QUEUE_NAME",
        }

        base_map.update(new_env_vars)
        return base_map

    def _coerce_config_value(self, internal_name: str, value):
        # Special processing for new configs
        if internal_name in ("enable_new_ui", "beta_features", "experimental_mode"):
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)

        # For others - parent logic
        return super()._coerce_config_value(internal_name, value)


class EnvironmentBasedPrefixClient(ControlUnitEtcdClient):
    """Client that selects prefix based on environment variables."""

    def get_config_prefix(self) -> str:
        """Select prefix based on environment."""
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"

        # Determine prefix based on application type
        app_type = os.getenv("APP_TYPE", "control-unit").lower()

        if app_type == "web":
            root = "/APPS/WebService"
        elif app_type == "api":
            root = "/APPS/ApiGateway"
        elif app_type == "worker":
            root = "/APPS/BackgroundWorker"
        else:
            # Default to original prefix
            root = self._root_key or "/APPS/ControlUnit"

        root = root.strip()
        if not root.startswith("/"):
            root = f"/{root}"
        root = root.rstrip("/")

        return f"{'/dev' if dev_enabled else ''}{root}"


def demonstrate_custom_prefix():
    """Demonstration of working with custom prefixes."""
    print("🔧 Demonstration of working with custom prefixes...")

    # === Example 1: Fully custom prefix ===
    print("\n1️⃣ Custom prefix via environment variable:")

    os.environ["CUSTOM_PREFIX"] = "/MyCustom/App"
    client1 = CustomPrefixClient(use_local_config=True)
    print(f"   Prefix: {client1.get_config_prefix()}")

    # === Example 2: Multiple prefixes ===
    print("\n2️⃣ Multiple prefixes:")

    client2 = MultiPrefixClient(use_local_config=True)
    print(f"   Main prefix: {client2.get_config_prefix()}")
    print(f"   Feature prefix: {client2.get_feature_prefix()}")
    print(f"   Service prefix: {client2.get_service_prefix()}")

    # Show key mappings
    key_map = client2.get_etcd_key_map()
    print("\n   Example keys:")
    examples = [
        key
        for key in key_map.keys()
        if any(term in key for term in ["CustomSetting", "EnableNewUI", "DatabaseHost"])
    ][:3]
    for key in examples:
        print(f"     {key} -> {key_map[key]}")

    # === Example 3: Environment-based prefix ===
    print("\n3️⃣ Prefix based on application type:")

    test_cases = [
        ("control-unit", "ControlUnit"),
        ("web", "WebService"),
        ("api", "ApiGateway"),
        ("worker", "BackgroundWorker"),
    ]

    for app_type, expected_in_prefix in test_cases:
        os.environ["APP_TYPE"] = app_type
        client3 = EnvironmentBasedPrefixClient(use_local_config=True)
        prefix = client3.get_config_prefix()
        print(f"   APP_TYPE={app_type} -> {prefix}")

        # Check that prefix contains expected part
        if expected_in_prefix in prefix:
            print("     ✅ Correct prefix")
        else:
            print("     ❌ Unexpected prefix")

    print("\n✨ Demonstration completed!")


if __name__ == "__main__":
    demonstrate_custom_prefix()
