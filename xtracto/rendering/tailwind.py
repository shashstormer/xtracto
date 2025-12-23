"""
Tailwind CSS Integration for xtracto
Handles Tailwind CSS generation using pytailwind.
"""
from __future__ import annotations
from typing import Optional
from xtracto.core.logging import get_logger


class TailwindIntegration:
    """
    Tailwind CSS integration for xtracto.
    Usage:
        tailwind = TailwindIntegration()
        css = tailwind.generate(html_content)
        final_html = tailwind.inject(html_content, css)
    """
    PLACEHOLDER = "{{generated_tailwind}}"

    def __init__(self):
        """Initialize Tailwind integration."""
        self.logger = get_logger("xtracto.tailwind")
        self._tailwind = None

    @property
    def tailwind(self):
        """Lazy-load pytailwind."""
        if self._tailwind is None:
            try:
                from pytailwind import Tailwind
                self._tailwind = Tailwind()
            except ImportError:
                self.logger.warning(
                    "pytailwind not installed. Tailwind CSS generation disabled."
                )
                self._tailwind = None
        return self._tailwind

    def generate(self, html_content: str) -> str:
        """
        Generate Tailwind CSS for the given HTML content.
        Args:
            html_content: HTML to analyze for Tailwind classes
        Returns:
            Generated CSS string, or empty string if unavailable
        """
        if self.tailwind is None:
            return ""
        self.logger.debug("Generating Tailwind CSS")
        try:
            return self.tailwind.generate(html_content) or ""
        except Exception as e:
            self.logger.error(f"Tailwind generation error: {e}")
            return ""

    def inject(self, html_content: str, css: str = None) -> str:
        """
        Inject generated CSS into HTML content.
        Args:
            html_content: HTML with {{generated_tailwind}} placeholder
            css: CSS to inject (if None, generates from content)
        Returns:
            HTML with CSS injected at placeholder
        """
        if css is None:
            css = self.generate(html_content)
        if css and self.PLACEHOLDER not in html_content:
            self.logger.warning(
                f'Tailwind generated but no "{self.PLACEHOLDER}" placeholder found in template.'
            )
        return html_content.replace(self.PLACEHOLDER, css)
