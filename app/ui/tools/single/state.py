"""
State management for the Single Range Ring tool.

Currently, there is no additional session state beyond what Streamlit provides
via widget keys, so this module exposes a small helper to clear any stored
outputs if needed in the future. It is intentionally minimal to match the
existing pattern of one state module per tool.
"""

from app.ui.layout.global_state import clear_tool_outputs


def reset_single_range_ring_state() -> None:
    """Clear persisted outputs for the single range ring tool."""
    clear_tool_outputs("single_range_ring")


__all__ = ["reset_single_range_ring_state"]