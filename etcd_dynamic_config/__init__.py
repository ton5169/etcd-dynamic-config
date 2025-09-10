"""Etcd Configuration Provider - A Python library for managing etcd-based configurations."""

__version__ = "0.1.1"
__author__ = "Anton Irshenko"
__email__ = "a_irshenko@example.com"

# Import base classes and implementations
from .core.base import BaseEtcdClient
from .core.client import EtcdClient, etcd_client  # Backward compatibility
from .core.config import EtcdConfig, etcd_config
from .core.control_unit import ControlUnitEtcdClient, control_unit_client
from .core.logging import setup_logging

__all__ = [
    "BaseEtcdClient",
    "ControlUnitEtcdClient",
    "control_unit_client",
    "EtcdClient",  # Backward compatibility
    "etcd_client",  # Backward compatibility
    "EtcdConfig",
    "etcd_config",
    "setup_logging",
]
