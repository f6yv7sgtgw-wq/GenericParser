"""Projektadapter für den versionierten GenericParser-Modulvertrag."""

from .evercade import evercade_profile
from .snes import snes_pal_profile

__all__ = ["evercade_profile", "snes_pal_profile"]
