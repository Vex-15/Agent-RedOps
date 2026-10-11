"""
Serialization helpers shared by the API layer and the live event stream.

`PipelineResult` and its nested types are dataclasses whose fields include
Enums and nested dataclasses.  The HTTP API and the NDJSON stream both need
the same plain-dict shape, so the conversion lives here rather than in
`main.py` (which imports the runner, and must not be imported back).
"""

from __future__ import annotations
import dataclasses
from enum import Enum
from typing import Any

# Only `AttackPath` exposes a meaningful computed property.
_COMPUTED_PROPERTIES = ("length",)


def to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses/enums to JSON-friendly structures."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        out = {}
        for f in dataclasses.fields(obj):
            out[f.name] = to_dict(getattr(obj, f.name))
        for name in _COMPUTED_PROPERTIES:
            prop = getattr(type(obj), name, None)
            if isinstance(prop, property):
                try:
                    out[name] = getattr(obj, name)
                except Exception:
                    pass
        return out
    if isinstance(obj, (list, tuple)):
        return [to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, Enum):
        return obj.value
    return obj
