"""
Xtracto - A web framework for pypx to HTML transformation
eXtensible, Configurable, and Reusable Automation Component Tool and Organizer
This module provides a parser for pypx (custom markup language) to HTML,
with support for components, layouts, Jinja2 templating, and Tailwind CSS.
Usage:
    from xtracto import Parser, Builder
    # Parse a pypx file
    parser = Parser(path="index.pypx")
    parser.render()
    print(parser.html_content)
    # Build all pages for production
    builder = Builder()
    builder.build()
"""
from __future__ import annotations

__author__ = "shashstormer"
__description__ = "A web framework for integration with pypx"
__version__ = "2.0.0"

import os
import re
from typing import Dict, Any, Optional
from jinja2 import Environment
from pytailwind import Tailwind
from xtracto.core.config import Config
from xtracto.core.logging import Log, get_logger, log
from xtracto.core.errors import Error
from xtracto.core.cache import get_cache, TemplateCache
from xtracto.utils import Utils, MAXIMUM_DEPTH_PROJECT_ROOT
from xtracto.builder import Builder
from xtracto.components.file_manager import FileManager
from xtracto.components.import_resolver import ImportResolver
from xtracto.components.layout_manager import LayoutManager
from xtracto.rendering.jinja_renderer import JinjaRenderer
from xtracto.rendering.tailwind import TailwindIntegration
from xtracto.parsing.tokenizer import Tokenizer
from xtracto.parsing.lexer import Lexer
from xtracto.parsing.parser import PypxParser
from xtracto.parsing.tokens import Token, TokenType
from xtracto.parsing.ast_nodes import Document, Element, TextNode, Variable, Import, JinjaBlock
from xtracto.codegen.html_generator import HTMLGenerator


class Parser:
    """
    High-level parser for pypx files.
    Parses pypx content and renders it to HTML using Jinja2.
    Usage:
        # From file
        parser = Parser(path="index.pypx")
        parser.render(context={"title": "My Page"})
        print(parser.html_content)
        # From content
        parser = Parser(content="html\\n    body\\n        h1\\n            Hello")
        parser.render()
        print(parser.html_content)
    """

    def __init__(
            self,
            path: Optional[str] = None,
            content: Optional[str] = None,
            module: bool = False,
            layout: bool = False,
    ):
        """
        Initialize the parser.
        Args:
            path: Path to .pypx file (relative to pages_root or module_root)
            content: pypx content string
            module: If True, load from module_root instead of pages_root
            layout: If True, skip layout wrapping
        """
        self.config = Config()
        self.raw_type = "path" if path is not None else "content"
        self.raw_origin = path if path is not None else content
        self.module = module
        self.layout = layout
        self.html_content = ""
        self.static_requirements: Dict[str, Any] = {}
        self.template_string = ""
        self.logger = get_logger("xtracto.parser")
        if path and not module and not layout and self.config.production:
            build_path = os.path.join(
                str(self.config.build_dir),
                os.path.splitext(path)[0] + ".html"
            )
            if os.path.exists(build_path):
                self.logger.debug(f"Loading pre-built file: {build_path}")
                with open(build_path) as f:
                    self.template_string = f.read()
                return
        if path:
            if module:
                _fpath = os.path.join(str(self.config.module_root), path)
                layout = True
            else:
                _fpath = os.path.join(str(self.config.pages_root), path)
            with open(_fpath) as f:
                self.content = f.read()
            self._cache = get_cache(self.config)
            self._content_hash = self._cache.content_hash(self.content)
            cached_template = self._cache.get_template(path, self._content_hash)
            if cached_template is not None:
                self.template_string = cached_template
                self.logger.debug(f"Using cached template: {path}")
                return
        else:
            self.content = content or ""
            self._cache = get_cache(self.config)
            self._content_hash = self._cache.content_hash(self.content)
        self.pypx_parser = Pypx(self.content, self.raw_origin)
        self._parse(layout)
        if self.raw_type == "path" and self.raw_origin:
            self._cache.set_template(self.raw_origin, self._content_hash, self.template_string)

    def _parse(self, layout: bool = False, layout_mode: Optional[str] = None):
        """Parse the pypx content."""
        self.pypx_parser.parse(layout, layout_mode=layout_mode)
        self.pypx_parser.do_imports()
        if not self.module:
            self.static_requirements.update(self.pypx_parser.static_requirements)
        self.template_string = self.pypx_parser.parsed

    def render(
            self,
            context: Optional[Dict[str, Any]] = None,
            layout_mode: Optional[str] = None,
    ):
        """
        Render the template with the given context.
        Args:
            context: Dictionary of variables to pass to the template
            layout_mode: Optional layout mode override:
                - 'replace' (default): Replace any outer layout with this one
                - 'stack': Stack layouts (inner layouts wrap content, outer layouts wrap inner)
        In production mode, uses Jinja2 bytecode caching for faster rendering.
        """
        if context is None:
            context = {}
        self.logger.debug("Rendering template", vars=list(context.keys()))
        try:
            cache = get_cache(self.config)
            self.html_content = cache.render_template(self.template_string, context)
        except Exception as e:
            self.logger.error(f"Jinja2 Rendering Error: {e}")
            self.html_content = self.template_string
        if self.config.reparse_tailwind:
            self._load_tailwind()

    def _load_tailwind(self):
        """Generate and inject Tailwind CSS as a style element."""
        _tailwind = Tailwind()
        scan_content = self.html_content
        for scan_dir in self.config.tailwind_scan_dirs:
            if os.path.isdir(scan_dir):
                for root, _, files in os.walk(scan_dir):
                    for file in files:
                        if file.endswith(('.pypx', '.html', '.js', '.jsx', '.ts', '.tsx', '.vue')):
                            try:
                                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                    scan_content += f.read()
                            except Exception:
                                pass
        _generated = _tailwind.generate(scan_content)
        if not _generated:
            return
        style_element = f"<style>{_generated}</style>"
        if "</head>" in self.html_content:
            self.html_content = self.html_content.replace(
                "</head>", f"{style_element}</head>"
            )
        elif "<body>" in self.html_content:
            self.html_content = self.html_content.replace(
                "<body>", f"<body>{style_element}"
            )
        else:
            self.html_content = style_element + self.html_content

    def clear_variables(self):
        """Clear any cached variables (reserved for future use)."""
        pass


