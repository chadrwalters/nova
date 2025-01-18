"""Bear parser module.

This module provides functionality for parsing Bear.app note exports.
"""

from .parser import BearNote, BearParser, BearParserError
from .processing import BearNoteProcessing

__all__ = ["BearParser", "BearNote", "BearParserError", "BearNoteProcessing"]
