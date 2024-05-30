"""
A web framework for integration with pypx
"""
__version__ = "0.0.6"
__author__ = "shashstormer"
__description__ = "A web framework for integration with pypx"

import os
import re
from fastapi import FastAPI, HTTPException, status, Response, Request
from fastapi.responses import FileResponse
from pytailwind import Tailwind

MAXIMUM_DEPTH_PROJECT_ROOT = 100

validated_files = {}


class Utils:
    @staticmethod
    def import_module_by_path(module_path):
        """
        Imports python module from the speficied module path


        Parameters:
        - module_path: path of python module to import
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("module_name", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def get_project_root():
        current_script = os.getcwd()
        ic = 0
        while current_script:
            if os.path.exists(os.path.join(current_script, 'xtracto.config.py')):
                break
            ic += 1
            current_script = os.path.dirname(current_script)
            if ic > MAXIMUM_DEPTH_PROJECT_ROOT:
                Log.critical(Error.ProjectConfig.message, "")
                if Config("").debug:
                    Log.debug(Error.ProjectConfig.resolution)
                current_script = False
        else:
            raise Error.ProjectConfig.error
        return current_script

    @staticmethod
    def get_config_file():
        return os.path.join(Utils.get_project_root(), "xtracto.config.py")

    @staticmethod
    def add_content_at_indent(line: int, indent: int, content: str, file_content: str):
        """
        Adds content at a specific indentation level in the given file content.

        Parameters:
        - line: The line number where the content will be added.
        - indent: The desired indentation level.
        - content: The content to be added.
        - file_content: The existing content of the file.

        Returns:
        - updated_file_content: The file content after adding the new content.
        """
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
    def get_variable_value_from_nearest_frame(_variable_name, _default_value=False, _raise_error=True,
                                              _use_current=True, _skip_after_current=2):
        """
            :param _variable_name: The Name of the variable whose value needs to be retrived.
            :param _default_value: This default value is used only in the case that there is no default value mentioned in the placeholder.
            :param _raise_error: Raise error if the variable is not found in any scope.
            :param _use_current: Look for variable in the calling scope.
            :param _skip_after_current: Number of frames to skip without looking for the variable value (current frame controlled by _use_current).
            :return:
            """
        import inspect as _inspect
        _frame = _inspect.currentframe()
        _frame = _frame.f_back
        if not _use_current:
            while _skip_after_current > 0:
                if hasattr(_frame, 'f_back'):
                    _frame = _frame.f_back
                else:
                    if Config().raise_value_errors_while_importing and _raise_error:
                        raise NameError(f"variable \"{_variable_name}\" has not been defined")
                    _value = _default_value
                _skip_after_current -= 1
        while _frame:
            if _variable_name in _frame.f_locals:
                _local_value = _frame.f_locals[_variable_name]
                _value = _local_value
                break
            if _skip_after_current <= 0:
                _frame = _frame.f_back
            while _skip_after_current > 0:
                _frame = _frame.f_back
                _skip_after_current -= 1
        else:
            if Config().raise_value_errors_while_importing and _raise_error:
                raise NameError(f"variable \"{_variable_name}\" has not been defined")
            _value = _default_value
        return _value

    @staticmethod
    def is_node_module_installed(module_name):
        """
            Checks if spefied node module is installed.

            Returns:
            - bool: True if module is installed, False otherwise.
            """
        import subprocess
        try:
            subprocess.run([module_name, '--version'], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def get_user_home():
        """
        Gets the user's home directory.

        Returns:
        - str: The absolute path to the user's home directory.
        """
        home_directory = os.path.expanduser("~")
        return home_directory

    @staticmethod
    def layout_exists():
        """
        This method returns if the layout file exists.
        If it exists it is used and the page is rendered in that layout.
        """
        return os.path.exists(os.path.join(Config().project_root, "_layout.pypx"))


class Parser:
    def __init__(self, path=None, content=None, module=False, layout=False, _additional_contexts=None):
        """
        Wrapper for parsing a pypx to a deliverable html file.
        """
        self.raw_type = "path" if path is not None else "content"
        self.raw_origin = path if path is not None else content
        if path:
            if module:
                _fpath = os.path.join(str(Config().module_root), path)
                layout = True
            else:
                _fpath = os.path.join(str(Config().pages_root), path)
            with open(_fpath) as f:
                self.content = f.read()
        else:
            self.content = content
        self.raw_content = self.content
        self.html_content = ""
        self.layout = layout
        self.static_requirements = {}
        self.module = module
        if _additional_contexts is None:
            _additional_contexts = []
        self.pypx_parser = Pypx(self.content, self.raw_origin, _additional_contexts=_additional_contexts)
        _additional_contexts.extend(self.pypx_parser.contexts)
        _additional_contexts = list(set(_additional_contexts))
        self.contexts = _additional_contexts
        del path, content, module, layout
        if self.content:
            if self.layout:
                _ = [self.pypx_parser.parsed]
                _.extend(self.contexts)
                self.pypx_parser.load_variables(_addnl_var_contexts=_)
            self.parse()

    def parse(self):
        self.pypx_parser.parse(self.layout)
        if not self.module:
            self.static_requirements.update(self.pypx_parser.parse_static_import())
            self.static_requirements.update(self.pypx_parser.static_requirements)
        self.contexts.extend(self.pypx_parser.contexts)
        self.contexts = list(set(self.contexts))
        self.html_content = self.pypx_parser.normalize(self.pypx_parser.parsed)
        self.contexts.extend(self.pypx_parser.contexts)
        self.contexts = list(set(self.contexts))

    def render(self):
        _loaders_match = re.compile("\+\$(.*?)\$\+")
        _load_list = []
        self.contexts.append(self.pypx_parser.parsed)
        self.contexts.extend(self.contexts)
        for _load in _loaders_match.findall("\n".join(self.contexts)):
            _load_list.append(_load.split("=", 1))
        for var, val in _load_list:
            locals()[var] = val
        self.pypx_parser.load_variables(_addnl_var_contexts=self.contexts)
        self.contexts.extend(self.pypx_parser.contexts)
        self.contexts = list(set(self.contexts))
        self.pypx_parser.do_imports()
        self.contexts.extend(self.pypx_parser.contexts)
        self.contexts = list(set(self.contexts))
        self.pypx_parser.load_variables(_addnl_var_contexts=self.contexts)
        self.contexts.extend(self.pypx_parser.contexts)
        self.contexts = list(set(self.contexts))
        self.html_content = self.pypx_parser.normalize(self.pypx_parser.parsed)

    def clear_variables(self):
        _loaders_match = re.compile("(\+\$.*?\$\+)")
        _matches = _loaders_match.findall(self.html_content)
        for _match in _matches:
            self.html_content = self.html_content.replace(_match, '')
    def load_tailwind(self):
        self.contexts.append(self.html_content)
        self.pypx_parser.load_variables(_addnl_var_contexts=self.contexts, _parse_tailwind=True)
        self.html_content = self.pypx_parser.normalize(self.pypx_parser.parsed)

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
        self.strip_imports = getattr(config, 'strip_imports', True)
        self.debug = getattr(config, 'debug', os.getenv("env", "prod").startswith("dev"))
        self.log_level = "debug" if self.debug else getattr(config, 'log_level', "info")
        self.raise_value_errors_while_importing = getattr(config, 'raise_value_errors_while_importing', True)
        del config


class Log:
    def __init__(self):
        """
        Formatted Messages for Warning, Logging, Errors etc
        """
        pass

    @staticmethod
    def xtracto_initiated():
        pass

    @staticmethod
    def get_logger(config_path=None):
        import requestez.helpers as ez_helper
        if config_path is None:
            config = Config()
        else:
            config = Config(config_path)
        ez_helper.set_log_level(config.log_level)
        logger = ez_helper.get_logger()
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
    """
    Base class for all errors
    """

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
        """
        Manages Files and Controls access,
        Manages api request origins,
        Manages asset delivery allowance.
        """
        pass

    @staticmethod
    def get_file_if_valid(path):
        path = os.path.join(str(Config().module_root), path)
        valid = FileManager.Valid(path).valid()
        if valid[0]:
            if valid[1]:
                return valid[1]
            if os.path.exists(path):
                with open(path) as f:
                    return f.read()
            else:
                log.critical(path, "NOT FOUND")
                return ""
        else:
            log.critical(path + " not used")
            log.debug(valid[1])
            return ""

    @staticmethod
    def get_file_type(path):
        """
            Returns the file type (extension) of the given file path.

            Args:
            - file_path (str): The path of the file.

            Returns:
            - str: The file type (extension).
            """
        _, file_extension = os.path.splitext(path)
        return file_extension[1:]

    @staticmethod
    def get_delivery_type(path):
        pass

    class Valid:
        def __init__(self, path):
            """
            Needs to be initialized for auto-detection. You may use specific validators without initializing this class.
            You must not use either this class or its methods in production.
            Only the bundled files are to be used in production.
            You must bundle them before using in production.
            Initialize the build method to create a production build.
            """
            self.path = path
            self.file_type = FileManager.get_file_type(path)
            self.invalid_types = ["__init__", "valid", "error"]

        def valid(self) -> list[[bool, str]]:
            """
            Detects the file content type and Checks if it is valid
            """
            if self.file_type in self.invalid_types:
                raise ValueError("invalid file type")
            if Config().production:
                if self.file_type != "pypx":
                    return [True, ""]
            func = getattr(self, self.file_type, self.unknown)
            return func(self.path)

        def error(self):
            if self.file_type in self.invalid_types:
                raise ValueError("invalid file type")
            func = getattr(self, self.file_type, self.unknown)
            return func(self.path)[1]

        @staticmethod
        def js(path):
            """
                Validates a JavaScript file using ESLint.

                Args:
                - file_path (str): The path of the JavaScript file.

                Returns:
                - str: Validation result.
                """
            import subprocess
            try:
                eslint = Utils.get_user_home() + "\\node_modules\\eslint\\bin\\eslint.js"
                result = subprocess.run(["node", eslint, os.path.join(str(Config().module_root), path)],
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return [True, ""]
                else:
                    log.critical(f"Validation failed. Errors found:\n{result.stdout}")
                    return [False, result.stdout]
            except subprocess.CalledProcessError as e:
                log.critical(f"Error during validation: {e}")
                return [False, e]

        @staticmethod
        def sass(path):
            """
            Validates a SASS file using Stylelint.

            Args:
            - file_path (str): The path of the SASS/SCSS/CSS file.

            Returns:
            - str: Validation result.
            """
            import subprocess
            try:
                stylelint = Utils.get_user_home() + "\\node_modules\\stylelint\\bin\\stylelint.mjs"
                config = f"{Utils.get_user_home()}\\node_modules\\stylelint-config-recommended-scss\\index.js"
                result = subprocess.run(
                    ["node", stylelint, os.path.join(str(Config().module_root), path), "-c", config],
                    capture_output=True,
                    text=True)
                if result.returncode == 0:
                    return [True, ""]
                else:
                    log.critical(f"Validation failed. Errors found:\n{result.stderr}")
                    return [False, result.stderr]
            except subprocess.CalledProcessError as e:
                log.critical(f"Error during validation: {e}")
                return [False, e]

        @staticmethod
        def scss(path):
            return FileManager.Valid.sass(path)

        @staticmethod
        def css(path):
            return FileManager.Valid.sass(path)

        @staticmethod
        def unknown(path):
            log.info(f"Unknown file type: {path}")
            return [True, ""]

        @staticmethod
        def pypx(path):
            _contexts = []
            nearest_self = Utils.get_variable_value_from_nearest_frame('self', _default_value="", _raise_error=False, _skip_after_current=0)
            if nearest_self:
                if hasattr(nearest_self, 'pypx_parser'):
                    _contexts.append(nearest_self.pypx_parser.parsed)
                if hasattr(nearest_self, 'parsed'):
                    _contexts.append(nearest_self.parsed)
            try:
                _parser = Parser(path=path, module=True, _additional_contexts=_contexts)
                _parser.parse()
                return [True, _parser]
            except Exception as e:
                return [False, e]

        @staticmethod
        def html(path):
            try:
                f = open(path)
                f.close()
                return [True, ""]
            except Exception as e:
                Log.debug(e)
                return [False, e]


class Pypx:
    def __init__(self, content=None, fname=None, _additional_contexts=None):
        """
        Parses pypx
        """
        if content is None:
            content = ""
        if _additional_contexts is None:
            _additional_contexts = []
        content = content.replace("\t", " " * 4)
        self.content = content.split("\n")
        self.contexts = _additional_contexts
        self.fname = fname
        self.parsing = self.content.copy()
        self.groups = [
            ["::", "::"],  # Removed comment
            ["?:", "?:"],  # File to be included as static asset
            ["{{", "}}"],  # Variable Field
            [";;", ";;"],  # HTML Attribute
            ["[[", "]]"],  # Import Files and embed them into the generated html
            ["(-(", ")-)"],  # Markdown Content
            ["{[", "]}"],  # Bundling groups
            ["+-", "-+"],  # Set Python variable values in pypx
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
        """
        imports files, parses other stuff, does not replace variables (this is because it is required to create build files)
        """
        self.make_groups_valid()
        self.generate_bundle()
        self.parse_comments()
        self.parse_blocks()
        self.load_blocks()
        self.normalize()
        if not layout:
            self.use_layout()

    def use_layout(self):
        _layout_file = os.path.join(str(Config().pages_root), "_layout.pypx")
        if not os.path.exists(_layout_file):
            log.warn("NO LAYOUT FILE")
            return
        children = self.parsed
        head = re.compile("<head>(.*)</head>").findall(self.parsed)
        head = head[0] if head else ""
        children = children.replace(f"<head>{head}</head>", "")
        if not children:
            log.warn("no children")
        _contexts = [self.parsed]
        _contexts.extend(self.contexts)
        _self = Parser(path="_layout.pypx", layout=True, _additional_contexts=_contexts)
        _self.render()
        self.static_requirements.update(_self.static_requirements)
        if self.parsed not in _self.html_content:
            log.critical("please put {{children}} in the layout file where the page content must appear")
        self.parsed = _self.html_content

    def make_groups_valid(self):
        num = 0
        while num < len(self.parsing):
            line = self.parsing[num]
            for value1, value2 in self.groups:
                while ((
                               (line.count(value1) != line.count(value2)) and (value1 != value2)
                       )
                       or (
                               (line.count(value1) % 2 != 0) and (value1 == value2)
                       )):
                    try:
                        self.parsing[num] += "#&N#" + self.parsing[num + 1]
                        self.parsing.pop(num + 1)
                        line = self.parsing[num]
                    except IndexError:
                        # log.error("Syntax error in file being parsed", "FILE CONTENT:\n" + "\n".join(self.parsing))
                        self.parsed = []
                        return
            num += 1

    def parse_comments(self):
        self.parsing = [
            i
            for i in
            re.sub("(::.*?::)", "", "\n".join(self.parsing)).split("\n")
            if i
        ]

    def parse_static_import(self):
        static_regex = re.compile("\?:(.*?)\?:")
        found = static_regex.findall(self.parsed)
        static_requirements = {}
        for i in found:
            sanitized_i = i.replace("./", "")
            static_requirements[sanitized_i] = i
            self.parsed = self.parsed.replace("?:" + i + "?:", f"/__static/{sanitized_i}")
        self.static_requirements.update(static_requirements)
        return static_requirements

    def normalize(self, content=None):
        ori_content = content
        if content is None:
            content = self.parsed
        _loaders_match = re.compile("\+\$(.*?)\$\+")
        content = content.replace("#&N#", "\n")
        if ori_content is None:
            self.parsed = content
        return content

    def parse_blocks(self):
        stack = []  # [[indent, element, children...]...]
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
        orignal_blocks = [i for i in blocks.copy()]
        for block in blocks:
            _block_orignal = orignal_blocks[orignal_blocks.index(block)].copy()
            if block[2]:
                loaded_block += "<" + block[1]
                for child in block[2].copy():
                    # THIS SECTION IS FOR WARNING WHEN ELEMENT DOES NOT HAVE CHILDREN
                    if block[1].lower() in self.elements and len(block[2]) == 1 and block[2][0][1].startswith(";;"):
                        pred_line = 0
                        for num, line in enumerate(self.content):
                            if line.lstrip(" ").lower() == block[1].lower():
                                forward = 1
                                while not line.lstrip(" "):
                                    forward += 1
                                    if num + forward > len(self.content):
                                        pred_line = num + forward
                                        break
                                if pred_line == 0:
                                    if self.content[num + forward].lstrip(" ").lower().startswith(
                                            _block_orignal[2][0][1].lower()):
                                        pred_line = num + forward
                        log.warn(f"\n{self.fname}:{pred_line} -> element \"" + block[
                            1] + "\" must have children elements/content this has been considered as an element as it has attributes but it is recomended that you add content")
                        # SECTION FOR WARNING WHEN ELEMENT DOES NOT HAVE CHILDREN ENDS HERE
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

                    # THIS SECTION IS FOR WARNING WHEN VOID ELEMENT HAS CHILDREN
                    if block[1].lower() in self.void_elements:
                        pred_line = 0
                        for num, line in enumerate(self.content):
                            if line.lstrip(" ").lower() == block[1].lower():
                                forward = 1
                                while self.content[num + forward].lstrip(" ").startswith(";;"):
                                    forward += 1
                                    if num + forward > len(self.content):
                                        pred_line = num + forward - 1
                                        break
                                if pred_line == 0:
                                    if self.content[num + forward].lstrip(" ").lower().startswith(
                                            block[2][0][1].lower()):
                                        pred_line = num + forward
                                pred_line += 1
                        log.warn(f"\n{self.fname}:{pred_line} -> element \"" + block[
                            1] + "\" cannot have children elements/content")
                    # SECTION FOR WARNING WHEN VOID ELEMENT HAS CHILDREN ENDS HERE

                    loaded_block += self.load_blocks(block[2])
                loaded_block += f"</{block[1]}>"
            elif not block[2]:
                # THIS SECTION IS FOR WARNING WHEN ELEMENT DOES NOT HAVE CHILDREN
                if block[1].lower() in self.elements:
                    pred_line = 0
                    for num, line in enumerate(self.content):
                        if line.lstrip(" ").lower() == block[1].lower():
                            forward = 1
                            while self.content[num + forward].lstrip(" ").startswith(";;") or not line.lstrip(" "):
                                forward += 1
                                if num + forward > len(self.content):
                                    pred_line = num + forward
                                    break
                            if pred_line == 0:
                                nextx_indent = len(self.content[num + forward]) - len(
                                    self.content[num + forward].lstrip(" "))
                                curendtx_indent = len(self.content[num]) - len(self.content[num].lstrip(" "))
                                if nextx_indent <= curendtx_indent:
                                    pred_line = num + forward
                    log.warn(f"\n{self.fname}:{pred_line} -> element \"" + block[
                        1] + "\" must have children elements/content as this does not have any children it will be considered as plain text")
                # SECTION FOR WARNING WHEN ELEMENT DOES NOT HAVE CHILDREN ENDS HERE
                loaded_block += block[1]
                loaded_block += "\n"
        if blocks == self.blocks:
            self.parsed = loaded_block
        return loaded_block

    def load_variables(self, _content=None, _load_list: list or None = None, _addnl_var_contexts: list or None = None, _parse_tailwind: bool = False):
        _original_content = _content
        if _content is None:
            _content = self.parsed
        if _load_list is None:
            _load_list = []
        _loaders_match = re.compile("\+\$(.*?)\$\+")
        if _addnl_var_contexts is None:
            _addnl_var_contexts = self.contexts
        else:
            self.contexts = list(set(self.contexts))
            _addnl_var_contexts.extend(self.contexts)
        _addnl_var_contexts.append(_content)
        _addnl_var_contexts = list(set(_addnl_var_contexts))
        _all_contexts = "\n".join(_addnl_var_contexts)
        for _load in _loaders_match.findall(_all_contexts):
            _load_list.append(_load.split("=", 1))
        for var, val in _load_list:
            locals()[var] = val
        if _load_list:
            del var, val
        _vars_reg = re.compile(r'\{\{(.*?)}}')
        _vars = _vars_reg.findall(_content)
        for _var in _vars:
            _ori_var = "{{" + _var + "}}"
            _var = _var.strip(" ")
            _var = _var.split("=", 1)
            if len(_var) == 2:
                _default = _var[1]
                _raise_error = False
            else:
                _default = False
                _raise_error = True
            _var = _var[0]
            if _var == "tailwind_css_content":
                if not _parse_tailwind:
                    continue
                if "children" in _vars:
                    _all_contexts += Utils.get_variable_value_from_nearest_frame(_variable_name="children", _default_value="",
                                                                     _raise_error=False)
                _tailwind = Tailwind()
                _value = _tailwind.generate(_all_contexts)
            else:
                _value = Utils.get_variable_value_from_nearest_frame(_variable_name=_var, _default_value=_default,
                                                                     _raise_error=_raise_error)
            _content = _content.replace(_ori_var, _value)
        if _original_content is None:
            self.parsed = _content
        return _content

    def do_imports(self, content=None):
        ori_cont = content
        if content is None:
            content = self.parsed
        _contexts = [content]
        _contexts.extend(self.contexts)
        fixed = Pypx(content=content, _additional_contexts=_contexts)
        fixed.make_groups_valid()
        fixed = "\n".join(fixed.parsing)
        file_groups = re.compile("(\[\[.*?]])")
        files = re.compile(r"\[\[([a-zA-Z0-9. /\\]+)(?:.*?)?]]")
        parameters = re.compile("\[\[[a-zA-Z0-9.]+\|\|(.*?)\|\|.*?")
        for group in file_groups.findall(fixed):
            file = files.findall(group)
            file = file[0]
            parms = parameters.findall(group)
            final_parms = []
            while parms:
                param = parms.pop()
                if len(param.split("||")) > 1:
                    final_parms.extend(param.split("||"))
                    continue
                final_parms.append(param)
            parms = [i.replace("#|#", "|") for i in final_parms]
            for num, param in enumerate(parms.copy()):
                parms[num] = param.strip("#&N#").strip(" ").strip("#&N#").strip(" ")
            parms = [i.split("=") for i in parms]  # [[key, value]...]
            cont = FileManager.get_file_if_valid(file)
            if isinstance(cont, Parser):
                self.contexts.extend(cont.contexts)
                self.static_requirements.update(cont.static_requirements)
                cont = cont.html_content
            self.contexts.append(cont)
            self.contexts.extend([content, fixed])
            cont = self.load_variables(_content=cont, _load_list=parms, _addnl_var_contexts=self.contexts)
            fixed = fixed.replace(group, cont)
            self.contexts.append(fixed)
            self.contexts.append(cont)
        if ori_cont is None:
            self.parsed = fixed
        return fixed

    def generate_bundle(self, content="", path_name=""):
        import datetime
        start = datetime.datetime.now()
        oric = content if content else None
        if not content:
            content = "\n".join(self.parsing)
        if not path_name:
            path_name = self.fname
            if not path_name:
                log.critical("You cannot use bundles while generating from string")
                log.debug("PATH NAME IS: \n" + path_name)
                return
        path_name = path_name.replace("/", "\\")
        if path_name.count(".") > 1:
            path_name = ".".join(path_name.split(".")[:-1])
        if path_name.startswith(".\\"):
            pass
        elif path_name.startswith("\\"):
            path_name = "." + path_name
        else:
            path_name = ".\\" + path_name
        fixed = Pypx(content=content, _additional_contexts=self.contexts)
        fixed.make_groups_valid()
        fixed = "\n".join(fixed.parsing)
        file_groups = re.compile("(\[\{.*?}])")
        files = re.compile(r"\[\{([a-zA-Z0-9. /\\]+)(?:.*?)?}]")
        parameters = re.compile("\[\{[a-zA-Z0-9.]+\|\|(.*?)\|\|.*?")
        bundles = {}
        for group in file_groups.findall(fixed):
            file = files.findall(group)
            file = file[0]
            bgroup = file.split(".")[-1]
            if bgroup in bundles:
                bundles[bgroup]["files"].append(group)
                bundles[bgroup]["tohash"] += file + str(os.path.getmtime(os.path.join(str(Config().module_root), file)))
            else:
                try:
                    mtime = str(os.path.getmtime(os.path.join(str(Config().module_root), file)))
                except FileNotFoundError:
                    try:
                        mtime = str(os.path.getmtime(file))
                    except FileNotFoundError:
                        mtime = ""
                bundles[bgroup] = {"files": [group], "content": "",
                                   "tohash": file + mtime,
                                   "hash": ""}

        for bgroup in bundles:
            h = 2166136261
            for byte in bundles[bgroup]["tohash"].encode():
                h = (h ^ byte) * 16777619
            somehash = format(h & 0xFFFFFFFFFFFFFFFF, 'x')[-8:]
            bundles[bgroup]["hash"] = somehash

            # USE EXISTING BUNDLE IF THE FILES ARE UNMODIFIED
            if os.path.exists(
                    os.path.join(str(Config().module_root), path_name + "." + bundles[bgroup]["hash"] + "." + bgroup)):
                continue

            # REMOVE EXISTING BUNDLES WITH SAME NAME
            file_dir = os.path.dirname(
                os.path.join(str(Config().module_root), path_name + "." + bundles[bgroup]["hash"] + "." + bgroup))
            for file in os.listdir(file_dir):
                file = os.path.join(file_dir, file)
                startwith = str(os.path.join(str(Config().module_root), path_name)) + "."
                endwith = "." + bgroup
                if os.path.isfile(file) and file.startswith(startwith) and file.endswith(endwith):
                    os.remove(file)

            for group in bundles[bgroup]["files"]:
                file = files.findall(group)
                file = file[0]
                parms = parameters.findall(group)
                final_parms = []
                while parms:
                    param = parms.pop()
                    if len(param.split("||")) > 1:
                        final_parms.extend(param.split("||"))
                        continue
                    final_parms.append(param)
                parms = [i.replace("#|#", "|") for i in final_parms]
                for num, param in enumerate(parms.copy()):
                    parms[num] = param.strip("#&N#").strip(" ").strip("#&N#").strip(" ")
                parms = [i.split("=") for i in parms]  # [[key, value]...]
                cont = FileManager.get_file_if_valid(file)
                if isinstance(cont, Parser):
                    self.static_requirements.update(cont.static_requirements)
                    cont = cont.html_content
                self.contexts.append(cont)
                self.contexts.extend([self.parsed, content, fixed, ])
                cont = self.load_variables(_content=cont, _load_list=parms, _addnl_var_contexts=self.contexts)
                self.contexts.append(cont)
                bundles[bgroup]["content"] += cont
        for bgroup in bundles:
            with open(os.path.join(str(Config().module_root), path_name + "." + bundles[bgroup]["hash"] + "." + bgroup),
                      "wt") as f:
                f.write(bundles[bgroup]["content"])
            while len(bundles[bgroup]["files"]) > 1:
                popped = bundles[bgroup]["files"].pop(0)
                content = content.replace(popped, "")
            popped = bundles[bgroup]["files"].pop(0)
            f_url = (path_name + "." + bundles[bgroup]["hash"] + "." + bgroup)[1::].replace("\\", "/")
            content = content.replace(popped, f_url)
            elapsed_time = datetime.datetime.now() - start
            if elapsed_time > datetime.timedelta(seconds=1):
                print(f'CREATED BUNDLE : {f_url}\nIN: {elapsed_time}')
        if oric is None:
            self.parsing = content.split("\n")
        return content


class Markdown:
    def __init__(self, content=""):
        """
        Parses markdown
        """
        import markdown2
        self.content = content
        self.parsed = markdown2.markdown(content)


class App:
    def __init__(self, app: FastAPI, auto_run=True, uvicorn_kwargs=None):
        for _ in range(1):
            log.warn("THIS FEATURE IS NOT IMPLEMENTED COMPLETELY")
        self.app = app
        self.add_routes()
        self.not_authorized = HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                            detail="You are not authorized to access this file")
        self.static_assets = {}
        if uvicorn_kwargs is None:
            uvicorn_kwargs = {}
        if auto_run:
            import uvicorn
            uvicorn.run(self.app, **uvicorn_kwargs)

    def add_routes(self):
        @self.app.middleware("*")
        async def set_assisted_by_header(request: Request, next_process):
            resp = await next_process(request)
            resp.headers['X-Assisted-By'] = 'eXTRACTO by shashstormer'
            return resp

        @self.app.get("/__static/{path:path}")
        async def serve_static_files(path: str):
            file_path = self.static_assets.get(path, False)
            if not file_path:
                raise self.not_authorized
            with open(file_path, "rb") as f:
                file_content = f.read()
            return Response(file_content)

        @self.app.get("/{path:path}")
        async def serve_pages(path: str = ""):
            if path == "":
                path += "index"
            _pypx_c1 = "../" in path
            _pypx_c2 = path.startswith("_")
            _pypx_c3 = "..\\/" in path
            _pypx_overall = _pypx_c1 or _pypx_c2 or _pypx_c3
            if _pypx_overall:
                raise self.not_authorized
            if len(path.split("/")[-1].split(".")) == 1:
                path += ".pypx"
            if path == "favicon.ico":
                if os.path.exists(Utils.get_project_root() + "/favicon.ico"):
                    return FileResponse(Utils.get_project_root() + "/favicon.ico")
                else:
                    import xtracto._images
                    return xtracto._images.favicon
            _pypx_parsed = Parser(path=path, layout=Utils.layout_exists())
            _pypx_parsed.render()
            _pypx_parsed.load_tailwind()
            _pypx_parsed.clear_variables()
            self.static_assets.update(_pypx_parsed.static_requirements)
            return Response(_pypx_parsed.html_content, media_type="text/html")
