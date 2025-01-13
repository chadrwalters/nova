"""Bear parser module.

This module provides functionality for parsing Bear.app note exports.
"""

from .parser import BearNote, BearParser, BearParserError

__all__ = ["BearParser", "BearNote", "BearParserError"]
