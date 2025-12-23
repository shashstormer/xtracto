"""
Layout Manager for xtracto
Handles layout wrapping (_layout.pypx) for pages.
"""
from __future__ import annotations
import os
from typing import Optional, Dict, Any, TYPE_CHECKING
from xtracto.core.logging import get_logger

if TYPE_CHECKING:
    from xtracto.core.config import Config


class LayoutManager:
    """
    Manages layout wrapping for pypx pages.
    Looks for _layout.pypx in the pages directory and wraps
    page content with the layout template.
    Usage:
        layout_mgr = LayoutManager(config)
        wrapped = layout_mgr.apply_layout(page_content)
    """
    LAYOUT_FILENAME = "_layout.pypx"
    CHILDREN_PLACEHOLDERS = ["{{children}}", "{children}"]

    def __init__(self, config: "Config" = None):
        """
        Initialize the layout manager.
        Args:
            config: Optional Config instance
        """
        self._config = config
        self.logger = get_logger("xtracto.layout")
        self._layout_cache: Optional[str] = None
        self._static_requirements: Dict[str, Any] = {}

    @property
    def config(self) -> "Config":
        """Lazy-load config if not provided."""
        if self._config is None:
            from xtracto.core.config import Config
            self._config = Config()
        return self._config

    @property
    def static_requirements(self) -> Dict[str, Any]:
        """Get static requirements from layout parsing."""
        return self._static_requirements

    def has_layout(self) -> bool:
        """Check if a layout file exists."""
        layout_path = os.path.join(str(self.config.pages_root), self.LAYOUT_FILENAME)
        return os.path.exists(layout_path)

    def get_layout_template(self) -> Optional[str]:
        """
        Get the layout template content.
        Returns:
            Layout template string, or None if no layout exists
        """
        if not self.has_layout():
            return None
        if self._layout_cache is not None:
            return self._layout_cache
        self.logger.debug("Loading layout template")
        try:
            from xtracto import Parser
            layout_parser = Parser(path=self.LAYOUT_FILENAME, layout=True)
            self._layout_cache = layout_parser.template_string
            self._static_requirements.update(layout_parser.static_requirements)
            return self._layout_cache
        except Exception as e:
            self.logger.error(f"Error loading layout: {e}")
            return None

    def apply_layout(self, content: str) -> str:
        """
        Apply the layout template to page content.
        Args:
            content: The page content to wrap
        Returns:
            Content wrapped in layout, or original content if no layout
        """
        layout_template = self.get_layout_template()
        if layout_template is None:
            return content
        for placeholder in self.CHILDREN_PLACEHOLDERS:
            if placeholder in layout_template:
                self.logger.debug(f"Applying layout with placeholder: {placeholder}")
                return layout_template.replace(placeholder, content)
        self.logger.warning(
            "Layout file does not contain {{children}} placeholder"
        )
        return content

    def clear_cache(self):
        """Clear the layout cache."""
        self._layout_cache = None
        self._static_requirements = {}
