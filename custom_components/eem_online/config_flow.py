"""Config flow discovery shim — hassfest requires this module at the integration root."""

from .config_flow_handler import EemOnlineConfigFlowHandler

__all__ = ["EemOnlineConfigFlowHandler"]
