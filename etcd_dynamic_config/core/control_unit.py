"""ControlUnit-specific etcd client implementation."""

import builtins
import os
from typing import Dict

from .base import BaseEtcdClient


class ControlUnitEtcdClient(BaseEtcdClient):
    """Etcd client specifically configured for ControlUnit application.

    This class provides the concrete implementation for ControlUnit's
    configuration management with predefined key mappings.
    """

    def get_config_prefix(self) -> str:
        """Get the etcd key prefix for ControlUnit."""
        dev_enabled = str(os.getenv("EtcdSettings__Dev", "false")).lower() == "true"
        root = self._root_key or "/APPS/ControlUnit"
        root = root.strip()
        if not root.startswith("/"):
            root = f"/{root}"
        root = root.rstrip("/")
        return f"{'/dev' if dev_enabled else ''}{root}"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        """Build etcd key mappings for ControlUnit."""
        base = self.get_config_prefix()
        return {
            f"{base}/CategorizationApiUrl": "categorization_api_url",
            f"{base}/CategorizationApiToken": "categorization_api_token",
            f"{base}/RecommendationApiUrl": "recommendation_api_url",
            f"{base}/RecommendationApiToken": "recommendation_api_token",
            f"{base}/CspMessage": "csp_message",
            f"{base}/CspMessageClosed": "csp_message_closed",
            f"{base}/CspMessageSpam": "csp_message_spam",
            f"{base}/SpamCount": "spam_count",
            f"{base}/LogLevel": "log_level",
            f"{base}/LogSqlLevel": "log_sql_level",
            f"{base}/LogSqlEcho": "log_sql_echo",
            f"{base}/ClosedStatuses": "closed_statuses",
            f"{base}/OpenStatuses": "open_statuses",
            f"{base}/PostgresDsn": "postgres_dsn",
            f"{base}/username": "basic_auth_username",
            f"{base}/password": "basic_auth_password",
            f"{base}/DiscordBotUrl": "discord_bot_url",
            f"{base}/DiscordBotApiUsername": "discord_bot_api_username",
            f"{base}/DiscordBotApiPassword": "discord_bot_api_password",
            f"{base}/CollieSensitiveUrl": "collie_sensitive_url",
            f"{base}/ColliePassword": "collie_password",
            f"{base}/CleanJobFrequencyPerDay": "clean_job_frequency_per_day",
            f"{base}/CleanJobHoursSinceLastTimeUpdated": "clean_job_hours_since_last_time_updated",
            f"{base}/CleanupApiBaseUrl": "cleanup_api_base_url",
            f"{base}/CleanupSource": "cleanup_source",
            f"{base}/CleanupStart": "cleanup_start",
            f"{base}/UseFakeExternalsDiscord": "use_fake_externals_discord",
            f"{base}/UseFakeExternalsAi": "use_fake_externals_ai",
            f"{base}/AiCategorizationDebug": "ai_categorization_debug",
            f"{base}/AiRecommendationDebug": "ai_recommendation_debug",
            f"{base}/AiHttpTimeoutSeconds": "ai_http_timeout_seconds",
            f"{base}/AiHttpMaxConnections": "ai_http_max_connections",
            f"{base}/AiHttpMaxKeepaliveConnections": "ai_http_max_keepalive_connections",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        """Build environment variable mappings for ControlUnit."""
        return {
            "categorization_api_url": "CATEGORIZATION_API_URL",
            "categorization_api_token": "CATEGORIZATION_API_TOKEN",
            "recommendation_api_url": "RECOMMENDATION_API_URL",
            "recommendation_api_token": "RECOMMENDATION_API_TOKEN",
            "csp_message": "CSP_MESSAGE",
            "csp_message_closed": "CSP_MESSAGE_CLOSED",
            "csp_message_spam": "CSP_MESSAGE_SPAM",
            "spam_count": "SPAM_COUNT",
            "log_level": "LOG_LEVEL",
            "log_sql_level": "LOG_SQL_LEVEL",
            "log_sql_echo": "LOG_SQL_ECHO",
            "closed_statuses": "CLOSED_STATUSES",
            "open_statuses": "OPEN_STATUSES",
            "postgres_dsn": "POSTGRES_DSN",
            "basic_auth_username": "BASIC_AUTH_USERNAME",
            "basic_auth_password": "BASIC_AUTH_PASSWORD",
            "discord_bot_url": "DISCORD_BOT_URL",
            "discord_bot_api_username": "DISCORD_BOT_API_USERNAME",
            "discord_bot_api_password": "DISCORD_BOT_API_PASSWORD",
            "collie_sensitive_url": "COLLIE_SENSITIVE_URL",
            "collie_password": "COLLIE_PASSWORD",
            "clean_job_frequency_per_day": "CLEAN_JOB_FREQUENCY_PER_DAY",
            "clean_job_hours_since_last_time_updated": "CLEAN_JOB_HOURS_SINCE_LAST_TIME_UPDATED",
            "cleanup_api_base_url": "CLEANUP_API_BASE_URL",
            "cleanup_source": "CLEANUP_SOURCE",
            "cleanup_start": "CLEANUP_START",
            "use_fake_externals_discord": "USE_FAKE_EXTERNALS_DISCORD",
            "use_fake_externals_ai": "USE_FAKE_EXTERNALS_AI",
            "ai_categorization_debug": "AI_CATEGORIZATION_DEBUG",
            "ai_recommendation_debug": "AI_RECOMMENDATION_DEBUG",
            "ai_http_timeout_seconds": "AI_HTTP_TIMEOUT_SECONDS",
            "ai_http_max_connections": "AI_HTTP_MAX_CONNECTIONS",
            "ai_http_max_keepalive_connections": "AI_HTTP_MAX_KEEPALIVE_CONNECTIONS",
        }

    def _coerce_config_value(
        self, internal_name: str, value: builtins.object
    ) -> builtins.object:
        """Apply ControlUnit-specific type coercion."""
        # Apply the same type coercion as in the original implementation
        if internal_name in (
            "log_sql_echo",
            "use_fake_externals_discord",
            "use_fake_externals_ai",
            "cleanup_start",
            "ai_categorization_debug",
            "ai_recommendation_debug",
        ):
            if isinstance(value, str):
                lowered = value.strip().lower()
                value = lowered in ("1", "true", "yes", "y", "on")
            value = bool(value) if value is not None else False
        elif internal_name == "closed_statuses":
            if isinstance(value, str):
                value = tuple(s.strip() for s in value.split(",") if s.strip())
            elif isinstance(value, (list, tuple)):
                value = tuple(value)
            else:
                value = tuple() if value is None else (str(value),)
        elif internal_name in (
            "ai_http_timeout_seconds",
            "ai_http_max_connections",
            "ai_http_max_keepalive_connections",
        ):
            # Convert to int/float with defaults
            if internal_name == "ai_http_timeout_seconds":
                try:
                    value = float(value) if value is not None else 30.0
                except (ValueError, TypeError):
                    value = 30.0
            else:  # connection limits
                try:
                    value = (
                        int(value)
                        if value is not None
                        else (10 if "max_connections" in internal_name else 5)
                    )
                except (ValueError, TypeError):
                    value = 10 if "max_connections" in internal_name else 5

        return value


# Create default ControlUnit client instance
control_unit_client = ControlUnitEtcdClient(
    endpoint=os.getenv("EtcdSettings__HostName"),
    username=os.getenv("EtcdSettings__UserName"),
    password=os.getenv("EtcdSettings__Password"),
    root_key=os.getenv("EtcdSettings__RootKey"),
    use_local_config=str(os.getenv("USE_LOCAL_CONFIG", "false")).lower() == "true",
)

__all__ = ["ControlUnitEtcdClient", "control_unit_client"]
