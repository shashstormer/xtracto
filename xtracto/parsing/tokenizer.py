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
    HTML_ELEMENTS = {
        "!doctype", "a", "abbr", "acronym", "address", "applet", "area", "article",
        "aside", "audio", "b", "base", "basefont", "bdi", "bdo", "bgsound", "big",
        "blockquote", "body", "br", "button", "canvas", "caption", "center", "cite",
        "code", "col", "colgroup", "data", "datalist", "dd", "del", "details", "dfn",
        "dialog", "dir", "div", "dl", "dt", "em", "embed", "fieldset", "figcaption",
        "figure", "font", "footer", "form", "frame", "frameset", "h1", "h2", "h3",
        "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i", "iframe",
        "img", "input", "ins", "isindex", "kbd", "keygen", "label", "legend", "li",
        "link", "main", "map", "mark", "marquee", "menu", "menuitem", "meta", "meter",
        "nav", "nobr", "noembed", "noframes", "noscript", "object", "ol", "optgroup",
        "option", "output", "p", "param", "picture", "pre", "progress", "q", "rp",
        "rt", "ruby", "s", "samp", "script", "section", "select", "small", "source",
        "spacer", "span", "strike", "strong", "style", "sub", "summary", "sup", "svg",
        "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time",
        "title", "tr", "track", "tt", "u", "ul", "var", "video", "wbr", "xmp",
    }

    def __init__(self, source: str, filename: Optional[str] = None):
        """
        Initialize the tokenizer.
        Args:
            source: The source text to tokenize
            filename: Optional filename for error reporting
        """
        source = source.expandtabs(4)
        source = source.replace("\t", "    ")
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.logger = get_logger("xtracto.tokenizer")
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
        if self._peek() == "\n":
            self._advance()
            self._emit(TokenType.NEWLINE, "\n", start_line, start_column)
            self._scan_indentation()
            return
        for delim, token_types in self.DELIMITERS.items():
            if self._peek_string(2) == delim:
                self._advance()
                self._advance()
                self._emit(token_types[0], delim, start_line, start_column)
                return
        char = self._peek()
        if char.isalpha() or char == "_" or char == "!":
            self._scan_identifier_or_text(start_line, start_column)
        elif char == " ":
            self._advance()
        else:
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
        full_content = ""
        while not self._at_end():
            char = self._peek()
            if self._peek_string(2) in self.DELIMITERS:
                break
            if char == "\n":
                break
            full_content += self._advance()
        if not full_content:
            return
        parts = full_content.split(None, 1)
        first_word = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""
        if first_word and self._is_valid_element_name(first_word):
            if rest:
                self._emit(TokenType.IDENTIFIER, first_word, start_line, start_column)
                self._emit(TokenType.TEXT, rest, start_line, start_column + len(first_word) + 1)
            else:
                self._emit(TokenType.IDENTIFIER, first_word, start_line, start_column)
        else:
            self._emit(TokenType.TEXT, full_content, start_line, start_column)

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
            if self._peek_string(2) in self.DELIMITERS:
                break
            if char == "\n":
                break
            value += self._advance()
        return value

    def _is_valid_element_name(self, name: str) -> bool:
        """
        Check if a string is a valid HTML element name.
        Only returns True for known HTML elements to avoid treating
        plain text words like 'Hello' as element names.
        """
        if not name:
            return False
        return name.lower() in self.HTML_ELEMENTS

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
