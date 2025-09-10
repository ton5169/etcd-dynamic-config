# Etcd Dynamic Config

[![PyPI version](https://badge.fury.io/py/etcd-dynamic-config.svg)](https://pypi.org/project/etcd-dynamic-config/)
[![Python versions](https://img.shields.io/pypi/pyversions/etcd-dynamic-config.svg)](https://pypi.org/project/etcd-dynamic-config/)
[![License](https://img.shields.io/pypi/l/etcd-dynamic-config.svg)](https://github.com/ton5169/etcd-dynamic-config/blob/main/LICENSE)

A robust Python library for managing etcd-based configurations with caching, real-time updates, and graceful fallbacks.

## Key Features

- 🚀 **High Performance**: In-memory caching for fast configuration access
- 🔄 **Real-time Updates**: Automatic watching for configuration changes
- 🛡️ **Reliability**: Graceful fallbacks to local environment variables
- 🔒 **Security**: Support for TLS and authentication
- 🧵 **Thread-safe**: Safe concurrent access to configuration data
- 📊 **Observability**: Structured logging and monitoring support
- 🎯 **Type-safe**: Built-in type coercion and validation

## Installation

```bash
pip install etcd-dynamic-config
```

For development with extra tools:

```bash
pip install etcd-dynamic-config[dev]
```

## Quick Start

### Basic Usage

```python
import asyncio
from etcd_dynamic_config import etcd_config

async def main():
    # Start the configuration manager
    success = await etcd_config.start()
    if success:
        # Get all configurations
        configs = await etcd_config.get_all_configs()
        print(f"Database URL: {configs.get('postgres_dsn')}")

        # Access specific config values
        api_url = configs.get('categorization_api_url')
        print(f"API URL: {api_url}")

    # Clean shutdown
    await etcd_config.stop()

asyncio.run(main())
```

### Environment Variables

Set these environment variables to configure etcd connection:

```bash
# Etcd connection settings
export EtcdSettings__HostName="http://localhost:2379"
export EtcdSettings__UserName="your-username"
export EtcdSettings__Password="your-password"
export EtcdSettings__RootKey="/APPS/ControlUnit"

# Optional: Use local environment variables instead of etcd
export USE_LOCAL_CONFIG="false"

# Optional: TLS settings
export EtcdSettings__CaCertPath="/path/to/ca-cert.pem"
```

### Local Development

For local development, set `USE_LOCAL_CONFIG=true` and define configurations as environment variables:

```bash
export USE_LOCAL_CONFIG="true"
export CATEGORIZATION_API_URL="http://localhost:8000"
export POSTGRES_DSN="postgresql://user:pass@localhost:5432/db"
export LOG_LEVEL="DEBUG"
```

## Detailed Usage Examples

### BaseEtcdClient - Creating Custom Clients

`BaseEtcdClient` is an abstract base class for creating custom etcd clients. It provides all necessary methods for working with etcd, but requires implementation of three abstract methods.

#### Complete BaseEtcdClient Example

```python
from typing import Dict
from etcd_dynamic_config import BaseEtcdClient

class MyApplicationClient(BaseEtcdClient):
    """Custom client for MyApplication."""

    def __init__(
        self,
        endpoint: str = None,
        username: str = None,
        password: str = None,
        root_key: str = None,
        ca_cert_path: str = None,
        use_local_config: bool = None,
        app_environment: str = "production"
    ):
        """Initialize MyApplication client.

        Args:
            endpoint: etcd server address (http://localhost:2379)
            username: Username for authentication
            password: Password for authentication
            root_key: Root key prefix (/APPS/MyApp)
            ca_cert_path: Path to CA certificate for TLS
            use_local_config: Whether to use local variables instead of etcd
            app_environment: Application environment (production/staging/dev)
        """
        # Pass all parameters to base class
        super().__init__(
            endpoint=endpoint,
            username=username,
            password=password,
            root_key=root_key,
            ca_cert_path=ca_cert_path,
            use_local_config=use_local_config
        )

        self.app_environment = app_environment

    def get_config_prefix(self) -> str:
        """Get the configuration keys prefix."""
        # Add environment to path
        dev_prefix = "/dev" if self.app_environment == "dev" else ""
        root = self._root_key or f"/APPS/MyApplication/{self.app_environment}"
        return f"{dev_prefix}{root}"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        """Build etcd keys to internal names mapping."""
        base = self.get_config_prefix()
        return {
            f"{base}/Database/Host": "database_host",
            f"{base}/Database/Port": "database_port",
            f"{base}/Database/Name": "database_name",
            f"{base}/Database/User": "database_user",
            f"{base}/Database/Password": "database_password",
            f"{base}/Redis/Url": "redis_url",
            f"{base}/API/BaseUrl": "api_base_url",
            f"{base}/API/SecretKey": "api_secret_key",
            f"{base}/Cache/Enabled": "cache_enabled",
            f"{base}/Cache/TTL": "cache_ttl_seconds",
            f"{base}/Logging/Level": "log_level",
            f"{base}/Monitoring/Enabled": "monitoring_enabled",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        """Build internal names to environment variables mapping."""
        return {
            "database_host": "MYAPP_DB_HOST",
            "database_port": "MYAPP_DB_PORT",
            "database_name": "MYAPP_DB_NAME",
            "database_user": "MYAPP_DB_USER",
            "database_password": "MYAPP_DB_PASSWORD",
            "redis_url": "MYAPP_REDIS_URL",
            "api_base_url": "MYAPP_API_BASE_URL",
            "api_secret_key": "MYAPP_API_SECRET_KEY",
            "cache_enabled": "MYAPP_CACHE_ENABLED",
            "cache_ttl_seconds": "MYAPP_CACHE_TTL_SECONDS",
            "log_level": "MYAPP_LOG_LEVEL",
            "monitoring_enabled": "MYAPP_MONITORING_ENABLED",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Apply custom type coercion."""
        # Application-specific type coercion
        if internal_name == "database_port":
            try:
                return int(value) if value else 5432
            except (ValueError, TypeError):
                return 5432
        elif internal_name in ("cache_enabled", "monitoring_enabled"):
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on", "enabled")
            return bool(value)
        elif internal_name == "cache_ttl_seconds":
            try:
                return int(value) if value else 3600
            except (ValueError, TypeError):
                return 3600
        elif internal_name == "api_secret_key":
            # Don't log secret keys
            return str(value) if value else ""

        # Use default coercion for other values
        return super()._coerce_config_value(internal_name, value)

# Client usage
def main():
    # Example 1: Using with etcd
    print("=== Using with etcd ===")
    client_etcd = MyApplicationClient(
        endpoint="https://etcd-cluster.example.com:2379",
        username="myapp-user",
        password="secure-password",
        root_key="/APPS/MyApplication/production",
        ca_cert_path="/etc/ssl/certs/ca-bundle.pem",
        use_local_config=False,
        app_environment="production"
    )

    # Get configuration
    config = client_etcd.get_config()
    print(f"Database Host: {config.get('database_host')}")
    print(f"Cache Enabled: {config.get('cache_enabled')} (type: {type(config.get('cache_enabled'))})")

    # Example 2: Local development
    print("\n=== Local development example ===")
    client_local = MyApplicationClient(
        use_local_config=True,
        app_environment="dev"
    )

    config_local = client_local.get_config()
    print(f"Local Database Host: {config_local.get('database_host')}")
    print(f"Local Log Level: {config_local.get('log_level')}")

    # Example 3: Minimal configuration
    print("\n=== Minimal configuration example ===")
    client_minimal = MyApplicationClient()  # All parameters default from env
    config_minimal = client_minimal.get_config()
    print(f"Minimal config keys: {list(config_minimal.keys())}")

if __name__ == "__main__":
    main()
```

### ControlUnitEtcdClient - Ready-to-Use Client for ControlUnit

`ControlUnitEtcdClient` is a ready-to-use client implementation for ControlUnit applications with predefined key mappings.

#### Basic ControlUnitEtcdClient Usage

```python
from etcd_dynamic_config import ControlUnitEtcdClient

def main():
    # Example 1: Basic usage (all parameters default)
    print("=== Basic ControlUnitEtcdClient usage ===")
    client = ControlUnitEtcdClient()

    # Get configuration
    config = client.get_config()

    print(f"API URL: {config.get('categorization_api_url')}")
    print(f"Database DSN: {config.get('postgres_dsn')}")
    print(f"Log Level: {config.get('log_level')}")
    print(f"Spam Count: {config.get('spam_count')} (type: {type(config.get('spam_count'))})")

    # Access mappings
    etcd_keys = client.get_etcd_key_map()
    env_vars = client.get_env_var_map()

    print(f"\nAvailable etcd keys: {len(etcd_keys)}")
    print(f"Available environment variables: {len(env_vars)}")
    print(f"Configuration prefix: {client.get_config_prefix()}")

if __name__ == "__main__":
    main()
```

#### ControlUnitEtcdClient with Explicit Parameters

```python
from etcd_dynamic_config import ControlUnitEtcdClient

def main():
    # Example 2: Full configuration with parameters
    print("=== ControlUnitEtcdClient with explicit parameters ===")

    client = ControlUnitEtcdClient(
        # Etcd connection
        endpoint="https://etcd-prod.company.com:2379",
        username="controlunit-user",
        password="secure-password-123",

        # Root configuration key
        root_key="/PROD/APPS/ControlUnit",

        # TLS settings
        ca_cert_path="/etc/ssl/certs/company-ca.pem",

        # Use etcd (not local variables)
        use_local_config=False
    )

    # Get configuration
    config = client.get_config()

    # Access ControlUnit-specific settings
    print("=== ControlUnit Configuration ===")
    print(f"Categorization API URL: {config.get('categorization_api_url')}")
    print(f"Categorization API Token: {'*' * 20}")  # Don't show tokens
    print(f"Postgres DSN: {config.get('postgres_dsn')}")
    print(f"Log Level: {config.get('log_level')}")
    print(f"Log SQL Level: {config.get('log_sql_level')}")
    print(f"Log SQL Echo: {config.get('log_sql_echo')} (type: {type(config.get('log_sql_echo'))})")

    # Discord settings
    print(f"\nDiscord Bot URL: {config.get('discord_bot_url')}")
    print(f"Discord Bot Username: {config.get('discord_bot_api_username')}")

    # Cache and cleanup settings
    print(f"\nClean Job Frequency: {config.get('clean_job_frequency_per_day')}")
    print(f"Clean Job Hours: {config.get('clean_job_hours_since_last_time_updated')}")

    # AI settings
    print(f"\nAI HTTP Timeout: {config.get('ai_http_timeout_seconds')}s")
    print(f"AI Max Connections: {config.get('ai_http_max_connections')}")
    print(f"AI Max Keepalive: {config.get('ai_http_max_keepalive_connections')}")

    # Boolean settings
    print(f"\nUse Fake Externals Discord: {config.get('use_fake_externals_discord')}")
    print(f"Use Fake Externals AI: {config.get('use_fake_externals_ai')}")
    print(f"AI Categorization Debug: {config.get('ai_categorization_debug')}")
    print(f"AI Recommendation Debug: {config.get('ai_recommendation_debug')}")

if __name__ == "__main__":
    main()
```

#### Local Development with ControlUnitEtcdClient

```python
import os
from etcd_dynamic_config import ControlUnitEtcdClient

def main():
    # Example 3: Local development
    print("=== Local development with ControlUnitEtcdClient ===")

    # Set environment variables for local development
    os.environ.update({
        # API settings
        "CATEGORIZATION_API_URL": "http://localhost:8001/api/v1",
        "CATEGORIZATION_API_TOKEN": "dev-token-12345",
        "RECOMMENDATION_API_URL": "http://localhost:8002/api/v1",
        "RECOMMENDATION_API_TOKEN": "dev-rec-token-67890",

        # Database
        "POSTGRES_DSN": "postgresql://controlunit:password@localhost:5432/controlunit_dev",

        # Logging
        "LOG_LEVEL": "DEBUG",
        "LOG_SQL_LEVEL": "INFO",
        "LOG_SQL_ECHO": "true",

        # Discord (fake for development)
        "DISCORD_BOT_URL": "http://localhost:8080/webhook",
        "DISCORD_BOT_API_USERNAME": "dev-bot",
        "DISCORD_BOT_API_PASSWORD": "dev-password",

        # Cleanup settings
        "CLEAN_JOB_FREQUENCY_PER_DAY": "24",
        "CLEAN_JOB_HOURS_SINCE_LAST_TIME_UPDATED": "168",

        # AI settings
        "AI_HTTP_TIMEOUT_SECONDS": "10.0",
        "AI_HTTP_MAX_CONNECTIONS": "20",
        "AI_HTTP_MAX_KEEPALIVE_CONNECTIONS": "10",

        # Fake external services for development
        "USE_FAKE_EXTERNALS_DISCORD": "true",
        "USE_FAKE_EXTERNALS_AI": "true",

        # AI debugging
        "AI_CATEGORIZATION_DEBUG": "true",
        "AI_RECOMMENDATION_DEBUG": "true",

        # CSP messages
        "CSP_MESSAGE": "Content Security Policy violation detected",
        "CSP_MESSAGE_CLOSED": "Ticket closed due to CSP violation",
        "CSP_MESSAGE_SPAM": "Message marked as spam",

        # Statuses
        "CLOSED_STATUSES": "closed,done,resolved",
        "OPEN_STATUSES": "open,new,in_progress",
    })

    # Create client for local development
    client = ControlUnitEtcdClient(
        use_local_config=True,  # Use local variables
        root_key="/DEV/APPS/ControlUnit"  # Development prefix
    )

    # Get configuration
    config = client.get_config()

    print("=== Development Configuration ===")
    print(f"Environment: Development")
    print(f"Config Prefix: {client.get_config_prefix()}")
    print(f"Use Local Config: {client._use_local_config}")

    print(f"\n=== API Settings ===")
    print(f"Categorization API: {config.get('categorization_api_url')}")
    print(f"Recommendation API: {config.get('recommendation_api_url')}")

    print(f"\n=== Database ===")
    print(f"Postgres DSN: {config.get('postgres_dsn')}")

    print(f"\n=== Logging ===")
    print(f"Log Level: {config.get('log_level')}")
    print(f"SQL Log Level: {config.get('log_sql_level')}")
    print(f"SQL Echo: {config.get('log_sql_echo')}")

    print(f"\n=== External Services ===")
    print(f"Discord Bot URL: {config.get('discord_bot_url')}")
    print(f"Use Fake Discord: {config.get('use_fake_externals_discord')}")
    print(f"Use Fake AI: {config.get('use_fake_externals_ai')}")

    print(f"\n=== AI Configuration ===")
    print(f"AI Timeout: {config.get('ai_http_timeout_seconds')}s")
    print(f"AI Max Connections: {config.get('ai_http_max_connections')}")
    print(f"AI Debug Categorization: {config.get('ai_categorization_debug')}")
    print(f"AI Debug Recommendation: {config.get('ai_recommendation_debug')}")

    print(f"\n=== Status Configuration ===")
    print(f"Closed Statuses: {config.get('closed_statuses')}")
    print(f"Open Statuses: {config.get('open_statuses')}")

if __name__ == "__main__":
    main()
```

## Client Initialization Parameters

### Common Parameters for BaseEtcdClient and ControlUnitEtcdClient

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `endpoint` | `str` | `EtcdSettings__HostName` env | etcd server address (http://localhost:2379) |
| `username` | `str` | `EtcdSettings__UserName` env | Username for authentication |
| `password` | `str` | `EtcdSettings__Password` env | Password for authentication |
| `root_key` | `str` | `EtcdSettings__RootKey` env | Root key prefix (/APPS/MyApp) |
| `ca_cert_path` | `str` | Auto-detection | Path to CA certificate for TLS |
| `use_local_config` | `bool` | `USE_LOCAL_CONFIG` env | Whether to use local variables instead of etcd |

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `EtcdSettings__HostName` | etcd server address | `http://etcd-cluster:2379` |
| `EtcdSettings__UserName` | Username | `myapp-user` |
| `EtcdSettings__Password` | Password | `secure-password` |
| `EtcdSettings__RootKey` | Root prefix | `/PROD/APPS/MyApp` |
| `EtcdSettings__CaCertPath` | Path to CA certificate | `/etc/ssl/certs/ca.pem` |
| `USE_LOCAL_CONFIG` | Use local variables | `false` |

## Working with Configurations

### Synchronous Configuration Retrieval

```python
from etcd_dynamic_config import ControlUnitEtcdClient

# Create client
client = ControlUnitEtcdClient(use_local_config=True)

# Get all configurations
config = client.get_config()

# Access specific values
api_url = config.get('categorization_api_url')
database_dsn = config.get('postgres_dsn')

print(f"API URL: {api_url}")
print(f"Database: {database_dsn}")
```

### Asynchronous Configuration Management

```python
import asyncio
from etcd_dynamic_config import EtcdConfig, ControlUnitEtcdClient

async def async_config_example():
    # Create custom client
    client = ControlUnitEtcdClient(
        endpoint="https://etcd.example.com:2379",
        username="my-user",
        password="my-password"
    )

    # Create configuration manager
    config_manager = EtcdConfig(client=client)

    try:
        # Start manager
        success = await config_manager.start()
        if success:
            print("✅ Configuration manager started")

            # Get configurations
            configs = await config_manager.get_all_configs()

            # Work with configurations
            api_token = configs.get('categorization_api_token')
            if api_token:
                print(f"API Token received: {len(api_token)} characters")

            # Work loop
            for i in range(5):
                await asyncio.sleep(2)
                current_configs = await config_manager.get_all_configs()
                log_level = current_configs.get('log_level', 'INFO')
                print(f"[{i+1}/5] Current log level: {log_level}")

    except Exception as e:
        print(f"❌ Configuration error: {e}")

    finally:
        # Clean shutdown
        await config_manager.stop()
        print("👋 Configuration manager stopped")

asyncio.run(async_config_example())
```

### Error Handling

```python
from etcd_dynamic_config import ControlUnitEtcdClient

def safe_config_access():
    try:
        client = ControlUnitEtcdClient(
            endpoint="https://etcd.example.com:2379",
            username="wrong-user",
            password="wrong-password"
        )

        config = client.get_config()

        # Safe access with default values
        timeout = config.get('ai_http_timeout_seconds') or 30.0
        max_conn = config.get('ai_http_max_connections') or 10
        log_level = config.get('log_level') or 'INFO'

        print(f"✅ Configuration loaded successfully")
        print(f"Timeout: {timeout}s, Max connections: {max_conn}")
        print(f"Log level: {log_level}")

    except Exception as e:
        print(f"❌ Configuration access error: {e}")
        print("🔄 Using fallback values...")

        # Fallback values
        timeout = 30.0
        max_conn = 10
        log_level = 'INFO'

    return {
        'timeout': timeout,
        'max_connections': max_conn,
        'log_level': log_level
    }

# Usage
config = safe_config_access()
print(f"Final configuration: {config}")
```

## Configuration Schema

The library doesn't impose any specific configuration schema - **you define your own keys!**

### Creating Your Own Configuration Schema

```python
from typing import Dict
from etcd_dynamic_config import BaseEtcdClient

class MyServiceClient(BaseEtcdClient):
    """Client for your service with custom configuration schema."""

    def get_config_prefix(self) -> str:
        """Returns the configuration keys prefix."""
        return "/services/my-service/prod"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        """Builds etcd keys to internal names mapping."""
        base = self.get_config_prefix()
        return {
            # Your custom etcd keys -> internal names
            f"{base}/Database/Host": "db_host",
            f"{base}/Database/Port": "db_port",
            f"{base}/Database/Name": "db_name",
            f"{base}/Database/Credentials/User": "db_user",
            f"{base}/Database/Credentials/Password": "db_password",
            f"{base}/Redis/Url": "redis_url",
            f"{base}/Redis/Password": "redis_password",
            f"{base}/API/BaseUrl": "api_base_url",
            f"{base}/API/SecretKey": "api_secret_key",
            f"{base}/Features/Cache/Enabled": "cache_enabled",
            f"{base}/Features/Cache/TTL": "cache_ttl_seconds",
            f"{base}/Monitoring/LogLevel": "log_level",
            f"{base}/Monitoring/Metrics/Enabled": "metrics_enabled",
            f"{base}/Limits/MaxConnections": "max_connections",
            f"{base}/Limits/Timeout": "request_timeout",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        """Builds internal names to environment variables mapping."""
        return {
            # Internal names -> environment variables
            "db_host": "MYSERVICE_DB_HOST",
            "db_port": "MYSERVICE_DB_PORT",
            "db_name": "MYSERVICE_DB_NAME",
            "db_user": "MYSERVICE_DB_USER",
            "db_password": "MYSERVICE_DB_PASSWORD",
            "redis_url": "MYSERVICE_REDIS_URL",
            "redis_password": "MYSERVICE_REDIS_PASSWORD",
            "api_base_url": "MYSERVICE_API_BASE_URL",
            "api_secret_key": "MYSERVICE_API_SECRET_KEY",
            "cache_enabled": "MYSERVICE_CACHE_ENABLED",
            "cache_ttl_seconds": "MYSERVICE_CACHE_TTL",
            "log_level": "MYSERVICE_LOG_LEVEL",
            "metrics_enabled": "MYSERVICE_METRICS_ENABLED",
            "max_connections": "MYSERVICE_MAX_CONNECTIONS",
            "request_timeout": "MYSERVICE_REQUEST_TIMEOUT",
        }

    def _coerce_config_value(self, internal_name: str, value):
        """Applies custom type coercion."""
        # Type coercion for numeric values
        if internal_name in ("db_port", "max_connections", "cache_ttl_seconds"):
            try:
                return int(value) if value else self._get_default_value(internal_name)
            except (ValueError, TypeError):
                return self._get_default_value(internal_name)

        # Type coercion for timeouts
        elif internal_name == "request_timeout":
            try:
                return float(value) if value else 30.0
            except (ValueError, TypeError):
                return 30.0

        # Type coercion for boolean values
        elif internal_name in ("cache_enabled", "metrics_enabled"):
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "on", "enabled")
            return bool(value)

        # Don't log secret values
        elif internal_name in ("db_password", "redis_password", "api_secret_key"):
            return str(value) if value else ""

        # Use default coercion for other values
        return super()._coerce_config_value(internal_name, value)

    def _get_default_value(self, internal_name: str):
        """Returns default values."""
        defaults = {
            "db_port": 5432,
            "max_connections": 10,
            "cache_ttl_seconds": 3600,
        }
        return defaults.get(internal_name, 0)
```

### Documenting Your Configuration Schema

Create documentation for your configuration keys:

| Etcd Key | Environment Variable | Type | Default | Description |
|----------|---------------------|------|---------|-------------|
| `/services/my-service/prod/Database/Host` | `MYSERVICE_DB_HOST` | str | - | Database host |
| `/services/my-service/prod/Database/Port` | `MYSERVICE_DB_PORT` | int | 5432 | Database port |
| `/services/my-service/prod/Database/Name` | `MYSERVICE_DB_NAME` | str | - | Database name |
| `/services/my-service/prod/Redis/Url` | `MYSERVICE_REDIS_URL` | str | - | Redis server URL |
| `/services/my-service/prod/Features/Cache/Enabled` | `MYSERVICE_CACHE_ENABLED` | bool | false | Enable caching |
| `/services/my-service/prod/Limits/MaxConnections` | `MYSERVICE_MAX_CONNECTIONS` | int | 10 | Maximum connections |
| `/services/my-service/prod/Monitoring/LogLevel` | `MYSERVICE_LOG_LEVEL` | str | INFO | Log level |

## Architecture

### Components

1. **BaseEtcdClient**: Base client for etcd operations
   - Connection management
   - Authentication and TLS
   - Key-value operations
   - Change watching capabilities

2. **ControlUnitEtcdClient**: Specialized client for ControlUnit
   - Predefined key mappings
   - Specific type coercion
   - Ready to use

3. **EtcdConfig**: High-level configuration manager
   - Caching layer
   - Type coercion
   - Real-time updates
   - Health monitoring

### Thread Safety

All operations are thread-safe:

- Configuration cache uses `threading.RLock()`
- Async operations properly handle concurrency
- Watcher callbacks are serialized

### Error Recovery

The library implements several recovery mechanisms:

- Automatic reconnection on authentication failures
- Watcher restart on inactivity
- Fallback to local environment variables
- Graceful degradation when etcd is unavailable

## Available Classes

| Class | Purpose | Usage |
|-------|---------|-------|
| `BaseEtcdClient` | Abstract base class | For creating custom clients |
| `ControlUnitEtcdClient` | Ready-to-use client for ControlUnit | For ControlUnit applications |
| `EtcdConfig` | Configuration manager | For async configuration management |

## Development

### Development Setup

```bash
# Clone the repository
git clone https://github.com/ton5169/etcd-dynamic-config.git
cd etcd-dynamic-config

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Format code
black etcd_dynamic_config/
isort etcd_dynamic_config/

# Type checking
mypy etcd_dynamic_config/
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=etcd_dynamic_config --cov-report=html

# Specific test file
pytest tests/test_client.py

# Integration tests
pytest -m integration
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e .[docs]

# Build documentation
cd docs
make html
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Usage Examples

Check out complete examples in the [examples/](examples/) directory:

- [basic_usage.py](examples/basic_usage.py) - basic usage
- [advanced_usage.py](examples/advanced_usage.py) - advanced features
- [custom_client_example.py](examples/custom_client_example.py) - custom client
- [schema_documentation_example.py](examples/schema_documentation_example.py) - schema documentation

## License

MIT License - see [LICENSE](LICENSE) file.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
