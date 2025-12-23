"""
Xtracto Error Definitions
Custom exception classes with source location information for precise error reporting.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceLocation:
    """Represents a location in source code for error reporting."""
    line: int
    column: int
    filename: Optional[str] = None
    source_line: Optional[str] = None

    def __str__(self) -> str:
        if self.filename:
            return f"{self.filename}:{self.line}:{self.column}"
        return f"line {self.line}, column {self.column}"

    def format_context(self, context_lines: int = 1) -> str:
        """Format the source location with context for error display."""
        parts = [str(self)]
        if self.source_line:
            parts.append(f"\n  | {self.source_line}")
            parts.append(f"\n  | {' ' * (self.column - 1)}^")
        return "".join(parts)


class XtractoError(Exception):
    """Base exception for all xtracto errors."""

    def __init__(
            self,
            message: str,
            location: Optional[SourceLocation] = None,
            hint: Optional[str] = None,
    ):
        self.message = message
        self.location = location
        self.hint = hint
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = []
        if self.location:
            parts.append(f"[{self.location}] ")
        parts.append(self.message)
        if self.hint:
            parts.append(f"\n  Hint: {self.hint}")
        return "".join(parts)


class ParseError(XtractoError):
    """Error during parsing phase."""
    pass


class TokenizerError(XtractoError):
    """Error during tokenization phase."""
    pass


class LexerError(XtractoError):
    """Error during lexical analysis phase."""
    pass


class SyntaxError(XtractoError):
    """Syntax error in pypx source."""

    def __init__(
            self,
            message: str,
            location: Optional[SourceLocation] = None,
            hint: Optional[str] = None,
            expected: Optional[str] = None,
            found: Optional[str] = None,
    ):
        self.expected = expected
        self.found = found
        if expected and found and not hint:
            hint = f"Expected {expected}, but found {found}"
        super().__init__(message, location, hint)


class ImportError(XtractoError):
    """Error during component import resolution."""

    def __init__(
            self,
            message: str,
            import_path: Optional[str] = None,
            location: Optional[SourceLocation] = None,
            hint: Optional[str] = None,
    ):
        self.import_path = import_path
        super().__init__(message, location, hint)


class ConfigError(XtractoError):
    """Error in configuration loading or validation."""
    pass


class FileError(XtractoError):
    """Error in file operations."""

    def __init__(
            self,
            message: str,
            file_path: Optional[str] = None,
            location: Optional[SourceLocation] = None,
            hint: Optional[str] = None,
    ):
        self.file_path = file_path
        super().__init__(message, location, hint)


class CircularImportError(ImportError):
    """Circular dependency detected in imports."""

    def __init__(
            self,
            message: str,
            import_chain: Optional[list[str]] = None,
            location: Optional[SourceLocation] = None,
    ):
        self.import_chain = import_chain or []
        hint = None
        if import_chain:
            hint = f"Import chain: {' -> '.join(import_chain)}"
        super().__init__(message, location=location, hint=hint)


class PathTraversalError(FileError):
    """Path traversal attempt detected."""

    def __init__(self, attempted_path: str, allowed_root: str):
        super().__init__(
            f"Path traversal attempt blocked",
            file_path=attempted_path,
            hint=f"Access is restricted to: {allowed_root}",
        )


class Error:
    """Legacy Error namespace for backward compatibility."""

    class ProjectConfig:
        message = "Project Config file not found (xtracto.config.py)"
        error = FileNotFoundError(message)
        resolution = "RESOLUTION: Create file 'xtracto.config.py' at your project root directory"

    class LineInsertError:
        class InvalidLineNumber:
            message = "Invalid line number. Please provide a valid line number."
            error = ValueError(message)
            resolution = "RESOLUTION: Enter a valid line number or Check Input Content"
