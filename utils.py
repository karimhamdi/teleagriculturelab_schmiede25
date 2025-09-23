"""
Deprecated API shim.

All API-related functions/constants moved to `api_call.py` to keep
`utils.py` free of network concerns. Import directly from `api_call`.

This module re-exports the public API for backward compatibility.
"""
from __future__ import annotations

import warnings

from api_call import (
    BASE_URL,
    HEADERS,
    get_kit_info,
    get_kit_measurements_df,
    fetch_kit_dataframe,
)

warnings.warn(
    "The API helpers were moved from utils.py to api_call.py. "
    "Please import from 'api_call' going forward.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BASE_URL",
    "HEADERS",
    "get_kit_info",
    "get_kit_measurements_df",
    "fetch_kit_dataframe",
]
