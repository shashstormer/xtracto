"""
File Manager for xtracto
Handles file I/O with security checks to prevent path traversal attacks.
"""
from __future__ import annotations
import os
from typing import Optional, Union, TYPE_CHECKING
from xtracto.core.logging import get_logger
from xtracto.core.errors import FileError, PathTraversalError

if TYPE_CHECKING:
    from xtracto.core.config import Config


class FileManager:
    """
    Secure file manager for xtracto.
    Provides file reading with path traversal protection.
    Usage:
        fm = FileManager(config)
        content = fm.get_file("component.pypx")
    """

    def __init__(self, config: "Config" = None):
        """
        Initialize the file manager.
        Args:
            config: Optional Config instance. If not provided, will be loaded.
        """
        self._config = config
        self.logger = get_logger("xtracto.file")

    @property
    def config(self) -> "Config":
        """Lazy-load config if not provided."""
        if self._config is None:
            from xtracto.core.config import Config
            self._config = Config()
        return self._config

    def get_file_if_valid(self, path: str) -> Union[str, "Parser", None]:
        """
        Get file content if the path is valid and safe.
        Args:
            path: Relative path to the file
        Returns:
            File content as string, or Parser instance for .pypx files,
            or empty string if invalid/not found
        """
        from xtracto.core.config import Config
        _, file_extension = os.path.splitext(path)
        file_type = file_extension[1:] if file_extension else ""
        module_root = os.path.abspath(str(self.config.module_root))
        full_path = os.path.abspath(os.path.join(module_root, path))
        try:
            if os.path.commonpath([module_root, full_path]) != module_root:
                self.logger.critical(
                    f"Path traversal attempt blocked: {full_path}"
                )
                return ""
        except ValueError:
            self.logger.critical(
                f"Path traversal attempt blocked (different drives): {full_path}"
            )
            return ""
        if not os.path.exists(full_path):
            self.logger.warning(f"File not found: {full_path}")
            return ""
        self.logger.file("Reading", path)
        if file_type == "pypx":
            try:
                from xtracto import Parser
                return Parser(path=path, module=True)
            except Exception as e:
                self.logger.error(f"Error parsing pypx file: {path}", error=str(e))
                return ""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file: {path}", error=str(e))
            return ""

    def read_file(self, path: str, root: str = None) -> str:
        """
        Read a file from the given path.
        Args:
            path: Relative path to the file
            root: Root directory (defaults to module_root)
        Returns:
            File content as string
        Raises:
            FileError: If file cannot be read
        """
        if root is None:
            root = self.config.module_root
        root = os.path.abspath(str(root))
        full_path = os.path.abspath(os.path.join(root, path))
        try:
            if os.path.commonpath([root, full_path]) != root:
                raise PathTraversalError(full_path, root)
        except ValueError:
            raise PathTraversalError(full_path, root)
        if not os.path.exists(full_path):
            raise FileError(f"File not found: {path}", file_path=full_path)
        self.logger.file("Reading", full_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise FileError(f"Error reading file: {e}", file_path=full_path)

    def write_file(self, path: str, content: str, root: str = None):
        """
        Write content to a file.
        Args:
            path: Relative path to the file
            content: Content to write
            root: Root directory (defaults to build_dir)
        Raises:
            FileError: If file cannot be written
        """
        if root is None:
            root = self.config.build_dir
        root = os.path.abspath(str(root))
        full_path = os.path.abspath(os.path.join(root, path))
        try:
            if os.path.commonpath([root, full_path]) != root:
                raise PathTraversalError(full_path, root)
        except ValueError:
            raise PathTraversalError(full_path, root)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        self.logger.file("Writing", full_path)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise FileError(f"Error writing file: {e}", file_path=full_path)

    def file_exists(self, path: str, root: str = None) -> bool:
        """
        Check if a file exists.
        Args:
            path: Relative path to the file
            root: Root directory (defaults to module_root)
        Returns:
            True if file exists
        """
        if root is None:
            root = self.config.module_root
        full_path = os.path.join(root, path)
        return os.path.exists(full_path)
