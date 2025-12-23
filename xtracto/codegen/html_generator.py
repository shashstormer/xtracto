"""
HTML Generator for pypx AST
Converts the AST back to HTML string output using the visitor pattern.
"""
from __future__ import annotations
from typing import List, Any
from xtracto.core.logging import get_logger
from xtracto.parsing.ast_nodes import (
    ASTNode,
    ASTVisitor,
    Document,
    Element,
    Attribute,
    TextNode,
    Variable,
    Import,
    JinjaBlock,
    JinjaComment,
)

ELEMENTS_WITH_CLOSING_TAG = {
    "!DOCTYPE html", "a", "abbr", "acronym", "address", "applet", "article", "aside",
    "audio", "b", "basefont", "bdi", "bdo", "bgsound", "big", "blockquote",
    "body", "bold", "button", "canvas", "caption", "center", "cite", "code",
    "colgroup", "column", "comment", "data", "datalist", "dd", "define", "delete",
    "details", "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "font", "footer", "form", "frame", "frameset", "head", "header",
    "heading", "hgroup", "html", "iframe", "ins", "isindex", "italic", "kbd",
    "keygen", "label", "legend", "list", "main", "mark", "marquee", "menuitem",
    "meter", "nav", "nobreak", "noembed", "noscript", "object", "optgroup",
    "option", "output", "paragraphs", "phrase", "pre", "progress", "q", "rp",
    "rt", "ruby", "s", "samp", "section", "small", "spacer", "span", "strike",
    "strong", "style", "sub", "sup", "summary", "svg", "table", "tbody", "td",
    "template", "tfoot", "th", "thead", "time", "title", "tr", "tt", "underline",
    "var", "video", "xmp",
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "script",
    "textarea", "select", "i", "u", "em", "strong",
}
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class HTMLGenerator(ASTVisitor):
    """
    Generates HTML from a pypx AST.
    Usage:
        generator = HTMLGenerator(document_ast)
        html = generator.generate()
    """

    def __init__(self, ast: Document = None):
        """
        Initialize the HTML generator.
        Args:
            ast: The Document AST to generate HTML from
        """
        self.ast = ast
        self.output: List[str] = []
        self.logger = get_logger("xtracto.codegen")

    def generate(self, ast: Document = None) -> str:
        """
        Generate HTML from the AST.
        Args:
            ast: Optional AST to generate from (uses self.ast if not provided)
        Returns:
            Generated HTML string
        """
        if ast is not None:
            self.ast = ast
        if self.ast is None:
            return ""
        self.output = []
        self.logger.trace("Starting HTML generation")
        self.ast.accept(self)
        result = "".join(self.output)
        self.logger.trace("HTML generation complete", length=len(result))
        return result

    def visit_document(self, node: Document) -> Any:
        """Visit a document node."""
        for child in node.children:
            child.accept(self)
        return None

    def visit_element(self, node: Element) -> Any:
        """Visit an element node."""
        tag_lower = node.tag_name.lower()
        is_void = tag_lower in VOID_ELEMENTS
        is_known_element = tag_lower in ELEMENTS_WITH_CLOSING_TAG or is_void
        has_children = len(node.children) > 0
        has_attributes = len(node.attributes) > 0
        if not is_known_element and not has_children and not has_attributes:
            self.logger.codegen("Generating text (non-element)", content=node.tag_name)
            self.output.append(node.tag_name)
            self.output.append("\n")
            return None
        self.logger.codegen("Generating element", tag=node.tag_name)
        self.output.append(f"<{node.tag_name}")
        for attr in node.attributes:
            attr.accept(self)
        if is_void and not has_children:
            self.output.append(" />")
        elif not has_children and is_known_element:
            self.output.append(f"></{node.tag_name}>")
        elif not has_children:
            self.output.append(" />")
        else:
            self.output.append(">")
            for child in node.children:
                child.accept(self)
            self.output.append(f"</{node.tag_name}>")
        return None

    def visit_attribute(self, node: Attribute) -> Any:
        """Visit an attribute node."""
        self.output.append(f" {node.content}")
        return None

    def visit_text(self, node: TextNode) -> Any:
        """Visit a text node."""
        self.output.append(node.content)
        return None

    def visit_variable(self, node: Variable) -> Any:
        """Visit a variable node."""
        self.output.append(node.to_jinja())
        return None

    def visit_import(self, node: Import) -> Any:
        """Visit an import node - outputs placeholder for later resolution."""
        if node.params:
            self.output.append(f"[[{node.path}||{node.params}]]")
        else:
            self.output.append(f"[[{node.path}]]")
        return None

    def visit_jinja_block(self, node: JinjaBlock) -> Any:
        """Visit a Jinja block node."""
        self.output.append(node.content)
        self.output.append("\n")
        return None

    def visit_jinja_comment(self, node: JinjaComment) -> Any:
        """Visit a Jinja comment node - these are typically omitted."""
        return None
