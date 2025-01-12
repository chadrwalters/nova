"""Bear parser module.

This module provides functionality for parsing Bear.app note exports.
"""

from .parser import BearParser, BearNote, BearAttachment, BearParserError

__all__ = ["BearParser", "BearNote", "BearAttachment", "BearParserError"]
