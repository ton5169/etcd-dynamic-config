"""Etcd configuration manager with caching and watching capabilities."""

import asyncio
import builtins
import logging
import os
import threading
import time
from typing import Callable, Dict, Optional

try:
    from .client import EtcdClient, etcd_client
except ImportError:
    # Fallback for when modules are imported directly
    from client import EtcdClient, etcd_client

from .logging import setup_logging


class EtcdConfig:
    """Manages etcd-based configuration with caching and real-time updates.

    Features:
    - In-memory caching for performance
    - Real-time watching for configuration changes
    - Fallback to local environment variables
    - Thread-safe operations
    - Graceful error handling
    """

    def __init__(self, client=None) -> None:
        # Allow dependency injection of client
        if client is None:
            client = etcd_client

        self._client = client

        # In-memory cache for configs
        self._cache: Dict[str, builtins.object] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("etcd_dynamic_config.config")
        self._watch_cancel: Optional[Callable[[], None]] = None
        self._last_watcher_event_time = time.time()
        self._watcher_check_task: Optional[asyncio.Task] = None
        self._auth_error_detected = False

    def _load_initial(self) -> bool:
        """Load initial configuration from etcd. Returns True if successful."""
        # Validate etcd connection first
        if not self._client.validate_connection_settings():
            self._logger.error(
                "etcd_config_validation_failed",
                extra={
                    "event": {"category": ["config"], "action": "validation_failed"},
                    "etcd": {"validation_passed": False},
                },
            )
            return False

        try:
            # Synchronous initial load
            configs = self._client.get_config({})
            with self._lock:
                self._cache = dict(configs)
        except Exception as e:
            self._logger.error(
                "etcd_config_load_failed",
                extra={
                    "event": {"category": ["config"], "action": "load_failed"},
                    "error": {"message": str(e), "type": type(e).__name__},
                },
                exc_info=True,
            )
            return False
        # Enrich init log with diagnostic context
        endpoint = os.getenv("EtcdSettings__HostName", "")
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"
        root_key_env = os.getenv("EtcdSettings__RootKey")
        try:
            host, port, _ = EtcdClient._parse_host_port(endpoint)
        except Exception:
            host, port = None, None
        scheme = None
        if "://" in str(endpoint):
            try:
                scheme = str(endpoint).split("://", 1)[0].lower()
            except Exception:
                scheme = None
        tls_enabled = scheme == "https"
        prefix = self._client.get_config_prefix()
        key_map = self._client.get_etcd_key_map()
        expected_count = len(key_map)
        loaded_count = sum(
            1 for name in key_map.values() if configs.get(name) is not None
        )
        missing_names = [name for name in key_map.values() if configs.get(name) is None]
        sample_key = f"{prefix}/CleanupApiBaseUrl"
        # Log initialization result
        # For local config mode, success if we have at least some configs loaded
        # For etcd mode, require all expected configs to be loaded
        if self._client._use_local_config:
            success = loaded_count >= 0  # At least some config loaded
        else:
            success = loaded_count > 0 and loaded_count == expected_count
        log_level = "info" if success else "warning"
        getattr(self._logger, log_level)(
            "etcd_config_initialized",
            extra={
                "event": {"category": ["config"], "action": "initialized"},
                "etcd": {
                    "endpoint": endpoint,
                    "scheme": scheme,
                    "host": host,
                    "port": port,
                    "tls": tls_enabled,
                    "dev": dev_enabled,
                    "root_key_env": root_key_env,
                    "prefix": prefix,
                    "sample_key": sample_key,
                    "initialization_success": success,
                },
                "config": {
                    "keys_expected": expected_count,
                    "keys_loaded": loaded_count,
                    "keys_missing": missing_names,
                },
            },
        )

        return success

    async def start(self) -> bool:
        """Start etcd configuration manager. Returns True if successful."""
        # Initial load in a thread to avoid blocking loop with CPU-bound work
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, self._load_initial)

        if not success:
            self._logger.error(
                "etcd_config_start_failed",
                extra={
                    "event": {"category": ["config"], "action": "start_failed"},
                    "etcd": {"initial_load_success": False},
                },
            )
            return False

        # Check if using local config - skip watcher if so
        use_local_config = str(os.getenv("USE_LOCAL_CONFIG", "false")).lower() == "true"

        if use_local_config:
            self._logger.info(
                "etcd_config_started",
                extra={
                    "event": {"category": ["config"], "action": "started"},
                    "etcd": {
                        "watcher_started": False,
                        "mode": "local_env",
                    },
                },
            )
            return True

        # Attempt to start watcher for the control unit prefix (only for etcd mode)
        watcher_started = False
        try:
            prefix = self._client.get_config_prefix()

            cancel = self._client.start_watch_prefix(prefix, self._get_event_handler())
            if cancel is not None:
                self._watch_cancel = cancel
                watcher_started = True
        except Exception:
            self._logger.warning(
                "etcd_watcher_start_failed",
                extra={
                    "event": {"category": ["config"], "action": "watcher_start_failed"},
                    "etcd": {"watcher_enabled": False},
                },
                exc_info=True,
            )

        self._logger.info(
            "etcd_config_started",
            extra={
                "event": {"category": ["config"], "action": "started"},
                "etcd": {
                    "watcher_started": watcher_started,
                    "mode": "watch" if watcher_started else "stub",
                },
            },
        )

        # Start watcher health check task
        if watcher_started:
            self._watcher_check_task = asyncio.create_task(self._watcher_health_check())

        return True

    async def _watcher_health_check(self):
        """Periodically check if watcher is still receiving events and restart if needed."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                # If no events received in last 10 minutes, watcher might be dead
                time_since_last_event = time.time() - self._last_watcher_event_time
                if time_since_last_event > 600:  # 10 minutes
                    self._logger.debug(
                        "Watcher appears inactive, attempting restart",
                        extra={
                            "etcd": {
                                "time_since_last_event": int(time_since_last_event)
                            },
                            "event": {
                                "category": ["config"],
                                "action": "watcher_restart",
                            },
                        },
                    )

                    # Restart watcher
                    try:
                        if self._watch_cancel:
                            self._watch_cancel()
                            self._watch_cancel = None

                        # Force reconnection
                        self._client._client = None

                        # Restart watcher
                        prefix = self._client.get_config_prefix()
                        cancel = self._client.start_watch_prefix(
                            prefix, self._get_event_handler()
                        )
                        if cancel:
                            self._watch_cancel = cancel
                            self._last_watcher_event_time = time.time()
                            self._logger.debug(
                                "Watcher restarted successfully",
                                extra={
                                    "event": {
                                        "category": ["config"],
                                        "action": "watcher_restarted",
                                    }
                                },
                            )
                    except Exception:
                        self._logger.error(
                            "Failed to restart watcher",
                            exc_info=True,
                            extra={
                                "event": {
                                    "category": ["config"],
                                    "action": "watcher_restart_failed",
                                }
                            },
                        )

            except asyncio.CancelledError:
                break
            except Exception:
                self._logger.warning(
                    "watcher_health_check_error",
                    extra={
                        "event": {
                            "category": ["config"],
                            "action": "health_check_error",
                        },
                        "etcd": {"watcher_active": True},
                    },
                    exc_info=True,
                )

    def _get_event_handler(self):
        """Get the event handler function for watcher."""

        def _on_event(absolute_key: str) -> None:
            try:
                # Update last event time
                self._last_watcher_event_time = time.time()

                self._logger.info(
                    "etcd_watch_event",
                    extra={
                        "event": {"category": ["config"], "action": "watch_event"},
                        "etcd": {"key": absolute_key},
                    },
                )
                # Only handle keys we care about
                key_map = self._client.get_etcd_key_map()
                internal_name = key_map.get(absolute_key)
                if not internal_name:
                    self._logger.debug(
                        "etcd_watch_event_skipped",
                        extra={"etcd": {"key": absolute_key}},
                    )
                    return
                values = self._client.get_values_by_keys([absolute_key])
                raw_value = values.get(absolute_key)

                # Apply the same type coercion as in get_control_unit_config
                processed_value = raw_value
                if internal_name in (
                    "log_sql_echo",
                    "use_fake_externals_discord",
                    "use_fake_externals_ai",
                    "cleanup_start",
                    "ai_categorization_debug",
                    "ai_recommendation_debug",
                ):
                    if isinstance(raw_value, str):
                        lowered = raw_value.strip().lower()
                        processed_value = lowered in ("1", "true", "yes", "y", "on")
                    processed_value = (
                        bool(processed_value) if processed_value is not None else False
                    )
                elif internal_name == "closed_statuses":
                    if isinstance(raw_value, str):
                        processed_value = tuple(
                            s.strip() for s in raw_value.split(",") if s.strip()
                        )
                    elif isinstance(raw_value, (list, tuple)):
                        processed_value = tuple(raw_value)
                    else:
                        processed_value = (
                            tuple() if raw_value is None else (str(raw_value),)
                        )
                elif internal_name in (
                    "ai_http_timeout_seconds",
                    "ai_http_max_connections",
                    "ai_http_max_keepalive_connections",
                ):
                    if internal_name == "ai_http_timeout_seconds":
                        try:
                            processed_value = (
                                float(raw_value) if raw_value is not None else 30.0
                            )
                        except (ValueError, TypeError):
                            processed_value = 30.0
                    else:  # connection limits
                        try:
                            processed_value = (
                                int(raw_value)
                                if raw_value is not None
                                else (10 if "max_connections" in internal_name else 5)
                            )
                        except (ValueError, TypeError):
                            processed_value = (
                                10 if "max_connections" in internal_name else 5
                            )

                with self._lock:
                    self._cache[internal_name] = processed_value

                self._logger.info(
                    "etcd_config_key_updated",
                    extra={
                        "event": {"category": ["config"], "action": "key_updated"},
                        "etcd": {
                            "key": absolute_key,
                            "internal_name": internal_name,
                        },
                    },
                )

                # Apply dynamic log level changes immediately
                if internal_name in ("log_level", "log_sql_level"):
                    try:
                        # Read both levels from cache (with fallback defaults)
                        level = str(self._cache.get("log_level", "INFO")).upper()
                        sql_level = str(
                            self._cache.get("log_sql_level", "WARNING")
                        ).upper()
                        setup_logging(
                            level,
                            sql_level=sql_level,
                            application_name="GsControlUnit",
                        )
                        self._logger.info(
                            "log_levels_reconfigured",
                            extra={
                                "event": {
                                    "category": ["config"],
                                    "action": "log_reconfigured",
                                },
                                "logging": {"level": level, "sql_level": sql_level},
                            },
                        )
                    except Exception:
                        self._logger.warning(
                            "log_level_apply_failed",
                            extra={
                                "event": {
                                    "category": ["config"],
                                    "action": "log_reconfigure_failed",
                                },
                                "logging": {"level": level, "sql_level": sql_level},
                            },
                            exc_info=True,
                        )
            except Exception as e:
                self._logger.warning(
                    "etcd_config_watch_callback_failed",
                    extra={
                        "event": {
                            "category": ["config"],
                            "action": "watch_cb_failed",
                        },
                        "error": {"message": str(e), "type": type(e).__name__},
                    },
                    exc_info=True,
                )

        return _on_event

    async def stop(self) -> None:
        try:
            if self._watcher_check_task is not None:
                self._watcher_check_task.cancel()
                try:
                    await self._watcher_check_task
                except asyncio.CancelledError:
                    pass
                self._watcher_check_task = None

            if self._watch_cancel is not None:
                self._watch_cancel()
                self._watch_cancel = None
        finally:
            return None

    async def get_all_configs(self) -> dict:
        # Return a copy to protect internal dict
        with self._lock:
            if self._cache:
                # Cache hit: return immediately and log it
                try:
                    self._logger.debug(
                        "etcd_config_cache_hit",
                        extra={
                            "event": {"category": ["config"], "action": "cache_hit"},
                            "config": {"keys_loaded": len(self._cache)},
                        },
                    )
                except Exception:
                    pass
                return dict(self._cache)
        # Fallback: if cache empty (e.g., before start), load synchronously in executor
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: self._client.get_config({})
            )
            with self._lock:
                if not self._cache:
                    self._cache = dict(result)
                    # Cache miss: populated from etcd synchronously
                    try:
                        self._logger.info(
                            "etcd_config_cache_miss_loaded",
                            extra={
                                "event": {
                                    "category": ["config"],
                                    "action": "cache_miss_loaded",
                                },
                                "config": {"keys_loaded": len(self._cache)},
                            },
                        )
                    except Exception:
                        pass
            return dict(self._cache)
        except Exception as e:
            self._logger.error(
                "etcd_config_fallback_failed",
                extra={
                    "event": {"category": ["config"], "action": "fallback_failed"},
                    "error": {"message": str(e), "type": type(e).__name__},
                },
                exc_info=True,
            )
            return {}


# Create default instance
etcd_config = EtcdConfig()

__all__ = ["EtcdConfig", "etcd_config"]
