"""
Builder for xtracto
Handles production builds - compiling all pages to HTML.
"""
from __future__ import annotations
import os
from typing import TYPE_CHECKING
from xtracto.core.logging import get_logger
from xtracto.rendering.tailwind import TailwindIntegration

if TYPE_CHECKING:
    from xtracto.core.config import Config


class Builder:
    """
    Production builder for xtracto.
    Compiles all .pypx pages to HTML files with Tailwind CSS.
    Usage:
        builder = Builder()
        builder.build()
    """

    def __init__(self, config: "Config" = None):
        """
        Initialize the builder.
        Args:
            config: Optional Config instance
        """
        self._config = config
        self.logger = get_logger("xtracto.builder")

    @property
    def config(self) -> "Config":
        """Lazy-load config if not provided."""
        if self._config is None:
            from xtracto.core.config import Config
            self._config = Config()
        return self._config

    def build(self):
        """
        Build all pages in pages_dir to build_dir.
        Compiles .pypx files to .html with Tailwind CSS generated.
        Skips files starting with underscore (layouts, partials).
        """
        pages_root = self.config.pages_root
        build_root = self.config.build_dir
        self.logger.build("Starting build", pages_root=pages_root, build_root=build_root)
        if not os.path.exists(build_root):
            os.makedirs(build_root)
        tailwind = TailwindIntegration()
        built_count = 0
        for root, dirs, files in os.walk(pages_root):
            rel_root = os.path.relpath(root, pages_root)
            target_root = os.path.join(build_root, rel_root)
            if not os.path.exists(target_root):
                os.makedirs(target_root)
            for file in files:
                if not file.endswith(".pypx") or file.startswith("_"):
                    continue
                source_path = os.path.join(root, file)
                rel_path = os.path.relpath(source_path, pages_root)
                try:
                    from xtracto import Parser
                    parser = Parser(path=rel_path)
                    generated_tailwind = tailwind.generate(parser.template_string)
                    final_content = parser.template_string.replace(
                        "{{generated_tailwind}}",
                        generated_tailwind
                    )
                    target_file = os.path.splitext(file)[0] + ".html"
                    target_path = os.path.join(target_root, target_file)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(final_content)
                    built_count += 1
                    self.logger.info(
                        f"Built: {rel_path} -> {os.path.relpath(target_path, build_root)}"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to build {rel_path}: {e}")
        self.logger.build("Build complete", files_built=built_count)
