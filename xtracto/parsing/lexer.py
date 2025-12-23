"""
Lexer for pypx
Processes the raw token stream from the tokenizer:
- Removes comments (:: ... ::)
- Groups multiline constructs when delimiters span lines
- Generates DEDENT tokens from indentation changes
- Filters insignificant whitespace
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from xtracto.core.logging import get_logger
from xtracto.core.errors import LexerError, SourceLocation
from xtracto.parsing.tokens import Token, TokenType


class Lexer:
    """
    Lexer for pypx token streams.
    Processes tokens from the tokenizer to handle:
    - Comment removal
    - Multiline delimiter grouping
    - Indent/dedent tracking
    - Token filtering
    Usage:
        lexer = Lexer(tokens, source_text)
        processed_tokens = lexer.process()
    """
    DELIMITER_PAIRS = {
        TokenType.COMMENT_START: TokenType.COMMENT_START,
        TokenType.VAR_START: TokenType.VAR_END,
        TokenType.ATTR_START: TokenType.ATTR_START,
        TokenType.IMPORT_START: TokenType.IMPORT_END,
        TokenType.JINJA_BLOCK_START: TokenType.JINJA_BLOCK_END,
        TokenType.JINJA_COMMENT_START: TokenType.JINJA_COMMENT_END,
    }

    def __init__(
            self,
            tokens: List[Token],
            source: Optional[str] = None,
            filename: Optional[str] = None,
    ):
        """
        Initialize the lexer.
        Args:
            tokens: Token list from the tokenizer
            source: Original source text (for error context)
            filename: Filename for error reporting
        """
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.pos = 0
        self.output: List[Token] = []
        self.indent_stack: List[int] = [0]
        self.logger = get_logger("xtracto.lexer")

    def process(self) -> List[Token]:
        """
        Process the token stream.
        Returns:
            Processed token list with comments removed, multiline
            constructs grouped, etc.
        Raises:
            LexerError: If processing fails
        """
        self.logger.trace("Starting lexical analysis", token_count=len(self.tokens))
        while not self._at_end():
            self._process_token()
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self._emit_synthetic(TokenType.DEDENT, "")
        self.logger.trace(
            "Lexical analysis complete",
            output_count=len(self.output),
        )
        return self.output

    def _at_end(self) -> bool:
        """Check if we've processed all tokens."""
        return self.pos >= len(self.tokens)

    def _current(self) -> Token:
        """Get the current token."""
        if self._at_end():
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

    def _emit(self, token: Token):
        """Emit a token to the output."""
        self.output.append(token)
        self.logger.lex("EMIT", token_type=token.type.name, value=token.value[:30])

    def _emit_synthetic(self, token_type: TokenType, value: str):
        """Emit a synthetic token (not from source)."""
        current = self._current() if not self._at_end() else self.tokens[-1]
        token = Token(
            type=token_type,
            value=value,
            line=current.line,
            column=current.column,
            source_file=self.filename,
        )
        self.output.append(token)
        self.logger.lex("EMIT_SYNTHETIC", token_type=token_type.name)

    def _process_token(self):
        """Process the current token."""
        token = self._current()
        if token.type == TokenType.COMMENT_START:
            self._skip_comment()
        elif token.type == TokenType.VAR_START:
            self._group_variable()
        elif token.type == TokenType.ATTR_START:
            self._group_attribute()
        elif token.type == TokenType.IMPORT_START:
            self._group_import()
        elif token.type == TokenType.JINJA_BLOCK_START:
            self._group_jinja_block()
        elif token.type == TokenType.JINJA_COMMENT_START:
            self._skip_jinja_comment()
        elif token.type == TokenType.NEWLINE:
            self._handle_newline()
        elif token.type == TokenType.INDENT:
            self._handle_indent()
        elif token.type == TokenType.EOF:
            self._emit(self._advance())
        else:
            self._emit(self._advance())

    def _skip_comment(self):
        """Skip a comment block (:: ... ::)."""
        start_token = self._advance()
        self.logger.lex("SKIP_COMMENT_START", line=start_token.line)
        depth = 1
        while not self._at_end() and depth > 0:
            token = self._advance()
            if token.type == TokenType.COMMENT_START:
                depth -= 1
        self.logger.lex("SKIP_COMMENT_END", line=self._current().line if not self._at_end() else -1)

    def _group_variable(self):
        """Group a variable construct ({{ ... }})."""
        start_token = self._advance()
        content_parts: List[str] = []
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.VAR_END:
                self._advance()
                break
            elif token.type == TokenType.EOF:
                raise LexerError(
                    "Unclosed variable block",
                    location=SourceLocation(
                        line=start_token.line,
                        column=start_token.column,
                        filename=self.filename,
                    ),
                    hint="Add '}}' to close the variable block",
                )
            else:
                content_parts.append(token.value)
                self._advance()
        content = "".join(content_parts).strip()
        grouped_token = Token(
            type=TokenType.VAR_CONTENT,
            value=content,
            line=start_token.line,
            column=start_token.column,
            source_file=self.filename,
        )
        self._emit(grouped_token)

    def _group_attribute(self):
        """Group an attribute construct (;; ... ;;)."""
        start_token = self._advance()
        content_parts: List[str] = []
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.ATTR_START:
                self._advance()
                break
            elif token.type == TokenType.EOF:
                raise LexerError(
                    "Unclosed attribute block",
                    location=SourceLocation(
                        line=start_token.line,
                        column=start_token.column,
                        filename=self.filename,
                    ),
                    hint="Add ';;' to close the attribute block",
                )
            else:
                content_parts.append(token.value)
                self._advance()
        content = "".join(content_parts).strip()
        grouped_token = Token(
            type=TokenType.ATTR_CONTENT,
            value=content,
            line=start_token.line,
            column=start_token.column,
            source_file=self.filename,
        )
        self._emit(grouped_token)

    def _group_import(self):
        """Group an import construct ([[ ... ]])."""
        start_token = self._advance()
        content_parts: List[str] = []
        has_params = False
        path_parts: List[str] = []
        param_parts: List[str] = []
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.IMPORT_END:
                self._advance()
                break
            elif token.type == TokenType.IMPORT_PARAMS:
                has_params = True
                self._advance()
            elif token.type == TokenType.EOF:
                raise LexerError(
                    "Unclosed import block",
                    location=SourceLocation(
                        line=start_token.line,
                        column=start_token.column,
                        filename=self.filename,
                    ),
                    hint="Add ']]' to close the import block",
                )
            else:
                if has_params:
                    param_parts.append(token.value)
                else:
                    path_parts.append(token.value)
                self._advance()
        path = "".join(path_parts).strip()
        params = "".join(param_parts).strip() if has_params else ""
        content = f"{path}||{params}" if has_params else path
        grouped_token = Token(
            type=TokenType.IMPORT_CONTENT,
            value=content,
            line=start_token.line,
            column=start_token.column,
            source_file=self.filename,
        )
        self._emit(grouped_token)

    def _group_jinja_block(self):
        """Group a Jinja2 block ({% ... %})."""
        start_token = self._advance()
        content_parts: List[str] = ["{%"]
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.JINJA_BLOCK_END:
                content_parts.append("%}")
                self._advance()
                break
            elif token.type == TokenType.EOF:
                raise LexerError(
                    "Unclosed Jinja2 block",
                    location=SourceLocation(
                        line=start_token.line,
                        column=start_token.column,
                        filename=self.filename,
                    ),
                    hint="Add '%}' to close the Jinja2 block",
                )
            else:
                content_parts.append(token.value)
                self._advance()
        content = "".join(content_parts)
        grouped_token = Token(
            type=TokenType.JINJA_BLOCK,
            value=content,
            line=start_token.line,
            column=start_token.column,
            source_file=self.filename,
        )
        self._emit(grouped_token)

    def _skip_jinja_comment(self):
        """Skip a Jinja2 comment ({# ... #})."""
        start_token = self._advance()
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.JINJA_COMMENT_END:
                self._advance()
                break
            elif token.type == TokenType.EOF:
                raise LexerError(
                    "Unclosed Jinja2 comment",
                    location=SourceLocation(
                        line=start_token.line,
                        column=start_token.column,
                        filename=self.filename,
                    ),
                    hint="Add '#}' to close the Jinja2 comment",
                )
            else:
                self._advance()

    def _handle_newline(self):
        """Handle a newline token."""
        self._emit(self._advance())

    def _handle_indent(self):
        """Handle indentation and emit INDENT/DEDENT tokens."""
        token = self._advance()
        current_indent = len(token.value)
        prev_indent = self.indent_stack[-1]
        if current_indent > prev_indent:
            self.indent_stack.append(current_indent)
            self._emit(token)
        elif current_indent < prev_indent:
            while len(self.indent_stack) > 1 and self.indent_stack[-1] > current_indent:
                self.indent_stack.pop()
                self._emit_synthetic(TokenType.DEDENT, "")
            if current_indent > 0:
                self._emit(token)
        else:
            self._emit(token)
