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

# Import from new modular structure
from xtracto.core.config import Config
from xtracto.core.logging import Log, get_logger, log
from xtracto.core.errors import Error
from xtracto.utils import Utils, MAXIMUM_DEPTH_PROJECT_ROOT
from xtracto.builder import Builder
from xtracto.components.file_manager import FileManager
from xtracto.components.import_resolver import ImportResolver
from xtracto.components.layout_manager import LayoutManager
from xtracto.rendering.jinja_renderer import JinjaRenderer
from xtracto.rendering.tailwind import TailwindIntegration

# Import parsing components for internal use
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
        
        # Check for pre-built file in production mode
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
        
        # Load content
        if path:
            if module:
                _fpath = os.path.join(str(self.config.module_root), path)
                layout = True  # Don't apply layout to modules
            else:
                _fpath = os.path.join(str(self.config.pages_root), path)
            
            with open(_fpath) as f:
                self.content = f.read()
        else:
            self.content = content or ""
        
        # Parse using new tokenizer/lexer/parser pipeline
        self.pypx_parser = Pypx(self.content, self.raw_origin)
        self._parse(layout)
    
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
        """
        if context is None:
            context = {}
        
        self.logger.debug("Rendering template", vars=list(context.keys()))

        try:
            env = Environment(autoescape=True)
            template = env.from_string(self.template_string)
            self.html_content = template.render(**context)
        except Exception as e:
            self.logger.error(f"Jinja2 Rendering Error: {e}")
            self.html_content = self.template_string

        if self.config.reparse_tailwind:
            self._load_tailwind()

    def _load_tailwind(self):
        """Generate and inject Tailwind CSS as a style element."""
        _tailwind = Tailwind()
        
        # Collect content from configured scan directories
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
                                pass  # Skip unreadable files
        
        _generated = _tailwind.generate(scan_content)
        
        if not _generated:
            return
        
        # Create the style element
        style_element = f"<style>{_generated}</style>"
        
        # Try to inject into <head> if it exists
        if "</head>" in self.html_content:
            self.html_content = self.html_content.replace(
                "</head>", f"{style_element}</head>"
            )
        elif "<body>" in self.html_content:
            # Inject after <body> tag
            self.html_content = self.html_content.replace(
                "<body>", f"<body>{style_element}"
            )
        else:
            # Prepend to the beginning of the content
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
        
        # Normalize tabs to 4 spaces
        content = content.expandtabs(4)
        content = content.replace("\t", "    ")
        
        self.content = content.split("\n")
        self.fname = fname
        self.parsing = self.content.copy()
        
        # Delimiter pairs for balanced checking
        self.groups = [
            ["::", "::"],
            ["{{", "}}"],
            [";;", ";;"],
            ["[[", "]]"],
        ]
        
        # Void HTML elements (self-closing)
        self.void_elements = [
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        ]
        
        # Elements that should have closing tags
        self.elements = [
            "!DOCTYPE html", "abbreviation", "acronym", "address", "anchor", "applet",
            "article", "aside", "audio", "basefont", "bdi", "bdo", "bgsound", "big",
            "blockquote", "body", "bold", "break", "button", "caption", "canvas",
            "center", "cite", "code", "colgroup", "column", "comment", "data",
            "datalist", "dd", "define", "delete", "details", "dialog", "dir", "div",
            "dl", "dt", "embed", "fieldset", "figcaption", "figure", "font", "footer",
            "form", "frame", "frameset", "head", "header", "heading", "hgroup", "html",
            "iframe", "ins", "isindex", "italic", "kbd", "keygen", "label", "legend",
            "list", "main", "mark", "marquee", "menuitem", "meter", "nav", "nobreak",
            "noembed", "noscript", "object", "optgroup", "option", "output",
            "paragraphs", "phrase", "pre", "progress", "q", "rp", "rt", "ruby", "s",
            "samp", "section", "small", "spacer", "span", "strike", "strong", "style",
            "sub", "sup", "summary", "svg", "table", "tbody", "td", "template", "tfoot",
            "th", "thead", "time", "title", "tr", "tt", "underline", "var", "video", "xmp",
        ]
        
        self.parsed = ""
        self.blocks = []
        self.static_requirements: Dict[str, Any] = {}
        self.logger = get_logger("xtracto.pypx")
    
    def parse(self, layout: bool = False, layout_mode: Optional[str] = None):
        """
        Parse the pypx content.
        
        Args:
            layout: If True, skip layout wrapping
            layout_mode: Layout behavior mode ('replace' or 'stack')
        """
        self.logger.trace("Starting pypx parsing", filename=self.fname)
        
        self.make_groups_valid()
        self.parse_comments()
        self.parse_blocks()
        self.load_blocks()
        self.normalize()
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
        
        # Parse the layout file (without applying its own layout yet)
        layout_parser = Parser(path="_layout.pypx", layout=True)
        layout_tpl = layout_parser.template_string
        
        # Check for children placeholder
        has_children = "{{children}}" in layout_tpl or "{children}" in layout_tpl
        
        if not has_children:
            log.warn("Layout file does not contain {{children}} placeholder")
            return
        
        # Apply the layout
        if "{{children}}" in layout_tpl:
            self.parsed = layout_tpl.replace("{{children}}", self.parsed)
        else:
            self.parsed = layout_tpl.replace("{children}", self.parsed)
        
        self.static_requirements.update(layout_parser.static_requirements)
        
        # Check if layout itself has a nested layout reference
        # Nested layouts use [[_parent_layout.pypx]] or similar patterns
        if layout_mode == 'stack':
            # In stack mode, check for parent layout in the layout file itself
            parent_layout_match = re.search(r'\[\[\s*_parent\.pypx\s*\]\]', layout_tpl)
            if parent_layout_match:
                # Recursively apply parent layout
                self.use_layout(layout_mode=layout_mode, _depth=_depth + 1)
    
    def make_groups_valid(self):
        """Join multiline constructs when delimiters are unbalanced."""
        num = 0
        while num < len(self.parsing):
            line = self.parsing[num]
            for value1, value2 in self.groups:
                while True:
                    if value1 == value2:
                        is_unbalanced = (line.count(value1) % 2 != 0)
                    else:
                        is_unbalanced = (line.count(value1) != line.count(value2))
                    
                    if not is_unbalanced:
                        break
                    
                    if num + 1 >= len(self.parsing):
                        raise SyntaxError(
                            f"Unbalanced '{value1}' starting at line {num + 1} in file {self.fname}"
                        )
                    
                    self.parsing[num] += "#&N#" + self.parsing[num + 1]
                    self.parsing.pop(num + 1)
                    line = self.parsing[num]
            num += 1
    
    def parse_comments(self):
        """Remove comments (:: ... ::) from content."""
        self.parsing = [
            i for i in
            re.sub("(::.*?::)", "", "\n".join(self.parsing)).split("\n")
            if i
        ]
    
    def normalize(self, content: Optional[str] = None) -> str:
        """Normalize content by replacing line continuation markers."""
        ori_content = content
        if content is None:
            content = self.parsed
        
        content = content.replace("#&N#", "\n")
        
        if ori_content is None:
            self.parsed = content
        return content
    
    def parse_blocks(self):
        """Parse indentation-based block structure."""
        stack = []
        parent_indent = []
        
        for line in self.parsing:
            indent = len(line) - len(line.lstrip(" "))
            line = line.lstrip(" ")
            
            if not line:
                continue
            
            if not stack:
                stack.append([indent, line, []])
                parent_indent.append(indent)
                continue
            
            curr_depth = 0
            parent = stack
            
            while (curr_depth < len(parent_indent)) and (indent > parent_indent[curr_depth]):
                if indent == parent_indent[curr_depth]:
                    break
                curr_depth += 1
                parent = parent[-1]
                if len(parent) == 3:
                    parent = parent[2]
                if not parent:
                    break
            
            parent_indent = parent_indent[:curr_depth]
            parent.append([indent, line, []])
            parent_indent.append(indent)
        
        self.blocks = stack
    
    def load_blocks(self, blocks=None) -> str:
        """Convert block structure to HTML."""
        if blocks is None:
            blocks = self.blocks.copy()
        
        loaded_block = ""
        
        for block in blocks:
            if block[2]:
                loaded_block += "<" + block[1]
                
                # Extract attributes from children
                for child in block[2].copy():
                    if child[1].startswith(";;"):
                        loaded_block += " " + child[1][2:-2]
                        block[2].remove(child)
                
                if not block[2]:
                    if block[1].lower() in self.elements:
                        loaded_block += f"></{block[1]}>"
                    else:
                        loaded_block += " />"
                else:
                    loaded_block += ">"
                    loaded_block += self.load_blocks(block[2])
                
                loaded_block += f"</{block[1]}>"
            elif not block[2]:
                loaded_block += block[1]
                loaded_block += "\n"
        
        if blocks == self.blocks:
            self.parsed = loaded_block
        
        return loaded_block
    
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


# Public API exports
__all__ = [
    # Main classes
    "Parser",
    "Builder", 
    "Pypx",
    "Config",
    
    # Utilities
    "Utils",
    "Log",
    "log",
    "Error",
    "FileManager",
    
    # Constants
    "MAXIMUM_DEPTH_PROJECT_ROOT",
    
    # Parsing components (for advanced usage)
    "Tokenizer",
    "Lexer",
    "PypxParser",
    "HTMLGenerator",
    "Token",
    "TokenType",
]