class Pypx:
    """
    Core pypx parser using tokenizer/lexer/parser pipeline.
    Parses pypx content into HTML with support for:
    - Indentation-based structure
    - Comments (:: ... ::)
    - Attributes (;; ... ;;)
    - Variables ({{ ... }})
    - Imports ([[ ... ]])
    - Jinja2 blocks ({% ... %})
    This class now uses the modular parsing pipeline:
    Tokenizer → Lexer → Parser → HTMLGenerator
    """

    def __init__(self, content: Optional[str] = None, fname: Optional[str] = None):
        """
        Initialize the pypx parser.
        Args:
            content: pypx content string
            fname: Filename for error reporting
        """
        if content is None:
            content = ""
        content = content.expandtabs(4)
        content = content.replace("\t", "    ")
        self.content = content
        self._content_lines = content.split("\n")
        self.fname = fname
        self.parsed = ""
        self.ast = None
        self.static_requirements: Dict[str, Any] = {}
        self.logger = get_logger("xtracto.pypx")
        self.parsing = self._content_lines.copy()
        self.groups = [
            ["::", "::"],
            ["{{", "}}"],
            [";;", ";;"],
            ["[[", "]]"],
        ]

    def make_groups_valid(self):
        """
        Legacy method - multiline grouping is now handled by the lexer.
        This method exists for backward compatibility with tests.
        """
        pass

    def parse(self, layout: bool = False, layout_mode: Optional[str] = None):
        """
        Parse the pypx content using the tokenizer/lexer/parser pipeline.
        Args:
            layout: If True, skip layout wrapping
            layout_mode: Layout behavior mode ('replace' or 'stack')
        """
        self.logger.trace("Starting pypx parsing", filename=self.fname)
        self.logger.trace("Tokenizing content")
        tokenizer = Tokenizer(self.content, self.fname)
        tokens = tokenizer.tokenize()
        self.logger.trace("Lexing token stream", token_count=len(tokens))
        lexer = Lexer(tokens, self.content, self.fname)
        processed_tokens = lexer.process()
        self.logger.trace("Parsing into AST", token_count=len(processed_tokens))
        parser = PypxParser(processed_tokens, self.content, self.fname)
        self.ast = parser.parse()
        self.logger.trace("Generating HTML from AST")
        generator = HTMLGenerator(self.ast)
        self.parsed = generator.generate()
        self.convert_variables_to_jinja()
        if not layout:
            self.use_layout(layout_mode=layout_mode)
        self.logger.trace("Pypx parsing complete")

    def convert_variables_to_jinja(self):
        """Convert {{ var=default }} to Jinja2 default filter syntax."""

        def replace_default(match):
            var = match.group(1).strip()
            default = match.group(2).strip()
            return f"{{{{ {var} | default('{default}') }}}}"

        self.parsed = re.sub(r'\{\{\s*([^=}]+?)\s*=\s*(.*?)\s*\}\}', replace_default, self.parsed)

    def use_layout(self, layout_mode: Optional[str] = None, _depth: int = 0):
        """
        Apply layout wrapper if _layout.pypx exists.
        Args:
            layout_mode: Layout behavior mode:
                - 'replace' (default): Replace any outer layout with this one
                - 'stack': Stack layouts (inner layouts wrap content, outer layouts wrap inner)
            _depth: Internal recursion depth counter to prevent infinite loops
        """
        if _depth > 10:
            log.error("Layout nesting too deep (max 10 levels)")
            return
        config = Config()
        if layout_mode is None:
            layout_mode = config.layout_mode
        _layout_file = os.path.join(str(config.pages_root), "_layout.pypx")
        if not os.path.exists(_layout_file):
            return
        layout_parser = Parser(path="_layout.pypx", layout=True)
        layout_tpl = layout_parser.template_string
        children_pattern = re.compile(r'\{\{\s*children\s*\}\}')
        has_children = children_pattern.search(layout_tpl) is not None or "{children}" in layout_tpl
        if not has_children:
            log.warn("Layout file does not contain {{children}} placeholder")
            return
        self.parsed = children_pattern.sub(self.parsed, layout_tpl) if children_pattern.search(
            layout_tpl) else layout_tpl.replace("{children}", self.parsed)
        self.static_requirements.update(layout_parser.static_requirements)
        if layout_mode == 'stack':
            parent_layout_match = re.search(r'\[\[\s*_parent\.pypx\s*\]\]', layout_tpl)
            if parent_layout_match:
                self.use_layout(layout_mode=layout_mode, _depth=_depth + 1)

    def do_imports(self, content: Optional[str] = None) -> str:
        """Resolve component imports ([[ ... ]])."""
        ori_cont = content
        if content is None:
            content = self.parsed
        regex = re.compile(r"\[\[\s*([a-zA-Z0-9. _/\\-]+)\s*(?:\|\|\s*(.*?))?\s*\]\]")

        def replace_import(match):
            filename = match.group(1).strip()
            params_str = match.group(2)
            cont = FileManager().get_file_if_valid(filename)
            if isinstance(cont, Parser):
                self.static_requirements.update(cont.static_requirements)
                file_content = cont.template_string
            else:
                file_content = str(cont)
            if params_str:
                return f"{{% with {params_str} %}}{file_content}{{% endwith %}}"
            return file_content

        old_content = ""
        loops = 0
        MAX_LOOPS = 100
        while old_content != content:
            if loops > MAX_LOOPS:
                log.error("Circular dependency or too deep recursion detected in imports")
                break
            loops += 1
            old_content = content
            content = regex.sub(replace_import, content)
        if ori_cont is None:
            self.parsed = content
        return content


__all__ = [
    "Parser",
    "Builder",
    "Pypx",
    "Config",
    "Utils",
    "Log",
    "log",
    "Error",
    "FileManager",
    "TemplateCache",
    "get_cache",
    "MAXIMUM_DEPTH_PROJECT_ROOT",
    "Tokenizer",
    "Lexer",
    "PypxParser",
    "HTMLGenerator",
    "Token",
    "TokenType",
]
