"""
A web framework for integration with pypx
"""
from __future__ import annotations

__author__ = "shashstormer"
__description__ = "A web framework for integration with pypx"

import os
import re
from typing import Dict, Any

from jinja2 import Environment
from pytailwind import Tailwind

MAXIMUM_DEPTH_PROJECT_ROOT = 10


class Utils:
    @staticmethod
    def import_module_by_path(module_path):
        """
        Imports python module from the speficied module path
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("module_name", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def get_project_root():
        current_script = os.getcwd()
        if os.path.exists(os.path.join(current_script, 'xtracto.config.py')):
            return current_script
        Log.critical(Error.ProjectConfig.message, "")
        if Config("").debug:
            Log.debug(Error.ProjectConfig.resolution)
        raise Error.ProjectConfig.error

    @staticmethod
    def get_config_file():
        return os.path.join(Utils.get_project_root(), "xtracto.config.py")

    @staticmethod
    def add_content_at_indent(line: int, indent: int, content: str, file_content: str):
        lines = file_content.split('\n')
        if 1 <= line <= len(lines):
            target_indent = indent * ' '
            content = content.strip("\n")
            content = content.replace("\n", f"\n{target_indent}")
            new_line = f"{target_indent}{content}"
            lines.insert(line - 1, new_line)
            updated_file_content = '\n'.join(lines)
            return updated_file_content
        else:
            if Config().debug:
                Log.error(Error.LineInsertError.InvalidLineNumber.message, line, indent, content, file_content)
                Log.debug(Error.LineInsertError.InvalidLineNumber.resolution)
            raise Error.LineInsertError.InvalidLineNumber.error

    @staticmethod
    def root_path(path):
        return os.path.join(Utils.get_project_root(), path)

    @staticmethod
    def layout_exists():
        return os.path.exists(os.path.join(Config().project_root, "_layout.pypx"))

    @staticmethod
    def page_exists(page):
        return os.path.exists(os.path.join(Config().pages_root, page))


class Parser:
    def __init__(self, path=None, content=None, module=False, layout=False):
        """
        Wrapper for parsing a pypx to a deliverable html file.
        """
        self.config = Config()
        self.raw_type = "path" if path is not None else "content"
        self.raw_origin = path if path is not None else content
        self.module = module
        self.layout = layout
        self.html_content = ""
        self.static_requirements = {}
        if path and not module and not layout and self.config.production:
            build_path = os.path.join(str(self.config.build_dir), os.path.splitext(path)[0] + ".html")
            if os.path.exists(build_path):
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
        else:
            self.content = content
        self.pypx_parser = Pypx(self.content, self.raw_origin)
        self.parse()

    def parse(self):
        self.pypx_parser.parse(self.layout)
        self.pypx_parser.do_imports()
        if not self.module:
            self.static_requirements.update(self.pypx_parser.static_requirements)
        self.template_string = self.pypx_parser.parsed

    def render(self, context: Dict[str, Any] = None):
        if context is None:
            context = {}
        try:
            env = Environment(autoescape=True)
            template = env.from_string(self.template_string)
            self.html_content = template.render(**context)
        except Exception as e:
            Log.error(f"Jinja2 Rendering Error: {e}")
            self.html_content = self.template_string
        if self.config.reparse_tailwind:
            self.load_tailwind()

    def clear_variables(self):
        pass

    def load_tailwind(self):
        _tailwind = Tailwind()
        _generated = _tailwind.generate(self.html_content)
        if _generated and not "{{generated_tailwind}}" in self.html_content:
            Log.warn("Tailwind generated but no \"{{generated_tailwind}}\" placeholder found in template.")
        self.html_content = self.html_content.replace("{{generated_tailwind}}", _generated)


class Config:
    def __init__(self, project_root=None):
        """
        load xtracto.config.py
        """
        if project_root is None:
            config = Utils.import_module_by_path(Utils.get_config_file())
            self.project_root = Utils.get_project_root()
            self.module_root = Utils.root_path(getattr(config, "modules_dir", "xtractocomponents"))
            self.pages_root = Utils.root_path(getattr(config, "pages_dir", "xtractopages"))
        else:
            config = Config
            self.project_root = project_root
            self.module_root = os.getcwd()
            self.pages_root = os.getcwd()
        self.production = getattr(config, 'production', os.getenv("env", "prod").startswith("dev"))
        self.app_start_path = getattr(config, 'app_start_path', "/")
        self.strip_imports = getattr(config, 'strip_imports', True)
        self.debug = getattr(config, 'debug', os.getenv("env", "prod").startswith("dev"))
        self.log_level = "debug" if self.debug else getattr(config, 'log_level', "info")
        self.raise_value_errors_while_importing = getattr(config, 'raise_value_errors_while_importing', True)
        self.build_dir = Utils.root_path(getattr(config, "build_dir", "build"))
        self.reparse_tailwind = getattr(config, 'reparse_tailwind', False)
        del config


class Builder:
    def __init__(self):
        self.config = Config()

    def build(self):
        """
        Builds all pages in pages_dir to build_dir as rendered Jinja2 templates.
        Also runs pytailwind on the templates.
        """
        pages_root = self.config.pages_root
        build_root = self.config.build_dir
        if not os.path.exists(build_root):
            os.makedirs(build_root)
        for root, dirs, files in os.walk(pages_root):
            rel_root = os.path.relpath(root, pages_root)
            target_root = os.path.join(build_root, rel_root)
            if not os.path.exists(target_root):
                os.makedirs(target_root)
            for file in files:
                if file.endswith(".pypx") and not file.startswith("_"):
                    source_path = os.path.join(root, file)
                    rel_path = os.path.relpath(source_path, pages_root)
                    parser = Parser(path=rel_path)
                    tailwind = Tailwind()
                    generated_tailwind = tailwind.generate(parser.template_string)
                    final_content = parser.template_string.replace("{{generated_tailwind}}", generated_tailwind)
                    target_file = os.path.splitext(file)[0] + ".html"
                    target_path = os.path.join(target_root, target_file)
                    with open(target_path, "w") as f:
                        f.write(final_content)
                    log.info(f"Built: {rel_path} -> {os.path.relpath(target_path, build_root)}")


class Log:
    def __init__(self):
        pass

    @staticmethod
    def xtracto_initiated():
        pass

    @staticmethod
    def get_logger(config_path=None):
        import requestez.helpers as ez_helper
        import logging
        if config_path is None:
            config = Config()
        else:
            config = Config(config_path)
        ez_helper.set_log_level(config.log_level)
        logger = ez_helper.get_logger()
        logger.logger = logging.getLogger("xtracto")
        return logger

    @staticmethod
    def critical(message, config=None):
        Log.get_logger(config).log("c", msg=message, color="red")

    @staticmethod
    def error(message, *args):
        Log.get_logger().stack("e", *args, msg=message, color="red")

    @staticmethod
    def warn(message):
        Log.get_logger().log("w", msg=message, color="yellow")

    @staticmethod
    def info(message):
        Log.get_logger().log("i", msg=message, color="CYAN")

    @staticmethod
    def debug(message):
        Log.get_logger().log("d", msg=message, color="reset")


log = Log


class Error:
    class ProjectConfig:
        message = "Project Config file not found (xtracto.config.py)"
        error = FileNotFoundError(message)
        resolution = "RESOLUTION: Create file 'xtracto.config.py' at your project root directory"

    class LineInsertError:
        class InvalidLineNumber:
            message = "Invalid line number. Please provide a valid line number."
            error = ValueError(message)
            resolution = "RESOLUTION: Enter a valid line number or Check Input Content"


class FileManager:
    def __init__(self):
        pass

    @staticmethod
    def get_file_if_valid(path):
        _, file_extension = os.path.splitext(path)
        file_type = file_extension[1:]
        module_root = os.path.abspath(str(Config().module_root))
        full_path = os.path.abspath(os.path.join(module_root, path))
        try:
            if os.path.commonpath([module_root, full_path]) != module_root:
                log.critical(full_path, "PATH TRAVERSAL ATTEMPT")
                return ""
        except ValueError:
            log.critical(full_path, "PATH TRAVERSAL ATTEMPT (Different Drives)")
            return ""
        if not os.path.exists(full_path):
            log.critical(full_path, "NOT FOUND")
            return ""
        if file_type == "pypx":
            try:
                return Parser(path=path, module=True)
            except Exception as e:
                log.error(e, f"Error parsing pypx file: {path}")
                return ""
        try:
            with open(full_path) as f:
                return f.read()
        except Exception as e:
            log.error(e, f"Error reading file: {path}")
            return ""


class Pypx:
    def __init__(self, content=None, fname=None):
        if content is None:
            content = ""
        content = content.expandtabs(4)
        content = content.replace("\t", "    ")
        self.content = content.split("\n")
        self.fname = fname
        self.parsing = self.content.copy()
        self.groups = [
            ["::", "::"],
            ["{{", "}}"],
            [";;", ";;"],
            ["[[", "]]"],
        ]
        self.void_elements = [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]
        self.elements = [
            "!DOCTYPE html", "abbreviation", "acronym", "address", "anchor", "applet", "article", "aside",
            "audio", "basefont", "bdi", "bdo", "bgsound", "big", "blockquote", "body", "bold", "break",
            "button", "caption", "canvas", "center", "cite", "code", "colgroup", "column", "comment", "data",
            "datalist", "dd", "define", "delete", "details", "dialog", "dir", "div", "dl", "dt", "embed", "fieldset",
            "figcaption", "figure", "font", "footer", "form", "frame", "frameset", "head", "header", "heading",
            "hgroup", "html", "iframe", "ins", "isindex", "italic", "kbd", "keygen", "label",
            "legend", "list", "main", "mark", "marquee", "menuitem", "meter", "nav", "nobreak", "noembed",
            "noscript", "object", "optgroup", "option", "output", "paragraphs", "phrase", "pre", "progress",
            "q", "rp", "rt", "ruby", "s", "samp", "section", "small", "spacer", "span", "strike", "strong",
            "style", "sub", "sup", "summary", "svg", "table", "tbody", "td", "template", "tfoot", "th", "thead",
            "time", "title", "tr", "tt", "underline", "var", "video", "xmp"
        ]
        self.parsed = ""
        self.blocks = []
        self.static_requirements = {}
        del content, fname

    def parse(self, layout=False):
        self.make_groups_valid()
        self.parse_comments()
        self.parse_blocks()
        self.load_blocks()
        self.normalize()
        self.convert_variables_to_jinja()
        if not layout:
            self.use_layout()

    def convert_variables_to_jinja(self):
        def replace_default(match):
            var = match.group(1).strip()
            default = match.group(2).strip()
            return f"{{{{ {var} | default('{default}') }}}}"

        self.parsed = re.sub(r'\{\{\s*([^=}]+?)\s*=\s*(.*?)\s*\}\}', replace_default, self.parsed)

    def use_layout(self):
        _layout_file = os.path.join(str(Config().pages_root), "_layout.pypx")
        if not os.path.exists(_layout_file):
            return
        _self = Parser(path="_layout.pypx", layout=True)
        layout_tpl = _self.template_string
        if "{{children}}" in layout_tpl:
            self.parsed = layout_tpl.replace("{{children}}", self.parsed)
        elif "{children}" in layout_tpl:
            self.parsed = layout_tpl.replace("{children}", self.parsed)
        else:
            log.warn("Layout file does not contain {{children}} placeholder")
        self.static_requirements.update(_self.static_requirements)

    def make_groups_valid(self):
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
                        raise SyntaxError(f"Unbalanced '{value1}' starting at line {num + 1} in file {self.fname}")
                        # log.error(f"Syntax Error: Unbalanced '{value1}' starting at line {num + 1}")
                        # self.parsed = []
                        # return
                    self.parsing[num] += "#&N#" + self.parsing[num + 1]
                    self.parsing.pop(num + 1)
                    line = self.parsing[num]
            num += 1

    def parse_comments(self):
        self.parsing = [
            i
            for i in
            re.sub("(::.*?::)", "", "\n".join(self.parsing)).split("\n")
            if i
        ]

    def normalize(self, content=None):
        ori_content = content
        if content is None:
            content = self.parsed
        content = content.replace("#&N#", "\n")
        if ori_content is None:
            self.parsed = content
        return content

    def parse_blocks(self):
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

    def load_blocks(self, blocks=None):
        if blocks is None:
            blocks = self.blocks.copy()
        loaded_block = ""
        for block in blocks:
            if block[2]:
                loaded_block += "<" + block[1]
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

    def do_imports(self, content=None):
        ori_cont = content
        if content is None:
            content = self.parsed
        regex = re.compile(r"\[\[\s*([a-zA-Z0-9. _/\\-]+)\s*(?:\|\|\s*(.*?))?\s*\]\]")

        def replace_import(match):
            filename = match.group(1).strip()
            params_str = match.group(2)
            cont = FileManager.get_file_if_valid(filename)
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
