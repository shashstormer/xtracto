"""
Xtracto Logging System
Comprehensive logging with support for:
- Multiple log levels including TRACE for debugging parser internals
- Source location context in error messages
- Colored output for terminal
- Structured logging for tokenizer/lexer/parser phases
"""
from __future__ import annotations
import logging
import os
import sys
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from xtracto.parsing.tokens import Token
    from xtracto.parsing.ast_nodes import ASTNode
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class LogLevel(IntEnum):
    """Log levels for xtracto logging system."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class ColorCodes:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    LEVEL_COLORS = {
        TRACE: DIM,
        logging.DEBUG: BLUE,
        logging.INFO: CYAN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: RED + BOLD,
    }


class ColoredFormatter(logging.Formatter):
    """Formatter that adds color to log output based on level."""

    def __init__(self, fmt: str = None, use_color: bool = True):
        super().__init__(fmt or "%(levelname)s: %(message)s")
        self.use_color = use_color and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if self.use_color:
            color = ColorCodes.LEVEL_COLORS.get(record.levelno, ColorCodes.RESET)
            return f"{color}{message}{ColorCodes.RESET}"
        return message


class XtractoLogger:
    """
    Comprehensive logger for xtracto with phase-specific logging.
    Usage:
        logger = XtractoLogger("xtracto.parsing")
        logger.trace("Scanning character", char='<', pos=42)
        logger.token("EMIT", token)
        logger.parse("Building element", node=element)
        logger.error_at("Unexpected token", line=10, column=5)
    """

    def __init__(self, name: str = "xtracto", level: int = None):
        self.logger = logging.getLogger(name)
        self._setup_handler()
        if level is not None:
            self.set_level(level)

    def _setup_handler(self):
        """Setup console handler with colored formatter."""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(ColoredFormatter(
                fmt="[%(name)s] %(levelname)s: %(message)s"
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def set_level(self, level: int | str):
        """Set the logging level."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(level)

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context dictionary for log message."""
        if not context:
            return ""
        parts = [f"{k}={v!r}" for k, v in context.items()]
        return " | " + ", ".join(parts)

    def trace(self, msg: str, **context):
        """Extremely verbose logging for debugging parser internals."""
        self.logger.log(TRACE, msg + self._format_context(context))

    def debug(self, msg: str, **context):
        """Debug-level logging."""
        self.logger.debug(msg + self._format_context(context))

    def info(self, msg: str, **context):
        """Info-level logging."""
        self.logger.info(msg + self._format_context(context))

    def warning(self, msg: str, **context):
        """Warning-level logging."""
        self.logger.warning(msg + self._format_context(context))

    def warn(self, msg: str, **context):
        """Alias for warning."""
        self.warning(msg, **context)

    def error(self, msg: str, **context):
        """Error-level logging."""
        self.logger.error(msg + self._format_context(context))

    def critical(self, msg: str, **context):
        """Critical-level logging."""
        self.logger.critical(msg + self._format_context(context))

    def token(self, action: str, token: "Token"):
        """Log tokenizer activity."""
        self.trace(
            f"[TOKENIZER] {action}: {token.type.name}",
            value=token.value[:50] if len(token.value) > 50 else token.value,
            line=token.line,
            col=token.column,
        )

    def lex(self, action: str, **context):
        """Log lexer activity."""
        self.trace(f"[LEXER] {action}", **context)

    def parse(self, action: str, node: "ASTNode" = None, **context):
        """Log parser activity."""
        if node:
            context["node_type"] = type(node).__name__
        self.trace(f"[PARSER] {action}", **context)

    def codegen(self, action: str, **context):
        """Log code generation activity."""
        self.trace(f"[CODEGEN] {action}", **context)

    def file(self, action: str, path: str, **context):
        """Log file operations."""
        self.debug(f"[FILE] {action}: {path}", **context)

    def build(self, action: str, **context):
        """Log build operations."""
        self.info(f"[BUILD] {action}", **context)

    def error_at(
            self,
            message: str,
            line: int,
            column: int,
            source_line: str = None,
            filename: str = None,
    ):
        """Log error with source location context."""
        location = f"{filename}:{line}:{column}" if filename else f"L{line}:C{column}"
        self.error(f"{location}: {message}")
        if source_line:
            self.error(f"  | {source_line}")
            self.error(f"  | {' ' * max(0, column - 1)}^")

    def warning_at(
            self,
            message: str,
            line: int,
            column: int,
            source_line: str = None,
            filename: str = None,
    ):
        """Log warning with source location context."""
        location = f"{filename}:{line}:{column}" if filename else f"L{line}:C{column}"
        self.warning(f"{location}: {message}")
        if source_line:
            self.warning(f"  | {source_line}")


_global_logger: Optional[XtractoLogger] = None


def get_logger(name: str = "xtracto") -> XtractoLogger:
    """Get or create a logger instance."""
    global _global_logger
    if name == "xtracto" and _global_logger is not None:
        return _global_logger
    logger = XtractoLogger(name)
    if name == "xtracto":
        _global_logger = logger
    return logger


def set_log_level(level: int | str):
    """Set the global log level."""
    get_logger().set_level(level)


log = get_logger()


class Log:
    """Legacy Log class for backward compatibility with existing code."""

    def __init__(self):
        pass

    @staticmethod
    def xtracto_initiated():
        pass

    @staticmethod
    def get_logger(config_path=None):
        """Get logger, optionally using legacy requestez.helpers."""
        try:
            import requestez.helpers as ez_helper
            from xtracto.core.config import Config
            if config_path is None:
                config = Config()
            else:
                config = Config(config_path)
            ez_helper.set_log_level(config.log_level)
            logger = ez_helper.get_logger()
            logger.logger = logging.getLogger("xtracto")
            return logger
        except ImportError:
            return get_logger()

    @staticmethod
    def critical(message, config=None):
        try:
            Log.get_logger(config).log("c", msg=message, color="red")
        except (AttributeError, TypeError):
            get_logger().critical(message)

    @staticmethod
    def error(message, *args):
        try:
            Log.get_logger().stack("e", *args, msg=message, color="red")
        except (AttributeError, TypeError):
            get_logger().error(message)

    @staticmethod
    def warn(message):
        try:
            Log.get_logger().log("w", msg=message, color="yellow")
        except (AttributeError, TypeError):
            get_logger().warning(message)

    @staticmethod
    def info(message):
        try:
            Log.get_logger().log("i", msg=message, color="CYAN")
        except (AttributeError, TypeError):
            get_logger().info(message)

    @staticmethod
    def debug(message):
        try:
            Log.get_logger().log("d", msg=message, color="reset")
        except (AttributeError, TypeError):
            get_logger().debug(message)
