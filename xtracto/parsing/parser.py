"""
Parser for pypx
Converts token stream into an Abstract Syntax Tree (AST).
Uses indentation for structure determination.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from xtracto.core.logging import get_logger
from xtracto.core.errors import ParseError, SourceLocation
from xtracto.parsing.tokens import Token, TokenType
from xtracto.parsing.ast_nodes import (
    ASTNode,
    Document,
    Element,
    Attribute,
    TextNode,
    Variable,
    Import,
    JinjaBlock,
)

HTML_ELEMENTS = {
    "!DOCTYPE html", "a", "abbr", "acronym", "address", "applet", "article", "aside",
    "audio", "b", "base", "basefont", "bdi", "bdo", "bgsound", "big", "blockquote",
    "body", "br", "button", "canvas", "caption", "center", "cite", "code", "col",
    "colgroup", "data", "datalist", "dd", "del", "details", "dfn", "dialog", "dir",
    "div", "dl", "dt", "em", "embed", "fieldset", "figcaption", "figure", "font",
    "footer", "form", "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6",
    "head", "header", "hgroup", "hr", "html", "i", "iframe", "img", "input", "ins",
    "isindex", "kbd", "keygen", "label", "legend", "li", "link", "main", "map",
    "mark", "marquee", "menu", "menuitem", "meta", "meter", "nav", "nobr", "noembed",
    "noframes", "noscript", "object", "ol", "optgroup", "option", "output", "p",
    "param", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp",
    "script", "section", "select", "small", "source", "spacer", "span", "strike",
    "strong", "style", "sub", "summary", "sup", "svg", "table", "tbody", "td",
    "template", "textarea", "tfoot", "th", "thead", "time", "title", "tr", "track",
    "tt", "u", "ul", "var", "video", "wbr", "xmp",
}
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class PypxParser:
    """
    Parser for pypx token streams.
    Builds an AST from the token stream, using indentation to determine
    element nesting.
    Usage:
        parser = PypxParser(tokens, source_text, "example.pypx")
        document = parser.parse()
    """

    def __init__(
            self,
            tokens: List[Token],
            source: Optional[str] = None,
            filename: Optional[str] = None,
    ):
        """
        Initialize the parser.
        Args:
            tokens: Token list from the lexer
            source: Original source text (for error context)
            filename: Filename for error reporting
        """
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.pos = 0
        self.logger = get_logger("xtracto.parser")
        self.current_indent = 0

    def parse(self) -> Document:
        """
        Parse the token stream into a Document AST.
        Returns:
            Document node containing the parsed AST
        Raises:
            ParseError: If parsing fails
        """
        self.logger.trace("Starting parsing", token_count=len(self.tokens))
        document = Document(filename=self.filename)
        while not self._at_end():
            node = self._parse_node()
            if node:
                document.children.append(node)
        self.logger.trace(
            "Parsing complete",
            node_count=len(document.children),
        )
        return document

    def _at_end(self) -> bool:
        """Check if we've processed all tokens."""
        return self.pos >= len(self.tokens) or self._current().type == TokenType.EOF

    def _current(self) -> Token:
        """Get the current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Optional[Token]:
        """Look ahead at a token without consuming it."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return None
        return self.tokens[pos]

    def _advance(self) -> Token:
        """Consume and return the current token."""
        token = self._current()
        self.pos += 1
        return token

    def _check(self, *types: TokenType) -> bool:
        """Check if current token is one of the given types."""
        if self._at_end():
            return False
        return self._current().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        """If current token matches, consume and return it."""
        if self._check(*types):
            return self._advance()
        return None

    def _skip_newlines(self):
        """Skip any newline tokens."""
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _parse_node(self) -> Optional[ASTNode]:
        """Parse a single node from the token stream."""
        self._skip_newlines()
        if self._at_end():
            return None
        token = self._current()
        if token.type == TokenType.INDENT:
            self.current_indent = len(token.value)
            self._advance()
            return self._parse_node()
        if token.type == TokenType.DEDENT:
            self._advance()
            return None
        if token.type == TokenType.IDENTIFIER:
            return self._parse_element()
        elif token.type == TokenType.VAR_CONTENT:
            return self._parse_variable()
        elif token.type == TokenType.IMPORT_CONTENT:
            return self._parse_import()
        elif token.type == TokenType.JINJA_BLOCK:
            return self._parse_jinja_block()
        elif token.type == TokenType.ATTR_CONTENT:
            return self._parse_attribute()
        elif token.type == TokenType.TEXT:
            return self._parse_text()
        else:
            self.logger.warning(
                f"Unexpected token type: {token.type}",
                value=token.value[:30],
            )
            self._advance()
            return None

    def _parse_element(self) -> Element:
        """Parse an HTML element."""
        token = self._advance()
        tag_name = token.value
        self.logger.parse(
            "Parsing element",
            tag=tag_name,
            line=token.line,
        )
        element = Element(
            tag_name=tag_name,
            is_void=tag_name.lower() in VOID_ELEMENTS,
            line=token.line,
            column=token.column,
        )
        self._parse_element_content(element)
        return element

    def _parse_element_content(self, element: Element):
        """Parse element attributes and children."""
        element_indent = self.current_indent
        while not self._at_end() and not self._check(TokenType.NEWLINE, TokenType.EOF):
            if self._check(TokenType.ATTR_CONTENT):
                element.add_attribute(self._parse_attribute())
            elif self._check(TokenType.VAR_CONTENT):
                element.add_child(self._parse_variable())
            elif self._check(TokenType.IMPORT_CONTENT):
                element.add_child(self._parse_import())
            elif self._check(TokenType.TEXT):
                element.add_child(self._parse_text())
            else:
                break
        self._match(TokenType.NEWLINE)
        while not self._at_end():
            while self._check(TokenType.DEDENT):
                self._advance()
            if self._check(TokenType.INDENT):
                next_indent = len(self._current().value)
                if next_indent > element_indent:
                    self._advance()
                    self.current_indent = next_indent
                    while not self._at_end() and not self._check(TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT,
                                                                 TokenType.EOF):
                        child = self._parse_node()
                        if child:
                            if isinstance(child, Attribute):
                                element.add_attribute(child)
                            else:
                                element.add_child(child)
                        else:
                            break
                    self._match(TokenType.NEWLINE)
                else:
                    break
            elif self._check(TokenType.NEWLINE):
                self._advance()
            elif self._check(TokenType.EOF):
                break
            else:
                break

    def _parse_attribute(self) -> Attribute:
        """Parse an attribute (;; ... ;;)."""
        token = self._advance()
        self.logger.parse(
            "Parsing attribute",
            content=token.value[:30],
            line=token.line,
        )
        return Attribute(
            content=token.value,
            line=token.line,
            column=token.column,
        )

    def _parse_variable(self) -> Variable:
        """Parse a variable ({{ ... }})."""
        token = self._advance()
        content = token.value
        self.logger.parse(
            "Parsing variable",
            content=content[:30],
            line=token.line,
        )
        name = content
        default_value = None
        if "=" in content:
            parts = content.split("=", 1)
            name = parts[0].strip()
            default_value = parts[1].strip()
        return Variable(
            name=name,
            default_value=default_value,
            raw_content=content,
            line=token.line,
            column=token.column,
        )

    def _parse_import(self) -> Import:
        """Parse an import ([[ ... ]])."""
        token = self._advance()
        content = token.value
        self.logger.parse(
            "Parsing import",
            content=content[:30],
            line=token.line,
        )
        path = content
        params = None
        if "||" in content:
            parts = content.split("||", 1)
            path = parts[0].strip()
            params = parts[1].strip()
        return Import(
            path=path,
            params=params,
            raw_content=content,
            line=token.line,
            column=token.column,
        )

    def _parse_jinja_block(self) -> JinjaBlock:
        """Parse a Jinja2 block ({% ... %})."""
        token = self._advance()
        content = token.value
        self.logger.parse(
            "Parsing Jinja block",
            content=content[:30],
            line=token.line,
        )
        block_type = None
        if content.startswith("{%"):
            inner = content[2:-2].strip() if content.endswith("%}") else content[2:].strip()
            parts = inner.split(None, 1)
            if parts:
                block_type = parts[0]
        return JinjaBlock(
            content=content,
            block_type=block_type,
            line=token.line,
            column=token.column,
        )

    def _parse_text(self) -> TextNode:
        """Parse plain text content."""
        token = self._advance()
        self.logger.parse(
            "Parsing text",
            content=token.value[:30],
            line=token.line,
        )
        return TextNode(
            content=token.value,
            line=token.line,
            column=token.column,
        )

    def get_source_line(self, line_number: int) -> str:
        """Get a specific line from the source for error reporting."""
        if not self.source:
            return ""
        lines = self.source.split("\n")
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""

    def create_location(self, token: Token = None) -> SourceLocation:
        """Create a SourceLocation for error reporting."""
        if token is None:
            token = self._current()
        return SourceLocation(
            line=token.line,
            column=token.column,
            filename=self.filename,
            source_line=self.get_source_line(token.line),
        )
