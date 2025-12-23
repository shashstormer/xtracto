"""
AST Node Definitions for pypx

Defines the Abstract Syntax Tree node types that represent parsed pypx documents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any


class ASTNode(ABC):
    """Base class for all AST nodes."""
    
    line: int
    column: int
    
    @abstractmethod
    def accept(self, visitor: "ASTVisitor") -> Any:
        """Accept a visitor for tree traversal."""
        pass
    
    def children_nodes(self) -> List["ASTNode"]:
        """Return child nodes for traversal."""
        return []


@dataclass
class Document(ASTNode):
    """
    Root node representing an entire pypx document.
    
    Attributes:
        children: Top-level nodes in the document
        filename: Optional source filename
    """
    
    children: List[ASTNode] = field(default_factory=list)
    filename: Optional[str] = None
    line: int = 1
    column: int = 1
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_document(self)
    
    def children_nodes(self) -> List[ASTNode]:
        return self.children


@dataclass
class Element(ASTNode):
    """
    HTML element node.
    
    Attributes:
        tag_name: The HTML tag name (div, span, etc.)
        attributes: List of element attributes
        children: Child nodes (elements, text, etc.)
        is_void: Whether this is a void/self-closing element
    """
    
    tag_name: str
    attributes: List["Attribute"] = field(default_factory=list)
    children: List[ASTNode] = field(default_factory=list)
    is_void: bool = False
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_element(self)
    
    def children_nodes(self) -> List[ASTNode]:
        return self.children
    
    def add_attribute(self, attr: "Attribute"):
        """Add an attribute to this element."""
        self.attributes.append(attr)
    
    def add_child(self, child: ASTNode):
        """Add a child node to this element."""
        self.children.append(child)


@dataclass
class Attribute(ASTNode):
    """
    Element attribute (from ;; ... ;;).
    
    Attributes:
        content: Raw attribute string like 'class="foo"' or 'href="..."'
    """
    
    content: str
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_attribute(self)


@dataclass
class TextNode(ASTNode):
    """
    Plain text content.
    
    Attributes:
        content: The text content
        preserve_whitespace: Whether to preserve whitespace formatting
    """
    
    content: str
    preserve_whitespace: bool = False
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_text(self)


@dataclass
class Variable(ASTNode):
    """
    Jinja2 variable reference ({{ var }} or {{ var=default }}).
    
    Attributes:
        name: Variable name
        default_value: Optional default value if variable is not provided
        raw_content: Original content between {{ and }}
    """
    
    name: str
    default_value: Optional[str] = None
    raw_content: str = ""
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_variable(self)
    
    def to_jinja(self) -> str:
        """Convert to Jinja2 template syntax."""
        if self.default_value is not None:
            return f"{{{{ {self.name} | default('{self.default_value}') }}}}"
        return f"{{{{ {self.name} }}}}"


@dataclass
class Import(ASTNode):
    """
    Component import ([[file.pypx]] or [[file.pypx || params]]).
    
    Attributes:
        path: Path to the component file
        params: Optional parameters to pass to the component
        raw_content: Original content between [[ and ]]
    """
    
    path: str
    params: Optional[str] = None
    raw_content: str = ""
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_import(self)


@dataclass
class JinjaBlock(ASTNode):
    """
    Raw Jinja2 block passthrough ({% ... %}).
    
    This is not parsed further - it's passed through to Jinja2 as-is.
    
    Attributes:
        content: The complete Jinja2 block including {% %}
        block_type: Type of block (if, for, endif, endfor, etc.)
    """
    
    content: str
    block_type: Optional[str] = None
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_jinja_block(self)


@dataclass
class JinjaComment(ASTNode):
    """
    Jinja2 comment ({# ... #}).
    
    Attributes:
        content: The comment content (without delimiters)
    """
    
    content: str
    line: int = 0
    column: int = 0
    
    def accept(self, visitor: "ASTVisitor") -> Any:
        return visitor.visit_jinja_comment(self)


class ASTVisitor(ABC):
    """
    Visitor interface for AST traversal.
    
    Implement this to perform operations on the AST (code generation, 
    optimization, analysis, etc.)
    """
    
    @abstractmethod
    def visit_document(self, node: Document) -> Any:
        pass
    
    @abstractmethod
    def visit_element(self, node: Element) -> Any:
        pass
    
    @abstractmethod
    def visit_attribute(self, node: Attribute) -> Any:
        pass
    
    @abstractmethod
    def visit_text(self, node: TextNode) -> Any:
        pass
    
    @abstractmethod
    def visit_variable(self, node: Variable) -> Any:
        pass
    
    @abstractmethod
    def visit_import(self, node: Import) -> Any:
        pass
    
    @abstractmethod
    def visit_jinja_block(self, node: JinjaBlock) -> Any:
        pass
    
    @abstractmethod
    def visit_jinja_comment(self, node: JinjaComment) -> Any:
        pass


class DefaultASTVisitor(ASTVisitor):
    """
    Default visitor that visits all children.
    
    Subclass this and override specific visit methods as needed.
    """
    
    def visit_document(self, node: Document) -> Any:
        for child in node.children:
            child.accept(self)
        return None
    
    def visit_element(self, node: Element) -> Any:
        for attr in node.attributes:
            attr.accept(self)
        for child in node.children:
            child.accept(self)
        return None
    
    def visit_attribute(self, node: Attribute) -> Any:
        return None
    
    def visit_text(self, node: TextNode) -> Any:
        return None
    
    def visit_variable(self, node: Variable) -> Any:
        return None
    
    def visit_import(self, node: Import) -> Any:
        return None
    
    def visit_jinja_block(self, node: JinjaBlock) -> Any:
        return None
    
    def visit_jinja_comment(self, node: JinjaComment) -> Any:
        return None
