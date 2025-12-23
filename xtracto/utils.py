"""
Utility functions for xtracto

General-purpose utilities used throughout the library.
"""

from __future__ import annotations

import os
from typing import Any

from xtracto.core.logging import get_logger
from xtracto.core.errors import Error


MAXIMUM_DEPTH_PROJECT_ROOT = 10


class Utils:
    """
    Utility class with static helper methods.
    
    Provides file path utilities, module importing, and text manipulation.
    """
    
    @staticmethod
    def import_module_by_path(module_path: str) -> Any:
        """
        Import a Python module from a file path.
        
        Args:
            module_path: Path to the .py file
        
        Returns:
            The imported module
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("module_name", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    @staticmethod
    def get_project_root() -> str:
        """
        Get the project root directory.
        
        Looks for xtracto.config.py in the current working directory.
        Does NOT traverse upward for security reasons.
        
        Returns:
            Absolute path to project root
        
        Raises:
            FileNotFoundError: If config file not found
        """
        from xtracto.core.logging import Log
        from xtracto.core.config import Config
        
        current_script = os.getcwd()
        if os.path.exists(os.path.join(current_script, 'xtracto.config.py')):
            return current_script
        
        Log.critical(Error.ProjectConfig.message, "")
        try:
            if Config("").debug:
                Log.debug(Error.ProjectConfig.resolution)
        except Exception:
            pass
        raise Error.ProjectConfig.error
    
    @staticmethod
    def get_config_file() -> str:
        """Get the path to the configuration file."""
        return os.path.join(Utils.get_project_root(), "xtracto.config.py")
    
    @staticmethod
    def add_content_at_indent(
        line: int,
        indent: int,
        content: str,
        file_content: str
    ) -> str:
        """
        Insert content at a specific line with given indentation.
        
        Args:
            line: 1-indexed line number to insert at
            indent: Number of spaces for indentation
            content: Content to insert
            file_content: Original file content
        
        Returns:
            Modified file content
        
        Raises:
            ValueError: If line number is invalid
        """
        from xtracto.core.logging import Log
        from xtracto.core.config import Config
        
        lines = file_content.split('\n')
        if 1 <= line <= len(lines):
            target_indent = indent * ' '
            content = content.strip("\n")
            content = content.replace("\n", f"\n{target_indent}")
            new_line = f"{target_indent}{content}"
            lines.insert(line - 1, new_line)
            return '\n'.join(lines)
        else:
            try:
                if Config().debug:
                    Log.error(
                        Error.LineInsertError.InvalidLineNumber.message,
                        line, indent, content, file_content
                    )
                    Log.debug(Error.LineInsertError.InvalidLineNumber.resolution)
            except Exception:
                pass
            raise Error.LineInsertError.InvalidLineNumber.error
    
    @staticmethod
    def root_path(path: str) -> str:
        """
        Get absolute path relative to project root.
        
        Args:
            path: Relative path
        
        Returns:
            Absolute path
        """
        return os.path.join(Utils.get_project_root(), path)
    
    @staticmethod
    def layout_exists() -> bool:
        """Check if a layout file exists."""
        from xtracto.core.config import Config
        return os.path.exists(os.path.join(Config().project_root, "_layout.pypx"))
    
    @staticmethod
    def page_exists(page: str) -> bool:
        """Check if a page file exists."""
        from xtracto.core.config import Config
        return os.path.exists(os.path.join(Config().pages_root, page))
