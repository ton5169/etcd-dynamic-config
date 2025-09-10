# Etcd Dynamic Config

[![PyPI version](https://badge.fury.io/py/etcd-dynamic-config.svg)](https://pypi.org/project/etcd-dynamic-config/)
[![Python versions](https://img.shields.io/pypi/pyversions/etcd-dynamic-config.svg)](https://pypi.org/project/etcd-dynamic-config/)
[![License](https://img.shields.io/pypi/l/etcd-dynamic-config.svg)](https://github.com/ton5169/etcd-dynamic-config/blob/main/LICENSE)

A robust Python library for managing etcd-based configurations with caching, real-time updates, and graceful fallbacks.

## Features

- 🚀 **High Performance**: In-memory caching for fast configuration access
- 🔄 **Real-time Updates**: Automatic watching for configuration changes
- 🛡️ **Resilient**: Graceful fallbacks to local environment variables
- 🔒 **Secure**: Support for TLS and authentication
- 🧵 **Thread-safe**: Safe concurrent access to configuration data
- 📊 **Observable**: Structured logging and monitoring support
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

# Run the example
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

## Advanced Usage

### Custom Configuration Keys

#### Using Built-in ControlUnit Client

```python
from etcd_dynamic_config import EtcdClient

# Use the built-in ControlUnit client (backward compatible)
client = EtcdClient()

# Get specific configuration values
key_map = client.get_control_unit_key_map()
print("Available config keys:", list(key_map.values()))

# Direct key access
values = client.get_values_by_keys(["/APPS/ControlUnit/LogLevel"])
print("Log level:", values.get("/APPS/ControlUnit/LogLevel"))
```

#### Creating Custom Clients

```python
from etcd_dynamic_config import BaseEtcdClient

class MyAppEtcdClient(BaseEtcdClient):
    def get_config_prefix(self) -> str:
        return "/apps/myapp/prod"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            f"{base}/DatabaseUrl": "database_url",
            f"{base}/RedisUrl": "redis_url",
            f"{base}/ApiKey": "api_key",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            "database_url": "MYAPP_DATABASE_URL",
            "redis_url": "MYAPP_REDIS_URL",
            "api_key": "MYAPP_API_KEY",
        }

# Use custom client
client = MyAppEtcdClient(use_local_config=True)
config = client.get_config()
print("Database URL:", config.get("database_url"))
```

### Async Configuration Manager

```python
import asyncio
from etcd_dynamic_config import EtcdConfig

async def config_worker():
    config_manager = EtcdConfig()

    # Start with watching
    await config_manager.start()

    try:
        while True:
            configs = await config_manager.get_all_configs()

            # Your application logic here
            api_token = configs.get('categorization_api_token')
            if api_token:
                print(f"Using API token: {api_token[:10]}...")

            await asyncio.sleep(60)  # Check every minute

    finally:
        await config_manager.stop()

asyncio.run(config_worker())
```

### Error Handling

```python
import asyncio
from etcd_dynamic_config import etcd_config

async def robust_config_access():
    try:
        await etcd_config.start()

        configs = await etcd_config.get_all_configs()

        # Safe access with defaults
        timeout = configs.get('ai_http_timeout_seconds', 30.0)
        max_conn = configs.get('ai_http_max_connections', 10)

        print(f"Timeout: {timeout}s, Max connections: {max_conn}")

    except Exception as e:
        print(f"Configuration error: {e}")
        # Fallback to hardcoded defaults
        timeout = 30.0
        max_conn = 10

    finally:
        await etcd_config.stop()
```

## Configuration Schema

The library doesn't impose any specific configuration schema - **you define your own keys!**

### Defining Your Configuration Schema

```python
from etcd_dynamic_config import BaseEtcdClient

class MyAppClient(BaseEtcdClient):
    def get_config_prefix(self) -> str:
        return "/myapp/production"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            # Your custom etcd keys -> internal names
            f"{base}/Database/Host": "db_host",
            f"{base}/Database/Port": "db_port",
            f"{base}/Database/Name": "db_name",
            f"{base}/Cache/RedisUrl": "redis_url",
            f"{base}/API/SecretKey": "api_secret",
            f"{base}/Features/EnableCache": "enable_cache",
            f"{base}/Monitoring/LogLevel": "log_level",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            # Internal names -> environment variables
            "db_host": "MYAPP_DB_HOST",
            "db_port": "MYAPP_DB_PORT",
            "db_name": "MYAPP_DB_NAME",
            "redis_url": "MYAPP_REDIS_URL",
            "api_secret": "MYAPP_API_SECRET",
            "enable_cache": "MYAPP_ENABLE_CACHE",
            "log_level": "MYAPP_LOG_LEVEL",
        }
```

### Custom Type Coercion

```python
def _coerce_config_value(self, internal_name: str, value):
    """Define your own type coercion rules."""
    if internal_name == "db_port":
        return int(value) if value else 5432
    elif internal_name == "enable_cache":
        return str(value).lower() in ("1", "true", "yes", "on")
    elif internal_name == "api_secret":
        # Don't log secrets in plain text
        return str(value) if value else ""

    # Use default coercion for other values
    return super()._coerce_config_value(internal_name, value)
```

### Your Configuration Documentation

Create documentation for **your** configuration keys:

| Your Etcd Key                            | Environment Variable | Type | Default   | Description           |
| ---------------------------------------- | -------------------- | ---- | --------- | --------------------- |
| `/myapp/production/Database/Host`        | `MYAPP_DB_HOST`      | str  | localhost | Database host         |
| `/myapp/production/Database/Port`        | `MYAPP_DB_PORT`      | int  | 5432      | Database port         |
| `/myapp/production/Cache/RedisUrl`       | `MYAPP_REDIS_URL`    | str  | -         | Redis connection URL  |
| `/myapp/production/Features/EnableCache` | `MYAPP_ENABLE_CACHE` | bool | false     | Enable caching        |
| `/myapp/production/Monitoring/LogLevel`  | `MYAPP_LOG_LEVEL`    | str  | INFO      | Application log level |

See [examples/schema_documentation_example.py](examples/schema_documentation_example.py) for a complete example of documenting and implementing a custom configuration schema.

### Built-in ControlUnit Client

For backward compatibility, the library includes a pre-configured client for ControlUnit applications:

```python
from etcd_dynamic_config import EtcdClient, etcd_client

# Uses the ControlUnit schema automatically
client = EtcdClient()
config = client.get_config()

# Access ControlUnit-specific keys
api_url = config.get("categorization_api_url")
db_dsn = config.get("postgres_dsn")
```

The ControlUnit client handles these keys automatically (see [ControlUnitEtcdClient](https://github.com/ton5169/etcd-dynamic-config/blob/main/etcd_dynamic_config/core/control_unit.py) for details).

## Architecture

### Components

1. **EtcdClient**: Low-level etcd operations

   - Connection management
   - Authentication and TLS
   - Key-value operations
   - Watching capabilities

2. **EtcdConfig**: High-level configuration management
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

- Automatic reconnection on auth failures
- Watcher restart on inactivity
- Fallback to local environment variables
- Graceful degradation on etcd unavailability

## Development

### Setup

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

# Run with coverage
pytest --cov=etcd_dynamic_config --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Run integration tests
pytest -m integration
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e .[docs]

# Build docs
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

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Extensibility & Customization

### Creating Custom Clients

The library provides `BaseEtcdClient` for creating custom implementations:

```python
from etcd_dynamic_config import BaseEtcdClient

class MyServiceClient(BaseEtcdClient):
    def get_config_prefix(self) -> str:
        return "/services/my-service"

    def _build_etcd_key_map(self) -> Dict[str, str]:
        base = self.get_config_prefix()
        return {
            f"{base}/DatabaseUrl": "database_url",
            f"{base}/RedisUrl": "redis_url",
            f"{base}/ApiKey": "api_key",
            f"{base}/MaxWorkers": "max_workers",
        }

    def _build_env_var_map(self) -> Dict[str, str]:
        return {
            "database_url": "MYAPP_DATABASE_URL",
            "redis_url": "MYAPP_REDIS_URL",
            "api_key": "MYAPP_API_KEY",
            "max_workers": "MYAPP_MAX_WORKERS",
        }

    def _coerce_config_value(self, name: str, value):
        if name == "max_workers":
            return int(value) if value else 4
        return super()._coerce_config_value(name, value)

# Use your custom client
client = MyServiceClient(use_local_config=True)
config = client.get_config()
```

### Available Classes

- **BaseEtcdClient**: Abstract base for custom implementations
- **ControlUnitEtcdClient**: Pre-configured for ControlUnit (default)
- **EtcdClient**: Alias for ControlUnitEtcdClient (backward compatibility)
- **EtcdConfig**: High-level configuration manager

### Key Benefits

- **🎯 Universal**: Works with any etcd key structure
- **🔧 Customizable**: Easy to adapt for different applications
- **🔄 Backward Compatible**: Existing code continues to work
- **🏗️ Extensible**: Clean architecture for future enhancements

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
