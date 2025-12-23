"""
Xtracto Configuration

Handles loading and managing project configuration from xtracto.config.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from xtracto.core.errors import ConfigError


MAXIMUM_DEPTH_PROJECT_ROOT = 10


def _get_project_root() -> str:
    """
    Find the project root directory by looking for xtracto.config.py.
    
    Only checks the current working directory (no upward traversal for security).
    """
    current_script = os.getcwd()
    if os.path.exists(os.path.join(current_script, 'xtracto.config.py')):
        return current_script
    raise ConfigError(
        "Project Config file not found (xtracto.config.py)",
        hint="Create file 'xtracto.config.py' at your project root directory",
    )


def _get_config_file() -> str:
    """Get the path to the configuration file."""
    return os.path.join(_get_project_root(), "xtracto.config.py")


def _import_module_by_path(module_path: str) -> Any:
    """Import a Python module from a file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("module_name", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _root_path(path: str, project_root: str) -> str:
    """Get absolute path relative to project root."""
    return os.path.join(project_root, path)


@dataclass
class Config:
    """
    Configuration container for xtracto.
    
    Loads settings from xtracto.config.py or uses defaults.
    
    Attributes:
        project_root: Absolute path to project root directory
        module_root: Directory containing reusable components
        pages_root: Directory containing page files
        build_dir: Output directory for built HTML files
        production: Whether running in production mode
        debug: Enable debug mode (verbose logging)
        log_level: Logging level (trace, debug, info, warning, error)
        strip_imports: Whether to strip import statements from output
        app_start_path: Starting path for the application
        reparse_tailwind: Whether to regenerate Tailwind CSS on render
        raise_value_errors_while_importing: Raise errors during component imports
    """
    
    project_root: str = field(default="")
    module_root: str = field(default="")
    pages_root: str = field(default="")
    build_dir: str = field(default="")
    production: bool = field(default=False)
    debug: bool = field(default=False)
    log_level: str = field(default="info")
    strip_imports: bool = field(default=True)
    app_start_path: str = field(default="/")
    reparse_tailwind: bool = field(default=False)
    raise_value_errors_while_importing: bool = field(default=True)
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            project_root: Optional explicit project root. If None, will be
                         auto-detected by looking for xtracto.config.py.
        """
        if project_root is None:
            try:
                config_module = _import_module_by_path(_get_config_file())
                self.project_root = _get_project_root()
                self.module_root = _root_path(
                    getattr(config_module, "modules_dir", "xtractocomponents"),
                    self.project_root,
                )
                self.pages_root = _root_path(
                    getattr(config_module, "pages_dir", "xtractopages"),
                    self.project_root,
                )
                self.build_dir = _root_path(
                    getattr(config_module, "build_dir", "build"),
                    self.project_root,
                )
                self.production = getattr(
                    config_module, 'production',
                    os.getenv("env", "prod").startswith("dev"),
                )
                self.debug = getattr(
                    config_module, 'debug',
                    os.getenv("env", "prod").startswith("dev"),
                )
                self.log_level = "debug" if self.debug else getattr(
                    config_module, 'log_level', "info"
                )
                self.strip_imports = getattr(config_module, 'strip_imports', True)
                self.app_start_path = getattr(config_module, 'app_start_path', "/")
                self.reparse_tailwind = getattr(config_module, 'reparse_tailwind', False)
                self.raise_value_errors_while_importing = getattr(
                    config_module, 'raise_value_errors_while_importing', True
                )
            except ConfigError:
                # Re-raise config errors
                raise
            except Exception as e:
                raise ConfigError(
                    f"Failed to load configuration: {e}",
                    hint="Check your xtracto.config.py for syntax errors",
                )
        else:
            # Explicit project root provided (used for testing/embedding)
            self.project_root = project_root
            self.module_root = os.getcwd()
            self.pages_root = os.getcwd()
            self.build_dir = os.path.join(project_root, "build")
            self.production = os.getenv("env", "prod").startswith("dev")
            self.debug = os.getenv("env", "prod").startswith("dev")
            self.log_level = "debug" if self.debug else "info"
            self.strip_imports = True
            self.app_start_path = "/"
            self.reparse_tailwind = False
            self.raise_value_errors_while_importing = True
    
    def layout_exists(self) -> bool:
        """Check if a layout file exists in the pages directory."""
        return os.path.exists(os.path.join(self.pages_root, "_layout.pypx"))
    
    def page_exists(self, page: str) -> bool:
        """Check if a page file exists."""
        return os.path.exists(os.path.join(self.pages_root, page))
