"""Etcd client for configuration management."""

# Re-export for backward compatibility
from .control_unit import ControlUnitEtcdClient as EtcdClient
from .control_unit import control_unit_client as etcd_client

__all__ = ["EtcdClient", "etcd_client"]
