#!/usr/bin/env python3
"""
Quick example of working with different prefixes.
Shows the main approaches to changing the base prefix.
"""

import os

from etcd_dynamic_config.core.control_unit import ControlUnitEtcdClient


class QuickCustomPrefixClient(ControlUnitEtcdClient):
    """Quick way to change the prefix."""

    def get_config_prefix(self) -> str:
        """Simply return our custom prefix."""
        return "/MyApp/Config"  # Your custom prefix


class DynamicPrefixClient(ControlUnitEtcdClient):
    """Prefix depends on environment variable."""

    def get_config_prefix(self) -> str:
        """Read prefix from environment variable."""
        custom_prefix = os.getenv("MY_APP_PREFIX", "/APPS/MyApp")
        return custom_prefix


# === Demonstration ===

if __name__ == "__main__":
    print("🚀 Quick examples of working with prefixes:")
    print()

    # 1. Fixed prefix
    print("1️⃣ Fixed prefix:")
    client1 = QuickCustomPrefixClient(use_local_config=True)
    print(f"   Prefix: {client1.get_config_prefix()}")
    print()

    # 2. Prefix from environment variable
    print("2️⃣ Prefix from environment variable:")

    # Without variable (default)
    client2a = DynamicPrefixClient(use_local_config=True)
    print(f"   Default: {client2a.get_config_prefix()}")

    # With variable
    os.environ["MY_APP_PREFIX"] = "/Production/MyService"
    client2b = DynamicPrefixClient(use_local_config=True)
    print(f"   With variable: {client2b.get_config_prefix()}")
    print()

    # 3. Show how this affects keys
    print("3️⃣ How prefix affects etcd keys:")

    # Create client with custom prefix
    os.environ["MY_APP_PREFIX"] = "/Test/App"
    client3 = DynamicPrefixClient(use_local_config=True)

    # Get key mapping
    key_map = client3.get_etcd_key_map()

    print(f"   Base prefix: {client3.get_config_prefix()}")
    print("   Example etcd keys:")

    # Show first few keys
    for i, (etcd_key, internal_name) in enumerate(list(key_map.items())[:3]):
        print(f"     {etcd_key} -> {internal_name}")

    print()
    print("✅ Done! Use the approach you need in your code.")
