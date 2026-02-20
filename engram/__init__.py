"""ENGRAM — Episodic-Networked Graph Retrieval & Agent Memory"""
__version__ = "1.0.0"

from .core import Engram
from .types import MemoryUnit, MEMORY_TYPES, EMOTION_DIMS
from .config import EngramConfig

__all__ = ["Engram", "MemoryUnit", "EngramConfig", "MEMORY_TYPES", "EMOTION_DIMS"]
