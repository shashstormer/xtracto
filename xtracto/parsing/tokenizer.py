"""
Tokenizer for pypx

Converts raw pypx source text into a stream of tokens.
Character-by-character scanning with source location tracking.
"""

from __future__ import annotations

from typing import List, Optional

from xtracto.core.logging import get_logger
from xtracto.core.errors import TokenizerError, SourceLocation
from xtracto.parsing.tokens import Token, TokenType


class Tokenizer:
    """
    Tokenizer for pypx source files.
    
    Converts source text into a stream of tokens, tracking line and column
    numbers for error reporting.
    
    Usage:
        tokenizer = Tokenizer(source_text, "example.pypx")
        tokens = tokenizer.tokenize()
    """
    
    # Two-character delimiters (order matters - check longer first)
    DELIMITERS = {
        "::": (TokenType.COMMENT_START, TokenType.COMMENT_END),
        "{{": (TokenType.VAR_START,),
        "}}": (TokenType.VAR_END,),
        ";;": (TokenType.ATTR_START, TokenType.ATTR_END),
        "[[": (TokenType.IMPORT_START,),
        "]]": (TokenType.IMPORT_END,),
        "||": (TokenType.IMPORT_PARAMS,),
        "{%": (TokenType.JINJA_BLOCK_START,),
        "%}": (TokenType.JINJA_BLOCK_END,),
        "{#": (TokenType.JINJA_COMMENT_START,),
        "#}": (TokenType.JINJA_COMMENT_END,),
    }
    
    def __init__(self, source: str, filename: Optional[str] = None):
        """
        Initialize the tokenizer.
        
        Args:
            source: The source text to tokenize
            filename: Optional filename for error reporting
        """
        # Normalize tabs to spaces
        source = source.expandtabs(4)
        source = source.replace("\t", "    ")
        
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.logger = get_logger("xtracto.tokenizer")
        
        # Track delimiter state for balanced checking
        self._delimiter_stack: List[tuple[str, int, int]] = []
    
    def tokenize(self) -> List[Token]:
        """
        Tokenize the source and return the token list.
        
        Returns:
            List of Token objects
        
        Raises:
            TokenizerError: If tokenization fails
        """
        self.logger.trace("Starting tokenization", filename=self.filename)
        
        while not self._at_end():
            self._scan_token()
        
        self._emit(TokenType.EOF, "")
        
        self.logger.trace(
            "Tokenization complete",
            token_count=len(self.tokens),
            filename=self.filename,
        )
        
        return self.tokens
    
    def _at_end(self) -> bool:
        """Check if we've reached the end of source."""
        return self.pos >= len(self.source)
    
    def _peek(self, offset: int = 0) -> str:
        """Look at a character without consuming it."""
        pos = self.pos + offset
        if pos >= len(self.source):
            return "\0"
        return self.source[pos]
    
    def _peek_string(self, length: int) -> str:
        """Look at multiple characters without consuming them."""
        return self.source[self.pos:self.pos + length]
    
    def _advance(self) -> str:
        """Consume and return the current character."""
        char = self._peek()
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def _emit(self, token_type: TokenType, value: str, line: int = None, column: int = None):
        """Emit a token."""
        token = Token(
            type=token_type,
            value=value,
            line=line or self.line,
            column=column or self.column,
            source_file=self.filename,
        )
        self.tokens.append(token)
        self.logger.token("EMIT", token)
    
    def _match(self, expected: str) -> bool:
        """Check if current position matches expected string, consume if so."""
        if self._peek_string(len(expected)) == expected:
            for _ in expected:
                self._advance()
            return True
        return False
    
    def _scan_token(self):
        """Scan and emit the next token(s)."""
        start_line = self.line
        start_column = self.column
        
        # Check for newline
        if self._peek() == "\n":
            self._advance()
            self._emit(TokenType.NEWLINE, "\n", start_line, start_column)
            # Scan indentation at start of new line
            self._scan_indentation()
            return
        
        # Check for two-character delimiters
        for delim, token_types in self.DELIMITERS.items():
            if self._peek_string(2) == delim:
                self._advance()
                self._advance()
                # Use first token type (start)
                self._emit(token_types[0], delim, start_line, start_column)
                return
        
        # If at start of line (after newline or at beginning), scan identifier or text
        # Otherwise scan text content
        char = self._peek()
        
        if char.isalpha() or char == "_" or char == "!":
            # Could be an identifier (element name) or text
            self._scan_identifier_or_text(start_line, start_column)
        elif char == " ":
            # Skip non-significant whitespace (not at line start)
            self._advance()
        else:
            # Other characters - scan as text
            self._scan_text(start_line, start_column)
    
    def _scan_indentation(self):
        """Scan and emit indentation at the start of a line."""
        start_column = self.column
        indent = ""
        
        while self._peek() == " ":
            indent += self._advance()
        
        if indent:
            self._emit(TokenType.INDENT, indent, self.line, start_column)
    
    def _scan_identifier_or_text(self, start_line: int, start_column: int):
        """Scan an identifier (element name) or text content."""
        value = ""
        
        # Collect alphanumeric and allowed chars
        while not self._at_end():
            char = self._peek()
            
            # Check for delimiter
            if self._peek_string(2) in self.DELIMITERS:
                break
            
            # Stop at newline
            if char == "\n":
                break
            
            # Continue with identifier-valid characters
            if char.isalnum() or char in "_-!":
                value += self._advance()
            else:
                # Switch to text mode if we hit non-identifier char
                value += self._scan_text_until_delimiter()
                break
        
        if value:
            # Determine if this is an identifier or text
            # Identifiers are typically single words at the start of a line
            if value.replace("-", "").replace("_", "").replace("!", "").replace(" ", "").isalnum():
                # Check if it looks like an HTML element name
                first_word = value.split()[0] if " " in value else value
                if self._is_valid_element_name(first_word):
                    self._emit(TokenType.IDENTIFIER, first_word, start_line, start_column)
                    # Emit rest as text if there's more
                    rest = value[len(first_word):].lstrip()
                    if rest:
                        self._emit(TokenType.TEXT, rest, start_line, start_column + len(first_word) + 1)
                else:
                    self._emit(TokenType.TEXT, value, start_line, start_column)
            else:
                self._emit(TokenType.TEXT, value, start_line, start_column)
    
    def _scan_text(self, start_line: int, start_column: int):
        """Scan text content until a delimiter or newline."""
        value = self._scan_text_until_delimiter()
        if value:
            self._emit(TokenType.TEXT, value, start_line, start_column)
    
    def _scan_text_until_delimiter(self) -> str:
        """Scan text until a delimiter or newline is found."""
        value = ""
        
        while not self._at_end():
            char = self._peek()
            
            # Check for delimiter
            if self._peek_string(2) in self.DELIMITERS:
                break
            
            # Stop at newline
            if char == "\n":
                break
            
            value += self._advance()
        
        return value
    
    def _is_valid_element_name(self, name: str) -> bool:
        """Check if a string is a valid HTML element or pypx element name."""
        if not name:
            return False
        
        # Must start with letter or !
        if not (name[0].isalpha() or name[0] == "!"):
            return False
        
        # Rest can be alphanumeric, hyphen, or underscore
        for char in name[1:]:
            if not (char.isalnum() or char in "-_"):
                return False
        
        return True
    
    def get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source for error reporting."""
        lines = self.source.split("\n")
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""
    
    def create_location(self, line: int = None, column: int = None) -> SourceLocation:
        """Create a SourceLocation for error reporting."""
        line = line or self.line
        column = column or self.column
        return SourceLocation(
            line=line,
            column=column,
            filename=self.filename,
            source_line=self.get_source_line(line),
        )
