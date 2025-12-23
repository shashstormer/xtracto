"""
Token Definitions for pypx
Defines token types and the Token data structure used throughout the parsing pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class TokenType(Enum):
    """Token types for the pypx language."""
    INDENT = auto()
    NEWLINE = auto()
    DEDENT = auto()
    EOF = auto()
    IDENTIFIER = auto()
    TEXT = auto()
    COMMENT_START = auto()
    COMMENT_END = auto()
    COMMENT = auto()
    ATTR_START = auto()
    ATTR_END = auto()
    ATTR_CONTENT = auto()
    VAR_START = auto()
    VAR_END = auto()
    VAR_CONTENT = auto()
    IMPORT_START = auto()
    IMPORT_END = auto()
    IMPORT_PARAMS = auto()
    IMPORT_CONTENT = auto()
    JINJA_BLOCK_START = auto()
    JINJA_BLOCK_END = auto()
    JINJA_BLOCK = auto()
    JINJA_COMMENT_START = auto()
    JINJA_COMMENT_END = auto()
    JINJA_COMMENT = auto()
    EQUALS = auto()
    WHITESPACE = auto()
    LINE_CONTINUATION = auto()

    def __repr__(self) -> str:
        return self.name


@dataclass
class Token:
    """
    Represents a single token from the pypx source.
    Attributes:
        type: The type of token
        value: The string content of the token
        line: 1-indexed line number in source
        column: 1-indexed column number in source
        source_file: Optional filename for error reporting
    """
    type: TokenType
    value: str
    line: int
    column: int
    source_file: Optional[str] = None

    def __repr__(self) -> str:
        value_repr = self.value
        if len(value_repr) > 20:
            value_repr = value_repr[:17] + "..."
        value_repr = value_repr.replace("\n", "\\n").replace("\t", "\\t")
        return f"Token({self.type.name}, {value_repr!r}, L{self.line}:C{self.column})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Token):
            return (
                    self.type == other.type
                    and self.value == other.value
                    and self.line == other.line
                    and self.column == other.column
            )
        return False

    def __hash__(self) -> int:
        return hash((self.type, self.value, self.line, self.column))

    @property
    def location(self) -> str:
        """Get a formatted location string."""
        if self.source_file:
            return f"{self.source_file}:{self.line}:{self.column}"
        return f"L{self.line}:C{self.column}"

    def is_delimiter(self) -> bool:
        """Check if this token is a delimiter type."""
        return self.type in {
            TokenType.COMMENT_START,
            TokenType.COMMENT_END,
            TokenType.ATTR_START,
            TokenType.ATTR_END,
            TokenType.VAR_START,
            TokenType.VAR_END,
            TokenType.IMPORT_START,
            TokenType.IMPORT_END,
            TokenType.JINJA_BLOCK_START,
            TokenType.JINJA_BLOCK_END,
            TokenType.JINJA_COMMENT_START,
            TokenType.JINJA_COMMENT_END,
        }
