"""
Caching module for xtracto.
Provides template caching and Jinja2 bytecode caching for production mode.
"""
from __future__ import annotations
import os
import hashlib
import pickle
from typing import Dict, Any, Optional, TYPE_CHECKING
from functools import lru_cache
from jinja2 import Environment, FileSystemBytecodeCache
from xtracto.core.logging import get_logger

if TYPE_CHECKING:
    from xtracto.core.config import Config


class TemplateCache:
    """
    Cache for parsed pypx templates.
    In production mode, caches:
    - Parsed template strings (HTML output from pypx parsing)
    - Jinja2 compiled templates with bytecode caching
    Usage:
        cache = TemplateCache(config)
        # Check if cached
        cached = cache.get_template("index.pypx", content_hash)
        if cached:
            return cached
        # Parse and cache
        parsed = parse_pypx(content)
        cache.set_template("index.pypx", content_hash, parsed)
    """
    _instance: Optional["TemplateCache"] = None
    _initialized: bool = False

    def __new__(cls, config: "Config" = None):
        """Singleton pattern for global cache."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: "Config" = None):
        """
        Initialize the template cache.
        Args:
            config: Optional Config instance
        """
        if self._initialized:
            return
        self._initialized = True
        self._config = config
        self.logger = get_logger("xtracto.cache")
        self._template_cache: Dict[str, tuple] = {}
        self._jinja_env: Optional[Environment] = None
        self._bytecode_cache_dir: Optional[str] = None
        self.logger.debug("Template cache initialized")

    @property
    def config(self) -> "Config":
        """Lazy-load config if not provided."""
        if self._config is None:
            from xtracto.core.config import Config
            self._config = Config()
        return self._config

    @property
    def enabled(self) -> bool:
        """Check if caching is enabled (production mode)."""
        return self.config.production

    @property
    def bytecode_cache_dir(self) -> str:
        """Get the bytecode cache directory."""
        if self._bytecode_cache_dir is None:
            self._bytecode_cache_dir = os.path.join(
                self.config.build_dir, ".jinja_cache"
            )
            os.makedirs(self._bytecode_cache_dir, exist_ok=True)
        return self._bytecode_cache_dir

    @property
    def jinja_env(self) -> Environment:
        """
        Get Jinja2 environment with bytecode caching.
        In production mode, uses FileSystemBytecodeCache for
        compiled template bytecode persistence.
        """
        if self._jinja_env is None:
            if self.enabled:
                bytecode_cache = FileSystemBytecodeCache(
                    directory=self.bytecode_cache_dir,
                    pattern="__jinja2_%s.cache"
                )
                self._jinja_env = Environment(
                    autoescape=True,
                    bytecode_cache=bytecode_cache,
                    auto_reload=False,
                )
                self.logger.debug(
                    f"Jinja2 bytecode caching enabled: {self.bytecode_cache_dir}"
                )
            else:
                self._jinja_env = Environment(autoescape=True)
        return self._jinja_env

    @staticmethod
    def content_hash(content: str) -> str:
        """Generate a hash for content to detect changes."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get_template(self, path: str, content_hash: str) -> Optional[str]:
        """
        Get cached template if available and hash matches.
        Args:
            path: Template file path
            content_hash: Hash of current content
        Returns:
            Cached parsed template string, or None if not cached/stale
        """
        if not self.enabled:
            return None
        cached = self._template_cache.get(path)
        if cached is None:
            return None
        cached_hash, cached_template = cached
        if cached_hash != content_hash:
            self.logger.trace(f"Cache miss (hash mismatch): {path}")
            return None
        self.logger.trace(f"Cache hit: {path}")
        return cached_template

    def set_template(self, path: str, content_hash: str, parsed: str):
        """
        Cache a parsed template.
        Args:
            path: Template file path
            content_hash: Hash of the content
            parsed: Parsed template string
        """
        if not self.enabled:
            return
        self._template_cache[path] = (content_hash, parsed)
        self.logger.trace(f"Cached template: {path}")

    def render_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with caching.
        In production mode, the compiled template is cached as bytecode.
        Args:
            template_string: Jinja2 template string
            context: Template context variables
        Returns:
            Rendered HTML string
        """
        template = self.jinja_env.from_string(template_string)
        return template.render(**context)

    def clear(self):
        """Clear all caches."""
        self._template_cache.clear()
        self._tailwind_cache = {}
        self._jinja_env = None
        self.logger.debug("Cache cleared")

    def get_tailwind(self, content_hash: str) -> Optional[str]:
        """
        Get cached Tailwind CSS if available.
        Args:
            content_hash: Hash of content used for Tailwind generation
        Returns:
            Cached CSS string, or None if not cached
        """
        if not self.enabled:
            return None
        if not hasattr(self, '_tailwind_cache'):
            self._tailwind_cache = {}
        cached = self._tailwind_cache.get(content_hash)
        if cached:
            self.logger.trace(f"Tailwind cache hit: {content_hash[:8]}...")
        return cached

    def set_tailwind(self, content_hash: str, css: str):
        """
        Cache generated Tailwind CSS.
        Args:
            content_hash: Hash of content used for generation
            css: Generated CSS string
        """
        if not self.enabled:
            return
        if not hasattr(self, '_tailwind_cache'):
            self._tailwind_cache = {}
        self._tailwind_cache[content_hash] = css
        self.logger.trace(f"Cached Tailwind CSS: {content_hash[:8]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        tailwind_count = len(getattr(self, '_tailwind_cache', {}))
        return {
            "enabled": self.enabled,
            "template_count": len(self._template_cache),
            "tailwind_count": tailwind_count,
            "bytecode_cache_dir": self._bytecode_cache_dir,
        }


_cache: Optional[TemplateCache] = None


def get_cache(config: "Config" = None) -> TemplateCache:
    """
    Get the global template cache instance.
    Args:
        config: Optional Config instance
    Returns:
        TemplateCache singleton instance
    """
    global _cache
    if _cache is None:
        _cache = TemplateCache(config)
    return _cache


def clear_cache():
    """Clear all caches."""
    global _cache
    if _cache is not None:
        _cache.clear()


@lru_cache(maxsize=128)
def hash_file(path: str, mtime: float) -> str:
    """
    Get content hash for a file.
    Uses mtime as part of cache key to invalidate on file changes.
    Args:
        path: Absolute path to file
        mtime: File modification time
    Returns:
        MD5 hash of file content
    """
    with open(path, 'r', encoding='utf-8') as f:
        return hashlib.md5(f.read().encode('utf-8')).hexdigest()
