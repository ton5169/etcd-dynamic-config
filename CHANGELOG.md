# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added

- Initial release of etcd-config-provider
- Core EtcdClient for etcd operations
- EtcdConfig manager with caching and watching
- Support for TLS and authentication
- Local environment variable fallback
- Real-time configuration watching
- Thread-safe operations
- Comprehensive error handling
- Async/await support
- Structured logging
- Type coercion for configuration values
- Health monitoring for watchers
- Graceful shutdown handling

### Features

- 🚀 High-performance in-memory caching
- 🔄 Real-time configuration updates via etcd watching
- 🛡️ Resilient with graceful fallbacks
- 🔒 Secure TLS and authentication support
- 🧵 Thread-safe concurrent access
- 📊 Structured logging and monitoring
- 🎯 Built-in type validation and coercion

### Dependencies

- `etcd3>=0.12.0` - Core etcd client library

### Python Support

- Python 3.8+
- Tested on CPython implementations
