#!/usr/bin/env python3
"""
Basic usage example for etcd-dynamic-config.

This example demonstrates:
1. Basic configuration loading
2. Accessing configuration values
3. Proper startup/shutdown handling
"""

import asyncio
import logging
import os

# Set environment variables BEFORE importing the package
os.environ["USE_LOCAL_CONFIG"] = "true"
os.environ["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
os.environ["CATEGORIZATION_API_URL"] = os.getenv(
    "CATEGORIZATION_API_URL", "http://localhost:8000/api"
)

from typing import Dict

from etcd_dynamic_config import BaseEtcdClient, etcd_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class DemoEtcdClient(BaseEtcdClient):
    """Demo custom client with minimal configuration."""

    def get_config_prefix(self) -> str:
        return "/demo/app"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            f"{base}/ApiUrl": "api_url",
            f"{base}/Debug": "debug_mode",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            "api_url": "DEMO_API_URL",
            "debug_mode": "DEMO_DEBUG",
        }


async def main():
    """Main application function."""
    print("🚀 Starting etcd-dynamic-config example...")

    # Check environment
    use_local = os.getenv("USE_LOCAL_CONFIG", "false").lower() == "true"
    etcd_host = os.getenv("EtcdSettings__HostName", "not set")

    print(f"📝 Configuration mode: {'Local' if use_local else 'etcd'}")
    print(f"🔗 Etcd endpoint: {etcd_host}")

    try:
        # Start configuration manager
        print("⚙️  Starting configuration manager...")
        success = await etcd_config.start()

        if not success:
            print("❌ Failed to start configuration manager")
            return

        print("✅ Configuration manager started successfully")

        # Get all configurations
        print("📋 Loading configurations...")
        configs = await etcd_config.get_all_configs()

        print(f"📊 Loaded {len(configs)} configuration keys")

        # Display some key configurations (works with any client)
        # Show first few available keys
        available_keys = list(configs.keys())[:5]  # Show first 5 keys
        key_configs = [(key, key.replace("_", " ").title()) for key in available_keys]

        print("\n🔍 Configuration values:")
        for key, description in key_configs:
            value = configs.get(key, "Not set")
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            print(f"  {description}: {value}")

        # Demonstrate periodic config checking
        print("\n⏰ Monitoring configuration for 30 seconds...")
        for i in range(6):
            await asyncio.sleep(5)

            # Check if log level changed
            current_configs = await etcd_config.get_all_configs()
            log_level = current_configs.get("log_level", "INFO")
            print(f"  [{i + 1}/6] Current log level: {log_level}")

        print("✅ Example completed successfully")

        # Demonstrate custom client
        print("\n🔧 Demonstrating custom client...")
        demo_client = DemoEtcdClient(use_local_config=True)

        # Set demo environment variables
        os.environ["DEMO_API_URL"] = "https://api.demo.com"
        os.environ["DEMO_DEBUG"] = "false"

        demo_config = demo_client.get_config()
        print("Custom client config:")
        print(f"  API URL: {demo_config.get('api_url')}")
        print(f"  Debug Mode: {demo_config.get('debug_mode')}")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        # Always cleanup
        print("🧹 Shutting down...")
        await etcd_config.stop()
        print("👋 Goodbye!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
