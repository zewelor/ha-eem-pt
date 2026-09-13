"""
Entity package for eem_online.

Architecture:
    All platform entities inherit from (PlatformEntity, EemOnlineEntity).
    MRO order matters — platform-specific class first, then the integration base.
    Entities read data from coordinator.data and NEVER call the API client directly.
    Unique IDs follow the pattern: {entry_id}_{description.key}

See entity/base.py for the EemOnlineEntity base class.
"""

from .base import EemOnlineEntity

__all__ = ["EemOnlineEntity"]
