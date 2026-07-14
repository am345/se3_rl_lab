"""Robot asset configurations with lazy Isaac runtime imports."""

from typing import Any

__all__ = ["SERIALLEG_CLOSED_CHAIN_CFG"]


def __getattr__(name: str) -> Any:
    if name == "SERIALLEG_CLOSED_CHAIN_CFG":
        from .serialleg import SERIALLEG_CLOSED_CHAIN_CFG

        return SERIALLEG_CLOSED_CHAIN_CFG
    raise AttributeError(name)
