"""
Import Resolver for xtracto
Resolves component imports ([[ ... ]]) in parsed content.
"""
from __future__ import annotations
import re
from typing import Optional, Set, Dict, Any, TYPE_CHECKING
from xtracto.core.logging import get_logger
from xtracto.core.errors import ImportError as PypxImportError, CircularImportError

if TYPE_CHECKING:
    from xtracto.core.config import Config


class ImportResolver:
    """
    Resolves component imports in pypx content.
    Handles [[file.pypx]] and [[file.pypx || params]] syntax,
    with circular dependency detection.
    Usage:
        resolver = ImportResolver(config)
        resolved_content = resolver.resolve(content)
    """
    IMPORT_PATTERN = re.compile(r"\[\[\s*([a-zA-Z0-9. _/\\-]+)\s*(?:\|\|\s*(.*?))?\s*\]\]")
    MAX_DEPTH = 100

    def __init__(self, config: "Config" = None):
        """
        Initialize the import resolver.
        Args:
            config: Optional Config instance
        """
        self._config = config
        self.logger = get_logger("xtracto.import")
        self.static_requirements: Dict[str, Any] = {}
        self._import_stack: Set[str] = set()
        self._depth = 0

    @property
    def config(self) -> "Config":
        """Lazy-load config if not provided."""
        if self._config is None:
            from xtracto.core.config import Config
            self._config = Config()
        return self._config

    def resolve(self, content: str, current_file: str = None) -> str:
        """
        Resolve all imports in the content.
        Args:
            content: Content with [[...]] import statements
            current_file: Current file path for circular dependency detection
        Returns:
            Content with imports resolved
        Raises:
            CircularImportError: If circular dependency detected
            PypxImportError: If import fails
        """
        self._depth = 0
        self._import_stack = set()
        if current_file:
            self._import_stack.add(current_file)
        return self._resolve_imports(content)

    def _resolve_imports(self, content: str) -> str:
        """
        Internal method to resolve imports with recursion tracking.
        """
        old_content = ""
        while old_content != content:
            self._depth += 1
            if self._depth > self.MAX_DEPTH:
                self.logger.error(
                    "Circular dependency or too deep recursion detected in imports"
                )
                break
            old_content = content
            content = self.IMPORT_PATTERN.sub(self._replace_import, content)
        return content

    def _replace_import(self, match: re.Match) -> str:
        """
        Replace a single import match with its content.
        """
        filename = match.group(1).strip()
        params_str = match.group(2)
        self.logger.debug(f"Resolving import: {filename}")
        if filename in self._import_stack:
            self.logger.warning(
                f"Circular import detected: {filename}",
                stack=list(self._import_stack),
            )
            return ""
        self._import_stack.add(filename)
        try:
            from xtracto.components.file_manager import FileManager
            fm = FileManager(self._config)
            cont = fm.get_file_if_valid(filename)
            if cont is None or cont == "":
                self.logger.warning(f"Import not found or empty: {filename}")
                return ""
            from xtracto import Parser
            if isinstance(cont, Parser):
                self.static_requirements.update(cont.static_requirements)
                file_content = cont.template_string
            else:
                file_content = str(cont)
            if params_str:
                return f"{{% with {params_str} %}}{file_content}{{% endwith %}}"
            return file_content
        finally:
            self._import_stack.discard(filename)

    def clear(self):
        """Clear resolver state."""
        self.static_requirements = {}
        self._import_stack = set()
        self._depth = 0
