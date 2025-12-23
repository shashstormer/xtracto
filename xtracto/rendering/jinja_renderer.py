"""
Jinja2 Renderer for xtracto

Handles Jinja2 template rendering with proper error handling.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from jinja2 import Environment

from xtracto.core.logging import get_logger


class JinjaRenderer:
    """
    Jinja2 template renderer.
    
    Usage:
        renderer = JinjaRenderer()
        html = renderer.render(template_string, {"name": "World"})
    """
    
    def __init__(self, autoescape: bool = True):
        """
        Initialize the Jinja2 renderer.
        
        Args:
            autoescape: Whether to auto-escape variables (default True for XSS protection)
        """
        self.env = Environment(autoescape=autoescape)
        self.logger = get_logger("xtracto.render")
    
    def render(
        self,
        template_string: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render a Jinja2 template string.
        
        Args:
            template_string: The template to render
            context: Variables to pass to the template
        
        Returns:
            Rendered HTML string, or original template if error
        """
        if context is None:
            context = {}
        
        self.logger.debug("Rendering Jinja2 template", vars=list(context.keys()))
        
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"Jinja2 Rendering Error: {e}")
            return template_string
    
    def render_safe(
        self,
        template_string: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Optional[Exception]]:
        """
        Render a template, returning both result and any error.
        
        Args:
            template_string: The template to render
            context: Variables to pass to the template
        
        Returns:
            Tuple of (rendered_content, error_or_none)
        """
        if context is None:
            context = {}
        
        try:
            template = self.env.from_string(template_string)
            return template.render(**context), None
        except Exception as e:
            self.logger.error(f"Jinja2 Rendering Error: {e}")
            return template_string, e
