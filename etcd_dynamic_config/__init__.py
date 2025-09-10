"""Etcd Configuration Provider - A Python library for managing etcd-based configurations."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import base classes and implementations
from .core.base import BaseEtcdClient
from .core.client import EtcdClient, etcd_client  # Backward compatibility
from .core.config import EtcdConfig, etcd_config
from .core.control_unit import ControlUnitEtcdClient, control_unit_client

__all__ = [
    "BaseEtcdClient",
    "ControlUnitEtcdClient",
    "control_unit_client",
    "EtcdClient",  # Backward compatibility
    "etcd_client",  # Backward compatibility
    "EtcdConfig",
    "etcd_config",
]
