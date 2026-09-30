"""Governance package for PanganWatch."""

from .data_dictionary import main as data_dictionary_main
from .glossary import main as glossary_main
from .lineage import main as lineage_main
from .policies import main as policies_main
from .raci import main as raci_main

__all__ = [
    "lineage_main",
    "data_dictionary_main",
    "glossary_main",
    "policies_main",
    "raci_main",
]
