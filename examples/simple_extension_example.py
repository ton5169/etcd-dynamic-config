#!/usr/bin/env python3
"""
Простой пример расширения ControlUnitEtcdClient.

Показывает минимальный код для добавления новых конфигов.
"""

import os

from etcd_dynamic_config.core.control_unit import ControlUnitEtcdClient


class SimpleExtendedClient(ControlUnitEtcdClient):
    """Простое расширение с минимальным количеством новых конфигов."""

    def _build_etcd_key_map(self):
        base_map = super()._build_etcd_key_map()
        base = self.get_config_prefix()

        # Добавляем всего 2 новых конфига
        new_configs = {
            f"{base}/NewFeatureEnabled": "new_feature_enabled",
            f"{base}/NewFeatureUrl": "new_feature_url",
        }

        base_map.update(new_configs)
        return base_map

    def _build_env_var_map(self):
        base_map = super()._build_env_var_map()

        new_env_vars = {
            "new_feature_enabled": "NEW_FEATURE_ENABLED",
            "new_feature_url": "NEW_FEATURE_URL",
        }

        base_map.update(new_env_vars)
        return base_map

    def _coerce_config_value(self, internal_name, value):
        # Специальная обработка для новых конфигов
        if internal_name == "new_feature_enabled":
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on")
            return bool(value)

        # Для остальных - родительская логика
        return super()._coerce_config_value(internal_name, value)


if __name__ == "__main__":
    print("🔧 Простой пример расширения:")

    # Создаем клиент
    client = SimpleExtendedClient(use_local_config=True)

    # Устанавливаем тестовые значения
    os.environ["NEW_FEATURE_ENABLED"] = "true"
    os.environ["NEW_FEATURE_URL"] = "https://new-feature.api.com"

    # Получаем конфиг
    config = client.get_config()

    print("✅ Новые конфиги:")
    print(
        f"  new_feature_enabled: {config['new_feature_enabled']} ({type(config['new_feature_enabled']).__name__})"
    )
    print(
        f"  new_feature_url: {config['new_feature_url']} ({type(config['new_feature_url']).__name__})"
    )

    print("\n📊 Всего конфигураций:", len(config))
    print("✨ Готово!")
