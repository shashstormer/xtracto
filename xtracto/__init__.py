"""
A web framework for integration with pypx
"""
__version__ = "0.0.4"
__author__ = "shashstormer"
__description__ = "A web framework for integration with pypx"

import os
import re
from fastapi import FastAPI, HTTPException, status, Response, Request
from fastapi.responses import FileResponse

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
                _frame = _frame.f_back
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
    def __init__(self, path=None, content=None, module=False, layout=False):
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
        self.pypx_parser = Pypx(self.content, self.raw_origin)
        self.html_content = ""
        self.layout = layout
        self.static_requirements = {}
        self.module = module
        del path, content, module, layout
        if self.content:
            if self.layout:
                self.pypx_parser.load_variables()
            self.parse()

    def parse(self):
        self.pypx_parser.parse(self.layout)
        if not self.module:
            self.static_requirements.update(self.pypx_parser.parse_static_import())
            self.static_requirements.update(self.pypx_parser.static_requirements)
        self.html_content = self.pypx_parser.parsed

    def render(self):
        self.pypx_parser.load_variables()
        self.pypx_parser.do_imports()
        self.pypx_parser.load_variables()
        self.pypx_parser.normalize()
        self.html_content = self.pypx_parser.parsed


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
            try:
                _parser = Parser(path=path, module=True)
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
    def __init__(self, content=None, fname=None):
        """
        Parses pypx
        """
        if content is None:
            content = ""
        content = content.replace("\t", " " * 4)
        self.content = content.split("\n")
        self.fname = fname
        self.parsing = self.content.copy()
        self.groups = [
            ["::", "::"],  # Removed comment
            # ["?:", ":?"],  # Comment to be inserted in html
            ["?:", "?:"],  # File to be included as static asset
            ["{{", "}}"],  # Variable Field
            [";;", ";;"],  # HTML Attribute
            ["[[", "]]"],  # Import Files and embed them into the generated html
            ["(-(", ")-)"],  # Markdown Content
            ["{[", "]}"],  # Bundling groups

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
        _ = Parser(path="_layout.pypx", layout=True)
        _.render()
        self.static_requirements.update(_.static_requirements)
        if self.parsed not in _.html_content:
            log.critical("please put {{children}} in the layout file where the page content must appear")
        self.parsed = _.html_content

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
                        log.error("Syntax error in file being parsed", "FILE CONTENT:\n" + "\n".join(self.parsing))
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
        if content is None:
            content = self.parsed
        content = content.replace("#&N#", "\n")
        if content is None:
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
        if blocks == self.blocks:
            self.parsed = loaded_block
        return loaded_block

    def load_variables(self, _content=None, _load_list: list or None = None):

        _original_content = _content
        if _content is None:
            _content = self.parsed
        if _load_list is None:
            _load_list = []
        for var, val in _load_list:
            locals()[val] = val
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
                _tailwind = Tailwind()
                _value = _tailwind.generate(_content)
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
        fixed = Pypx(content=content)
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
                self.static_requirements.update(cont.static_requirements)
                cont = cont.html_content
            cont = self.load_variables(_content=cont, _load_list=parms)
            fixed = fixed.replace(group, cont)
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
        fixed = Pypx(content=content)
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
                cont = self.load_variables(_content=cont, _load_list=parms)
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


class Tailwind:
    def __init__(self):
        self.colors = {
            "inherit": 'inherit',
            "current": 'currentColor',
            "transparent": 'transparent',
            "black": '#000',
            "white": '#fff',
            "slate": {
                "50": '#f8fafc',
                "100": '#f1f5f9',
                "200": '#e2e8f0',
                "300": '#cbd5e1',
                "400": '#94a3b8',
                "500": '#64748b',
                "600": '#475569',
                "700": '#334155',
                "800": '#1e293b',
                "900": '#0f172a',
                "950": '#020617',
            },
            "gray": {
                "50": '#f9fafb',
                "100": '#f3f4f6',
                "200": '#e5e7eb',
                "300": '#d1d5db',
                "400": '#9ca3af',
                "500": '#6b7280',
                "600": '#4b5563',
                "700": '#374151',
                "800": '#1f2937',
                "900": '#111827',
                "950": '#030712',
            },
            "zinc": {
                "50": '#fafafa',
                "100": '#f4f4f5',
                "200": '#e4e4e7',
                "300": '#d4d4d8',
                "400": '#a1a1aa',
                "500": '#71717a',
                "600": '#52525b',
                "700": '#3f3f46',
                "800": '#27272a',
                "900": '#18181b',
                "950": '#09090b',
            },
            "neutral": {
                "50": '#fafafa',
                "100": '#f5f5f5',
                "200": '#e5e5e5',
                "300": '#d4d4d4',
                "400": '#a3a3a3',
                "500": '#737373',
                "600": '#525252',
                "700": '#404040',
                "800": '#262626',
                "900": '#171717',
                "950": '#0a0a0a',
            },
            "stone": {
                "50": '#fafaf9',
                "100": '#f5f5f4',
                "200": '#e7e5e4',
                "300": '#d6d3d1',
                "400": '#a8a29e',
                "500": '#78716c',
                "600": '#57534e',
                "700": '#44403c',
                "800": '#292524',
                "900": '#1c1917',
                "950": '#0c0a09',
            },
            "red": {
                "50": '#fef2f2',
                "100": '#fee2e2',
                "200": '#fecaca',
                "300": '#fca5a5',
                "400": '#f87171',
                "500": '#ef4444',
                "600": '#dc2626',
                "700": '#b91c1c',
                "800": '#991b1b',
                "900": '#7f1d1d',
                "950": '#450a0a',
            },
            "orange": {
                "50": '#fff7ed',
                "100": '#ffedd5',
                "200": '#fed7aa',
                "300": '#fdba74',
                "400": '#fb923c',
                "500": '#f97316',
                "600": '#ea580c',
                "700": '#c2410c',
                "800": '#9a3412',
                "900": '#7c2d12',
                "950": '#431407',
            },
            "amber": {
                "50": '#fffbeb',
                "100": '#fef3c7',
                "200": '#fde68a',
                "300": '#fcd34d',
                "400": '#fbbf24',
                "500": '#f59e0b',
                "600": '#d97706',
                "700": '#b45309',
                "800": '#92400e',
                "900": '#78350f',
                "950": '#451a03',
            },
            "yellow": {
                "50": '#fefce8',
                "100": '#fef9c3',
                "200": '#fef08a',
                "300": '#fde047',
                "400": '#facc15',
                "500": '#eab308',
                "600": '#ca8a04',
                "700": '#a16207',
                "800": '#854d0e',
                "900": '#713f12',
                "950": '#422006',
            },
            "lime": {
                "50": '#f7fee7',
                "100": '#ecfccb',
                "200": '#d9f99d',
                "300": '#bef264',
                "400": '#a3e635',
                "500": '#84cc16',
                "600": '#65a30d',
                "700": '#4d7c0f',
                "800": '#3f6212',
                "900": '#365314',
                "950": '#1a2e05',
            },
            "green": {
                "50": '#f0fdf4',
                "100": '#dcfce7',
                "200": '#bbf7d0',
                "300": '#86efac',
                "400": '#4ade80',
                "500": '#22c55e',
                "600": '#16a34a',
                "700": '#15803d',
                "800": '#166534',
                "900": '#14532d',
                "950": '#052e16',
            },
            "emerald": {
                "50": '#ecfdf5',
                "100": '#d1fae5',
                "200": '#a7f3d0',
                "300": '#6ee7b7',
                "400": '#34d399',
                "500": '#10b981',
                "600": '#059669',
                "700": '#047857',
                "800": '#065f46',
                "900": '#064e3b',
                "950": '#022c22',
            },
            "teal": {
                "50": '#f0fdfa',
                "100": '#ccfbf1',
                "200": '#99f6e4',
                "300": '#5eead4',
                "400": '#2dd4bf',
                "500": '#14b8a6',
                "600": '#0d9488',
                "700": '#0f766e',
                "800": '#115e59',
                "900": '#134e4a',
                "950": '#042f2e',
            },
            "cyan": {
                "50": '#ecfeff',
                "100": '#cffafe',
                "200": '#a5f3fc',
                "300": '#67e8f9',
                "400": '#22d3ee',
                "500": '#06b6d4',
                "600": '#0891b2',
                "700": '#0e7490',
                "800": '#155e75',
                "900": '#164e63',
                "950": '#083344',
            },
            "sky": {
                "50": '#f0f9ff',
                "100": '#e0f2fe',
                "200": '#bae6fd',
                "300": '#7dd3fc',
                "400": '#38bdf8',
                "500": '#0ea5e9',
                "600": '#0284c7',
                "700": '#0369a1',
                "800": '#075985',
                "900": '#0c4a6e',
                "950": '#082f49',
            },
            "blue": {
                "50": '#eff6ff',
                "100": '#dbeafe',
                "200": '#bfdbfe',
                "300": '#93c5fd',
                "400": '#60a5fa',
                "500": '#3b82f6',
                "600": '#2563eb',
                "700": '#1d4ed8',
                "800": '#1e40af',
                "900": '#1e3a8a',
                "950": '#172554',
            },
            "indigo": {
                "50": '#eef2ff',
                "100": '#e0e7ff',
                "200": '#c7d2fe',
                "300": '#a5b4fc',
                "400": '#818cf8',
                "500": '#6366f1',
                "600": '#4f46e5',
                "700": '#4338ca',
                "800": '#3730a3',
                "900": '#312e81',
                "950": '#1e1b4b',
            },
            "violet": {
                "50": '#f5f3ff',
                "100": '#ede9fe',
                "200": '#ddd6fe',
                "300": '#c4b5fd',
                "400": '#a78bfa',
                "500": '#8b5cf6',
                "600": '#7c3aed',
                "700": '#6d28d9',
                "800": '#5b21b6',
                "900": '#4c1d95',
                "950": '#2e1065',
            },
            "purple": {
                "50": '#faf5ff',
                "100": '#f3e8ff',
                "200": '#e9d5ff',
                "300": '#d8b4fe',
                "400": '#c084fc',
                "500": '#a855f7',
                "600": '#9333ea',
                "700": '#7e22ce',
                "800": '#6b21a8',
                "900": '#581c87',
                "950": '#3b0764',
            },
            "fuchsia": {
                "50": '#fdf4ff',
                "100": '#fae8ff',
                "200": '#f5d0fe',
                "300": '#f0abfc',
                "400": '#e879f9',
                "500": '#d946ef',
                "600": '#c026d3',
                "700": '#a21caf',
                "800": '#86198f',
                "900": '#701a75',
                "950": '#4a044e',
            },
            "pink": {
                "50": '#fdf2f8',
                "100": '#fce7f3',
                "200": '#fbcfe8',
                "300": '#f9a8d4',
                "400": '#f472b6',
                "500": '#ec4899',
                "600": '#db2777',
                "700": '#be185d',
                "800": '#9d174d',
                "900": '#831843',
                "950": '#500724',
            },
            "rose": {
                "50": '#fff1f2',
                "100": '#ffe4e6',
                "200": '#fecdd3',
                "300": '#fda4af',
                "400": '#fb7185',
                "500": '#f43f5e',
                "600": '#e11d48',
                "700": '#be123c',
                "800": '#9f1239',
                "900": '#881337',
                "950": '#4c0519',
            }
        }
        self.spacing = {
            "px": '1px',
            "0": '0px',
            "0.5": '0.125rem',
            "1": '0.25rem',
            "1.5": '0.375rem',
            "2": '0.5rem',
            "2.5": '0.625rem',
            "3": '0.75rem',
            "3.5": '0.875rem',
            "4": '1rem',
            "5": '1.25rem',
            "6": '1.5rem',
            "7": '1.75rem',
            "8": '2rem',
            "9": '2.25rem',
            "10": '2.5rem',
            "11": '2.75rem',
            "12": '3rem',
            "14": '3.5rem',
            "16": '4rem',
            "20": '5rem',
            "24": '6rem',
            "28": '7rem',
            "32": '8rem',
            "36": '9rem',
            "40": '10rem',
            "44": '11rem',
            "48": '12rem',
            "52": '13rem',
            "56": '14rem',
            "60": '15rem',
            "64": '16rem',
            "72": '18rem',
            "80": '20rem',
            "96": '24rem',
        }
        self.classes = {
            "accentColor": {
                "auto": 'auto',
            },
            "animation": {
                "none": 'none',
                "spin": 'spin 1s linear infinite',
                "ping": 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite',
                "pulse": 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                "bounce": 'bounce 1s infinite',
            },
            "aria": {
                "busy": 'busy="true"',
                "checked": 'checked="true"',
                "disabled": 'disabled="true"',
                "expanded": 'expanded="true"',
                "hidden": 'hidden="true"',
                "pressed": 'pressed="true"',
                "readonly": 'readonly="true"',
                "required": 'required="true"',
                "selected": 'selected="true"',
            },
            "aspectRatio": {
                "auto": 'auto',
                "square": '1 / 1',
                "video": '16 / 9',
            },
            "backgroundImage": {
                "none": 'none',
                'gradient-to-t': 'linear-gradient(to top, var(--tw-gradient-stops))',
                'gradient-to-tr': 'linear-gradient(to top right, var(--tw-gradient-stops))',
                'gradient-to-r': 'linear-gradient(to right, var(--tw-gradient-stops))',
                'gradient-to-br': 'linear-gradient(to bottom right, var(--tw-gradient-stops))',
                'gradient-to-b': 'linear-gradient(to bottom, var(--tw-gradient-stops))',
                'gradient-to-bl': 'linear-gradient(to bottom left, var(--tw-gradient-stops))',
                'gradient-to-l': 'linear-gradient(to left, var(--tw-gradient-stops))',
                'gradient-to-tl': 'linear-gradient(to top left, var(--tw-gradient-stops))',
            },
            "backgroundPosition": {
                "bottom": 'bottom',
                "center": 'center',
                "left": 'left',
                'left-bottom': 'left bottom',
                'left-top': 'left top',
                "right": 'right',
                'right-bottom': 'right bottom',
                'right-top': 'right top',
                "top": 'top',
            },
            "backgroundSize": {
                "auto": 'auto',
                "cover": 'cover',
                "contain": 'contain',
            },
            "blur": {
                "0": '0',
                "none": '0',
                "sm": '4px',
                "DEFAULT": '8px',
                "md": '12px',
                "lg": '16px',
                "xl": '24px',
                '2xl': '40px',
                '3xl': '64px',
            },
            "borderRadius": {
                "none": '0px',
                "sm": '0.125rem',
                "DEFAULT": '0.25rem',
                "md": '0.375rem',
                "lg": '0.5rem',
                "xl": '0.75rem',
                '2xl': '1rem',
                '3xl': '1.5rem',
                "full": '9999px',
            },
            "borderWidth": {
                "DEFAULT": '1px',
                "0": '0px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "boxShadow": {
                "sm": '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                "DEFAULT": '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
                "md": '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
                "lg": '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
                "xl": '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
                '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
                "inner": 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
                "none": 'none',
            },
            "brightness": {
                "0": '0',
                '50': '.5',
                "75": '.75',
                "90": '.9',
                "95": '.95',
                "100": '1',
                "105": '1.05',
                "110": '1.1',
                "125": '1.25',
                "150": '1.5',
                "200": '2',
            },
            "colors": self.colors,
            "columns": {
                "auto": 'auto',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
                '3xs': '16rem',
                '2xs': '18rem',
                "xs": '20rem',
                "sm": '24rem',
                "md": '28rem',
                "lg": '32rem',
                "xl": '36rem',
                '2xl': '42rem',
                '3xl': '48rem',
                '4xl': '56rem',
                '5xl': '64rem',
                '6xl': '72rem',
                '7xl': '80rem',
            },
            'container': {},
            'content': {
                'none': 'none',
            },
            'contrast': {
                '0': '0',
                '50': '.5',
                '75': '.75',
                '100': '1',
                '125': '1.25',
                '150': '1.5',
                '200': '2',
            },
            'cursor': {
                'auto': 'auto',
                'default': 'default',
                'pointer': 'pointer',
                'wait': 'wait',
                'text': 'text',
                'move': 'move',
                'help': 'help',
                'not-allowed': 'not-allowed',
                'none': 'none',
                'context-menu': 'context-menu',
                'progress': 'progress',
                'cell': 'cell',
                'crosshair': 'crosshair',
                'vertical-text': 'vertical-text',
                'alias': 'alias',
                'copy': 'copy',
                'no-drop': 'no-drop',
                'grab': 'grab',
                'grabbing': 'grabbing',
                'all-scroll': 'all-scroll',
                'col-resize': 'col-resize',
                'row-resize': 'row-resize',
                'n-resize': 'n-resize',
                'e-resize': 'e-resize',
                's-resize': 's-resize',
                'w-resize': 'w-resize',
                'ne-resize': 'ne-resize',
                'nw-resize': 'nw-resize',
                'se-resize': 'se-resize',
                'sw-resize': 'sw-resize',
                'ew-resize': 'ew-resize',
                'ns-resize': 'ns-resize',
                'nesw-resize': 'nesw-resize',
                'nwse-resize': 'nwse-resize',
                'zoom-in': 'zoom-in',
                'zoom-out': 'zoom-out',
            },
            "dropShadow": {
                "sm": '0 1px 1px rgb(0 0 0 / 0.05)',
                "DEFAULT": ['0 1px 2px rgb(0 0 0 / 0.1)', '0 1px 1px rgb(0 0 0 / 0.06)'],
                "md": ['0 4px 3px rgb(0 0 0 / 0.07)', '0 2px 2px rgb(0 0 0 / 0.06)'],
                "lg": ['0 10px 8px rgb(0 0 0 / 0.04)', '0 4px 3px rgb(0 0 0 / 0.1)'],
                "xl": ['0 20px 13px rgb(0 0 0 / 0.03)', '0 8px 5px rgb(0 0 0 / 0.08)'],
                '2xl': '0 25px 25px rgb(0 0 0 / 0.15)',
                "none": '0 0 #0000',
            },
            "display": {
    "block": "block",
    "inline": "inline",
    "inline-block": "inline-block",
    "flex": "flex",
    "inline-flex": "inline-flex",
    "grid": "grid",
    "inline-grid": "inline-grid",
    "table": "table",
    "inline-table": "inline-table",
    "table-row": "table-row",
    "table-cell": "table-cell",
    "none": "none"
},
            "fill": self.colors,
            "flex": {
                "1": '1 1 0%',
                "auto": '1 1 auto',
                "initial": '0 1 auto',
                "none": 'none',
            },
            "flexBasis": {
                "auto": 'auto',
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                '1/5': '20%',
                '2/5': '40%',
                '3/5': '60%',
                '4/5': '80%',
                '1/6': '16.666667%',
                '2/6': '33.333333%',
                '3/6': '50%',
                '4/6': '66.666667%',
                '5/6': '83.333333%',
                '1/12': '8.333333%',
                '2/12': '16.666667%',
                '3/12': '25%',
                '4/12': '33.333333%',
                '5/12': '41.666667%',
                '6/12': '50%',
                '7/12': '58.333333%',
                '8/12': '66.666667%',
                '9/12': '75%',
                '10/12': '83.333333%',
                '11/12': '91.666667%',
                "full": '100%',
            },
            "flexGrow": {
                "0": '0',
                "DEFAULT": '1',
            },
            "flexShrink": {
                "0": '0',
                "DEFAULT": '1',
            },
            "fontFamily": {
                "sans": [
                    'ui-sans-serif',
                    'system-ui',
                    'sans-serif',
                    '"Apple Color Emoji"',
                    '"Segoe UI Emoji"',
                    '"Segoe UI Symbol"',
                    '"Noto Color Emoji"',
                ],
                "serif": ['ui-serif', 'Georgia', 'Cambria', '"Times New Roman"', 'Times', 'serif'],
                "mono": [
                    'ui-monospace',
                    'SFMono-Regular',
                    'Menlo',
                    'Monaco',
                    'Consolas',
                    '"Liberation Mono"',
                    '"Courier New"',
                    'monospace',
                ],
            },
            "fontSize": {
                "xs": ['0.75rem', {"lineHeight": '1rem'}],
                "sm": ['0.875rem', {"lineHeight": '1.25rem'}],
                "base": ['1rem', {"lineHeight": '1.5rem'}],
                "lg": ['1.125rem', {"lineHeight": '1.75rem'}],
                "xl": ['1.25rem', {"lineHeight": '1.75rem'}],
                '2xl': ['1.5rem', {"lineHeight": '2rem'}],
                '3xl': ['1.875rem', {"lineHeight": '2.25rem'}],
                '4xl': ['2.25rem', {"lineHeight": '2.5rem'}],
                '5xl': ['3rem', {"lineHeight": '1'}],
                '6xl': ['3.75rem', {"lineHeight": '1'}],
                '7xl': ['4.5rem', {"lineHeight": '1'}],
                '8xl': ['6rem', {"lineHeight": '1'}],
                '9xl': ['8rem', {"lineHeight": '1'}],
            },
            "fontWeight": {
                "thin": '100',
                "extralight": '200',
                "light": '300',
                "normal": '400',
                "medium": '500',
                "semibold": '600',
                "bold": '700',
                "extrabold": '800',
                "black": '900',
            },
            "gradientColorStopPositions": {
                '0%': '0%',
                '5%': '5%',
                '10%': '10%',
                '15%': '15%',
                '20%': '20%',
                '25%': '25%',
                '30%': '30%',
                '35%': '35%',
                '40%': '40%',
                '45%': '45%',
                '50%': '50%',
                '55%': '55%',
                '60%': '60%',
                '65%': '65%',
                '70%': '70%',
                '75%': '75%',
                '80%': '80%',
                '85%': '85%',
                '90%': '90%',
                '95%': '95%',
                '100%': '100%',
            },
            "grayscale": {
                "0": '0',
                "DEFAULT": '100%',
            },
            "gridAutoColumns": {
                "auto": 'auto',
                "min": 'min-content',
                "max": 'max-content',
                "fr": 'minmax(0, 1fr)',
            },
            "gridAutoRows": {
                "auto": 'auto',
                "min": 'min-content',
                "max": 'max-content',
                "fr": 'minmax(0, 1fr)',
            },
            "gridColumn": {
                "auto": 'auto',
                'span-1': 'span 1 / span 1',
                'span-2': 'span 2 / span 2',
                'span-3': 'span 3 / span 3',
                'span-4': 'span 4 / span 4',
                'span-5': 'span 5 / span 5',
                'span-6': 'span 6 / span 6',
                'span-7': 'span 7 / span 7',
                'span-8': 'span 8 / span 8',
                'span-9': 'span 9 / span 9',
                'span-10': 'span 10 / span 10',
                'span-11': 'span 11 / span 11',
                'span-12': 'span 12 / span 12',
                'span-full': '1 / -1',
            },
            "gridColumnEnd": {
                "auto": 'auto',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
                "13": '13',
            },
            "gridColumnStart": {
                "auto": 'auto',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
                "13": '13',
            },
            "gridRow": {
                "auto": 'auto',
                'span-1': 'span 1 / span 1',
                'span-2': 'span 2 / span 2',
                'span-3': 'span 3 / span 3',
                'span-4': 'span 4 / span 4',
                'span-5': 'span 5 / span 5',
                'span-6': 'span 6 / span 6',
                'span-7': 'span 7 / span 7',
                'span-8': 'span 8 / span 8',
                'span-9': 'span 9 / span 9',
                'span-10': 'span 10 / span 10',
                'span-11': 'span 11 / span 11',
                'span-12': 'span 12 / span 12',
                'span-full': '1 / -1',
            },
            "gridRowEnd": {
                "auto": 'auto',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
                "13": '13',
            },
            "gridRowStart": {
                "auto": 'auto',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
                "13": '13',
            },
            "gridTemplateColumns": {
                "none": 'none',
                "subgrid": 'subgrid',
                "1": 'repeat(1, minmax(0, 1fr))',
                "2": 'repeat(2, minmax(0, 1fr))',
                "3": 'repeat(3, minmax(0, 1fr))',
                "4": 'repeat(4, minmax(0, 1fr))',
                "5": 'repeat(5, minmax(0, 1fr))',
                "6": 'repeat(6, minmax(0, 1fr))',
                "7": 'repeat(7, minmax(0, 1fr))',
                "8": 'repeat(8, minmax(0, 1fr))',
                "9": 'repeat(9, minmax(0, 1fr))',
                "10": 'repeat(10, minmax(0, 1fr))',
                "11": 'repeat(11, minmax(0, 1fr))',
                "12": 'repeat(12, minmax(0, 1fr))',
            },
            "gridTemplateRows": {
                "none": 'none',
                "subgrid": 'subgrid',
                "1": 'repeat(1, minmax(0, 1fr))',
                "2": 'repeat(2, minmax(0, 1fr))',
                "3": 'repeat(3, minmax(0, 1fr))',
                "4": 'repeat(4, minmax(0, 1fr))',
                "5": 'repeat(5, minmax(0, 1fr))',
                "6": 'repeat(6, minmax(0, 1fr))',
                "7": 'repeat(7, minmax(0, 1fr))',
                "8": 'repeat(8, minmax(0, 1fr))',
                "9": 'repeat(9, minmax(0, 1fr))',
                "10": 'repeat(10, minmax(0, 1fr))',
                "11": 'repeat(11, minmax(0, 1fr))',
                "12": 'repeat(12, minmax(0, 1fr))',
            },
            "height": {
                "auto": 'auto',
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                '1/5': '20%',
                '2/5': '40%',
                '3/5': '60%',
                '4/5': '80%',
                '1/6': '16.666667%',
                '2/6': '33.333333%',
                '3/6': '50%',
                '4/6': '66.666667%',
                '5/6': '83.333333%',
                "full": '100%',
                "screen": '100vh',
                "svh": '100svh',
                "lvh": '100lvh',
                "dvh": '100dvh',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "hueRotate": {
                "0": '0deg',
                "15": '15deg',
                "30": '30deg',
                "60": '60deg',
                "90": '90deg',
                "180": '180deg',
            },
            "inset": {
                "auto": 'auto',
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                "full": '100%',
            },
            "invert": {
                "0": '0',
                "DEFAULT": '100%',
            },
            "keyframes": {
                "spin": {
                    "to": {
                        "transform": 'rotate(360deg)',
                    },
                },
                "ping": {
                    '75%, 100%': {
                        "transform": 'scale(2)',
                        "opacity": '0',
                    },
                },
                "pulse": {
                    '50%': {
                        "opacity": '.5',
                    },
                },
                "bounce": {
                    '0%, 100%': {
                        "transform": 'translateY(-25%)',
                        "animationTimingFunction": 'cubic-bezier(0.8,0,1,1)',
                    },
                    '50%': {
                        "transform": 'none',
                        "animationTimingFunction": 'cubic-bezier(0,0,0.2,1)',
                    },
                },
            },
            "letterSpacing": {
                "tighter": '-0.05em',
                "tight": '-0.025em',
                "normal": '0em',
                "wide": '0.025em',
                "wider": '0.05em',
                "widest": '0.1em',
            },
            "lineHeight": {
                "none": '1',
                "tight": '1.25',
                "snug": '1.375',
                "normal": '1.5',
                "relaxed": '1.625',
                "loose": '2',
                "3": '.75rem',
                "4": '1rem',
                "5": '1.25rem',
                "6": '1.5rem',
                "7": '1.75rem',
                "8": '2rem',
                "9": '2.25rem',
                "10": '2.5rem',
            },
            "listStyleType": {
                "none": 'none',
                "disc": 'disc',
                "decimal": 'decimal',
            },
            "listStyleImage": {
                "none": 'none',
            },
            "margin": {
                "auto": 'auto',
            },
            "lineClamp": {
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
            },
            "maxHeight": {
                "none": 'none',
                "full": '100%',
                "screen": '100vh',
                "svh": '100svh',
                "lvh": '100lvh',
                "dvh": '100dvh',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "maxWidth": {
                "none": 'none',
                "xs": '20rem',
                "sm": '24rem',
                "md": '28rem',
                "lg": '32rem',
                "xl": '36rem',
                '2xl': '42rem',
                '3xl': '48rem',
                '4xl': '56rem',
                '5xl': '64rem',
                '6xl': '72rem',
                '7xl': '80rem',
                "full": '100%',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
                "prose": '65ch',
                # ...
                # breakpoints(theme('screens')),
            },
            "minHeight": {
                "full": '100%',
                "screen": '100vh',
                "svh": '100svh',
                "lvh": '100lvh',
                "dvh": '100dvh',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "minWidth": {
                "full": '100%',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "objectPosition": {
                "bottom": 'bottom',
                "center": 'center',
                "left": 'left',
                'left-bottom': 'left bottom',
                'left-top': 'left top',
                "right": 'right',
                'right-bottom': 'right bottom',
                'right-top': 'right top',
                "top": 'top',
            },
            "opacity": {
                "0": '0',
                "5": '0.05',
                "10": '0.1',
                "15": '0.15',
                "20": '0.2',
                "25": '0.25',
                "30": '0.3',
                "35": '0.35',
                "40": '0.4',
                "45": '0.45',
                "50": '0.5',
                "55": '0.55',
                "60": '0.6',
                "65": '0.65',
                "70": '0.7',
                "75": '0.75',
                "80": '0.8',
                "85": '0.85',
                "90": '0.9',
                "95": '0.95',
                "100": '1',
            },
            "order": {
                "first": '-9999',
                "last": '9999',
                "none": '0',
                "1": '1',
                "2": '2',
                "3": '3',
                "4": '4',
                "5": '5',
                "6": '6',
                "7": '7',
                "8": '8',
                "9": '9',
                "10": '10',
                "11": '11',
                "12": '12',
            },
            "outlineOffset": {
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "outlineWidth": {
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "ringColor": {
                "DEFAULT": '#3b82f6'  # theme('colors.blue.500', '#3b82f6'),
            },
            "ringOffsetWidth": {
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "ringOpacity": {
                "DEFAULT": '0.5',
            },
            "ringWidth": {
                "DEFAULT": '3px',
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "rotate": {
                "0": '0deg',
                "1": '1deg',
                "2": '2deg',
                "3": '3deg',
                "6": '6deg',
                "12": '12deg',
                "45": '45deg',
                "90": '90deg',
                "180": '180deg',
            },
            "saturate": {
                "0": '0',
                "50": '.5',
                "100": '1',
                "150": '1.5',
                "200": '2',
            },
            "scale": {
                "0": '0',
                "50": '.5',
                "75": '.75',
                "90": '.9',
                "95": '.95',
                "100": '1',
                "105": '1.05',
                "110": '1.1',
                "125": '1.25',
                "150": '1.5',
            },
            "screens": {
                "sm": '640px',
                "md": '768px',
                "lg": '1024px',
                "xl": '1280px',
                '2xl': '1536px',
            },
            "sepia": {
                "0": '0',
                "DEFAULT": '100%',
            },
            "skew": {
                "0": '0deg',
                "1": '1deg',
                "2": '2deg',
                "3": '3deg',
                "6": '6deg',
                "12": '12deg',
            },
            "spacing": {
                "px": '1px',
                "0": '0px',
                "0.5": '0.125rem',
                "1": '0.25rem',
                "1.5": '0.375rem',
                "2": '0.5rem',
                "2.5": '0.625rem',
                "3": '0.75rem',
                "3.5": '0.875rem',
                "4": '1rem',
                "5": '1.25rem',
                "6": '1.5rem',
                "7": '1.75rem',
                "8": '2rem',
                "9": '2.25rem',
                "10": '2.5rem',
                "11": '2.75rem',
                "12": '3rem',
                "14": '3.5rem',
                "16": '4rem',
                "20": '5rem',
                "24": '6rem',
                "28": '7rem',
                "32": '8rem',
                "36": '9rem',
                "40": '10rem',
                "44": '11rem',
                "48": '12rem',
                "52": '13rem',
                "56": '14rem',
                "60": '15rem',
                "64": '16rem',
                "72": '18rem',
                "80": '20rem',
                "96": '24rem',
            },
            "stroke": {
                "none": 'none',
            },
            "strokeWidth": {
                "0": '0',
                "1": '1',
                "2": '2',
            },
            "supports": {},
            "data": {},
            "textDecorationThickness": {
                "auto": 'auto',
                'from-font': 'from-font',
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "textUnderlineOffset": {
                "auto": 'auto',
                "0": '0px',
                "1": '1px',
                "2": '2px',
                "4": '4px',
                "8": '8px',
            },
            "transformOrigin": {
                "center": 'center',
                "top": 'top',
                'top-right': 'top right',
                "right": 'right',
                'bottom-right': 'bottom right',
                "bottom": 'bottom',
                'bottom-left': 'bottom left',
                "left": 'left',
                'top-left': 'top left',
            },
            "transitionDelay": {
                "0": '0s',
                "75": '75ms',
                "100": '100ms',
                "150": '150ms',
                "200": '200ms',
                "300": '300ms',
                "500": '500ms',
                "700": '700ms',
                "1000": '1000ms',
            },
            "transitionDuration": {
                "DEFAULT": '150ms',
                "0": '0s',
                "75": '75ms',
                "100": '100ms',
                "150": '150ms',
                "200": '200ms',
                "300": '300ms',
                "500": '500ms',
                "700": '700ms',
                "1000": '1000ms',
            },
            "transitionProperty": {
                "none": 'none',
                "all": 'all',
                "DEFAULT":
                    'color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter',
                "colors": 'color, background-color, border-color, text-decoration-color, fill, stroke',
                "opacity": 'opacity',
                "shadow": 'box-shadow',
                "transform": 'transform',
            },
            "transitionTimingFunction": {
                "DEFAULT": 'cubic-bezier(0.4, 0, 0.2, 1)',
                "linear": 'linear',
                "in": 'cubic-bezier(0.4, 0, 1, 1)',
                "out": 'cubic-bezier(0, 0, 0.2, 1)',
                'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
            },
            "translate": {
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                "full": '100%',
            },
            "size": {
                "auto": 'auto',
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                '1/5': '20%',
                '2/5': '40%',
                '3/5': '60%',
                '4/5': '80%',
                '1/6': '16.666667%',
                '2/6': '33.333333%',
                '3/6': '50%',
                '4/6': '66.666667%',
                '5/6': '83.333333%',
                '1/12': '8.333333%',
                '2/12': '16.666667%',
                '3/12': '25%',
                '4/12': '33.333333%',
                '5/12': '41.666667%',
                '6/12': '50%',
                '7/12': '58.333333%',
                '8/12': '66.666667%',
                '9/12': '75%',
                '10/12': '83.333333%',
                '11/12': '91.666667%',
                "full": '100%',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "width": {
                "auto": 'auto',
                '1/2': '50%',
                '1/3': '33.333333%',
                '2/3': '66.666667%',
                '1/4': '25%',
                '2/4': '50%',
                '3/4': '75%',
                '1/5': '20%',
                '2/5': '40%',
                '3/5': '60%',
                '4/5': '80%',
                '1/6': '16.666667%',
                '2/6': '33.333333%',
                '3/6': '50%',
                '4/6': '66.666667%',
                '5/6': '83.333333%',
                '1/12': '8.333333%',
                '2/12': '16.666667%',
                '3/12': '25%',
                '4/12': '33.333333%',
                '5/12': '41.666667%',
                '6/12': '50%',
                '7/12': '58.333333%',
                '8/12': '66.666667%',
                '9/12': '75%',
                '10/12': '83.333333%',
                '11/12': '91.666667%',
                "full": '100%',
                "screen": '100vw',
                "svw": '100svw',
                "lvw": '100lvw',
                "dvw": '100dvw',
                "min": 'min-content',
                "max": 'max-content',
                "fit": 'fit-content',
            },
            "willChange": {
                "auto": 'auto',
                "scroll": 'scroll-position',
                "contents": 'contents',
                "transform": 'transform',
            },
            "zIndex": {
                "auto": 'auto',
                "0": '0',
                "10": '10',
                "20": '20',
                "30": '30',
                "40": '40',
                "50": '50',
            },
        }
        for c1, c2 in [
            ["flexBasis", "spacing"],
            ["margin", "spacing"],
            ["maxHeight", "spacing"],
            ["maxWidth", "spacing"],
            ["minHeight", "spacing"],
            ["minWidth", "spacing"],
            ["ringColor", "colors"],
            ["ringOpacity", "opacity"],
            ["stroke", "colors"],
            ["translate", "spacing"],
            ["size", "spacing"],
            ["width", "spacing"],
            ["accentColor", "colors"],
            # ["", ""],
        ]:
            self.classes[c1].update(self.classes[c2])
        for c1, c2 in [
            ["backdropBlur", 'blur'],
            ["backdropBrightness", "brightness"],
            ["backdropContrast", "contrast"],
            ["backdropGrayscale", "grayscale"],
            ["backdropHueRotate", "hueRotate"],
            ["backdropInvert", "invert"],
            ["backdropOpacity", "opacity"],
            ["backdropSaturate", "saturate"],
            ["backdropSepia", "sepia"],
            ["backgroundColor", "colors"],
            ["backgroundOpacity", "opacity"],
            ["borderColor", "colors"],
            ["borderOpacity", "opacity"],
            ["borderSpacing", "spacing"],
            ["boxShadowColor", "colors"],
            ["caretColor", "colors"],
            ["divideColor", "borderColor"],
            ["divideOpacity", "borderOpacity"],
            ["divideWidth", "borderWidth"],
            ["gap", "spacing"],
            ["gradientColorStops", "colors"],
            ["height", "spacing"],
            ["inset", "spacing"],
            ["outlineColor", "colors"],
            ["padding", "spacing"],
            ["placeholderColor", "colors"],
            ["placeholderOpacity", "opacity"],
            ["ringOffsetColor", "colors"],
            ["scrollMargin", "spacing"],
            ["scrollPadding", "spacing"],
            ["space", "spacing"],
            ["textColor", "colors"],
            ["textDecorationColor", "colors"],
            ["textIndent", "spacing"],
            ["textOpacity", "opacity"],
            # ["", ""],
        ]:
            self.classes[c1] = self.classes[c2]
        self.dynamic_value = {"text": "color", "w": "width", "h": "height", "z": "zIndex"}
        for i, j in [["m", "margin"], ["p", "padding"]]:
            for x, y in [["t", "top"], ["r","right"], ["l", "left"], ["b", "bottom"]]:
                self.dynamic_value[i+x] = j + "-" + y

        self.to_css_name = {
            "animation": "animation",
            "aria": "aria",
            "aspectRatio": "aspect-ratio",
            "backgroundImage": "background-image",
            "backgroundPosition": "background-position",
            "backgroundSize": "background-size",
            "blur": "blur",
            "borderRadius": "border-radius",
            "borderWidth": "border-width",
            "boxShadow": "box-shadow",
            "brightness": "brightness",
            "colors": "color",
            "columns": "columns",
            "container": "container",
            "content": "content",
            "contrast": "contrast",
            "cursor": "cursor",
            "dropShadow": "drop-shadow",
            "fill": "fill",
            "flex": "flex",
            "flexBasis": "flex-basis",
            "flexGrow": "flex-grow",
            "flexShrink": "flex-shrink",
            "fontFamily": "font-family",
            "fontSize": "font-size",
            "fontWeight": "font-weight",
            "gradientColorStopPositions": "gradient-color-stop-positions",
            "grayscale": "grayscale",
            "gridAutoColumns": "grid-auto-columns",
            "gridAutoRows": "grid-auto-rows",
            "gridColumn": "grid-column",
            "gridColumnEnd": "grid-column-end",
            "gridColumnStart": "grid-column-start",
            "gridRow": "grid-row",
            "gridRowEnd": "grid-row-end",
            "gridRowStart": "grid-row-start",
            "gridTemplateColumns": "grid-template-columns",
            "gridTemplateRows": "grid-template-rows",
            "height": "height",
            "hueRotate": "hue-rotate",
            "inset": "inset",
            "invert": "invert",
            "keyframes": "keyframes",
            "letterSpacing": "letter-spacing",
            "lineHeight": "line-height",
            "listStyleType": "list-style-type",
            "listStyleImage": "list-style-image",
            "margin": "margin",
            "lineClamp": "line-clamp",
            "maxHeight": "max-height",
            "maxWidth": "max-width",
            "minHeight": "min-height",
            "minWidth": "min-width",
            "objectPosition": "object-position",
            "opacity": "opacity",
            "order": "order",
            "outlineOffset": "outline-offset",
            "outlineWidth": "outline-width",
            "ringColor": "ring-color",
            "ringOffsetWidth": "ring-offset-width",
            "ringOpacity": "ring-opacity",
            "ringWidth": "ring-width",
            "rotate": "rotate",
            "saturate": "saturate",
            "scale": "scale",
            "screens": "screens",
            "sepia": "sepia",
            "skew": "skew",
            "spacing": "spacing",
            "stroke": "stroke",
            "strokeWidth": "stroke-width",
            "supports": "supports",
            "data": "data",
            "textDecorationThickness": "text-decoration-thickness",
            "textUnderlineOffset": "text-underline-offset",
            "transformOrigin": "transform-origin",
            "transitionDelay": "transition-delay",
            "transitionDuration": "transition-duration",
            "transitionProperty": "transition-property",
            "transitionTimingFunction": "transition-timing-function",
            "translate": "translate",
            "size": "size",
            "width": "width",
            "willChange": "will-change",
            "zIndex": "z-index",
            "backdropBlur": "backdrop-blur",
            "backdropBrightness": "backdrop-brightness",
            "backdropContrast": "backdrop-contrast",
            "backdropGrayscale": "backdrop-grayscale",
            "backdropHueRotate": "backdrop-hue-rotate",
            "backdropInvert": "backdrop-invert",
            "backdropOpacity": "backdrop-opacity",
            "backdropSaturate": "backdrop-saturate",
            "backdropSepia": "backdrop-sepia",
            "backgroundColor": "background-color",
            "backgroundOpacity": "background-opacity",
            "borderColor": "border-color",
            "borderOpacity": "border-opacity",
            "borderSpacing": "border-spacing",
            "boxShadowColor": "box-shadow-color",
            "caretColor": "caret-color",
            "divideColor": "divide-color",
            "divideOpacity": "divide-opacity",
            "divideWidth": "divide-width",
            "gap": "gap",
            "gradientColorStops": "gradient-color-stops",
            "outlineColor": "outline-color",
            "padding": "padding",
            "placeholderColor": "placeholder-color",
            "placeholderOpacity": "placeholder-opacity",
            "ringOffsetColor": "ring-offset-color",
            "scrollMargin": "scroll-margin",
            "scrollPadding": "scroll-padding",
            "space": "space",
            "textColor": "text-color",
            "textDecorationColor": "text-decoration-color",
            "textIndent": "text-indent",
            "textOpacity": "text-opacity",
        }
        self.to_tailwind_name = {
            "animation": "animate",
            "aria": "aria",
            "aspectRatio": "aspect",
            "backgroundImage": "bg",
            "backgroundPosition": "bg",
            "backgroundSize": "bg",
            "blur": "blur",
            "borderRadius": "rounded",
            "borderWidth": "border",
            "boxShadow": "shadow",
            "brightness": "brightness",
            "colors": "colors",
            "columns": "columns",
            "container": "container",
            "content": "content",
            "contrast": "contrast",
            "cursor": "cursor",
            "dropShadow": "drop-shadow",
            "display": [
    "block",
    "inline",
    "inline-block",
    "flex",
    "inline-flex",
    "grid",
    "inline-grid",
    "table",
    "inline-table",
    "table-row",
    "table-cell",
    "none"
],
            "fill": "fill",
            "flex": "flex",
            "flexBasis": "basis",
            "flexGrow": "grow",
            "flexShrink": "shrink",
            "fontFamily": "font",
            "fontSize": "text",
            "fontWeight": "font",
            "gradientColorStopPositions": "gradient",
            "grayscale": "grayscale",
            "gridAutoColumns": "auto-cols",
            "gridAutoRows": "auto-rows",
            "gridColumn": "col",
            "gridColumnEnd": "col-end",
            "gridColumnStart": "col-start",
            "gridRow": "row",
            "gridRowEnd": "row-end",
            "gridRowStart": "row-start",
            "gridTemplateColumns": "grid-cols",
            "gridTemplateRows": "grid-rows",
            "height": "h",
            "hueRotate": "hue-rotate",
            "inset": "inset",
            "invert": "invert",
            "keyframes": "keyframes",
            "letterSpacing": "tracking",
            "lineHeight": "leading",
            "listStyleType": "list",
            "listStyleImage": "list",
            "margin": ["m", "ml", "mt", "mr", "mb"],
            "lineClamp": "line-clamp",
            "maxHeight": "max-h",
            "maxWidth": "max-w",
            "minHeight": "min-h",
            "minWidth": "min-w",
            "objectPosition": "object",
            "opacity": "opacity",
            "order": "order",
            "outlineOffset": "outline-offset",
            "outlineWidth": "outline",
            "ringColor": "ring",
            "ringOffsetWidth": "ring-offset",
            "ringOpacity": "ring-opacity",
            "ringWidth": "ring",
            "rotate": "rotate",
            "saturate": "saturate",
            "scale": "scale",
            "screens": "screens",
            "sepia": "sepia",
            "skew": "skew",
            "spacing": "space",
            "stroke": "stroke",
            "strokeWidth": "stroke",
            "supports": "supports",
            "data": "data",
            "textDecorationThickness": "decoration",
            "textUnderlineOffset": "underline-offset",
            "transformOrigin": "origin",
            "transitionDelay": "delay",
            "transitionDuration": "duration",
            "transitionProperty": "transition",
            "transitionTimingFunction": "ease",
            "translate": "translate",
            "size": "size",
            "width": "w",
            "willChange": "will-change",
            "zIndex": "z",
            "backdropBlur": "backdrop-blur",
            "backdropBrightness": "backdrop-brightness",
            "backdropContrast": "backdrop-contrast",
            "backdropGrayscale": "backdrop-grayscale",
            "backdropHueRotate": "backdrop-hue-rotate",
            "backdropInvert": "backdrop-invert",
            "backdropOpacity": "backdrop-opacity",
            "backdropSaturate": "backdrop-saturate",
            "backdropSepia": "backdrop-sepia",
            "backgroundColor": "bg",
            "backgroundOpacity": "bg-opacity",
            "borderColor": "border",
            "borderOpacity": "border-opacity",
            "borderSpacing": "border-spacing",
            "boxShadowColor": "shadow",
            "caretColor": "caret",
            "divideColor": "divide",
            "divideOpacity": "divide-opacity",
            "divideWidth": "divide",
            "gap": "gap",
            "gradientColorStops": "gradient",
            "outlineColor": "outline",
            "padding": ["p", "pt", "pl", "pr", "pb"],
            "placeholderColor": "placeholder",
            "placeholderOpacity": "placeholder-opacity",
            "ringOffsetColor": "ring-offset",
            "scrollMargin": "scroll-m",
            "scrollPadding": "scroll-p",
            "space": "space",
            "textColor": "text",
            "textDecorationColor": "decoration",
            "textIndent": "indent",
            "textOpacity": "text-opacity",
        }

    def _tailwind_gps_matched(self, first):
        matches = []
        for i in self.to_tailwind_name:
            gp = self.to_tailwind_name[i]
            if gp == first:
                matches.append(i)
            if isinstance(gp, list):
                if first in gp:
                    matches.append(i)
        return matches

    def generate(self, page_content):
        match_classes = re.compile('class\s*=\s*["\']([^"\']+)["\']')
        classes = match_classes.findall(page_content)
        classes_list = []
        result_css = ""
        for i in classes:
            i = i.split(" ")
            for j in i:
                if j not in classes_list:
                    classes_list.append(j)
        for i in classes_list:
            j = i.split("-")
            if len(j) >= 2:
                if (j[0] in ["max", "min"] and j[1] in ["h", "w"]) or (j[0] in [] and j[1] in []):
                    x = ""
                    x += j.pop(0)
                    x += j.pop(0)
            gps = self._tailwind_gps_matched(j[0])
            res = ""
            gp_res = ""

            for gp in gps:
                if len(j) == 1:
                    if gp == j[0]:
                        res = self.classes[gp].get("DEFAULT", "")
                    else:
                        res = self.classes[gp].get(j[0], "")
                    if res:
                        gp_res = gp
                if len(j) == 2:
                    res = self.classes[gp].get(j[1], "")
                    if j[1].startswith("["):
                        gp_res = self.dynamic_value.get(j[0], "")
                        if gp_res:
                            res = j[1].replace("[", "").replace("]", "")
                    if isinstance(res, dict):
                            res = res.get("DEFAULT", "")
                    if res:
                        gp_res = gp
                if len(j) == 3:
                    res = self.classes[gp].get(j[1], {}).get(j[2], "")
                    if res:
                        gp_res = gp
                if res:
                    result_css += ".%s {%s: %s;}" % (i.replace("[", "\\[").replace("]", "\\]"), self.to_css_name.get(gp_res, gp_res), res)
        return result_css

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
            self.static_assets.update(_pypx_parsed.static_requirements)
            return Response(_pypx_parsed.html_content, media_type="text/html")
