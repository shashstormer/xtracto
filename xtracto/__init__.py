import inspect
import os
import importlib.util
import re
import uvicorn
from fastapi import FastAPI, Response
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
import xtracto._images


class Parser:
    def __init__(self, **_kwargs):
        """
        You may pass the following kwargs:

            path: file path

            content: content to be parsed to html

            render_layout: this will load the paage into the layout defined in {pages_dir}/_layout.pypx (default True)

            use_saved: Pass this variable to alway render the content from source file (default True)

        note: path and content parameters are mutually exclusive.
        :param _kwargs:
        """
        self._kwargs = ["path", "content", "render_layout"]
        for key in _kwargs:
            if key not in self._kwargs:
                raise ValueError(f"\"{key}\" is not a valid parameter")
        self.project_root = None
        self.pages_root = None
        self.module_root = None
        self.strip_imports = False
        self.raise_value_errors_while_importing = False
        self.imports = []
        self.variables = {}
        self.variables_list = []
        self.get_project_root()
        self.load_config()
        if _kwargs.get("content", False) and _kwargs.get("path", False):
            print("WARNING: BOTH CONTENT AND PATH PASSED USING CONTENT")
            print("WARNING: USE EITHER CONTENT OR PATH")
            content = _kwargs.get("content")
            path = False
        elif _kwargs.get("path", False):
            path = _kwargs.get("path")
            if not path.endswith("pypx"):
                path += ".pypx"
            with open(path) as file:
                content = file.read()
        else:
            content = _kwargs.get("content", False)
            path = False
        if self.strip_imports and content:
            content = content.strip("\n")
        self.render_layout = _kwargs.get("render_layout", True)
        self.content_loaded_from = "path" if path else "content"
        self.raw_content_origin = path if path else content
        self.raw_content = content
        self.unmodfied_raw_content = content
        self.html_content = ""
        self.blocks = []
        if self.content_loaded_from == "path" and _kwargs.get("use_saved", True):
            self._render_saved()
            if self.html_content:
                print("Rendered saved content: %s" % self.raw_content_origin)
                return
        if self.raw_content:
            self.parse_content()

    def parse_content(self, **kwargs):
        """
        This a wrapper to call all the parsing methods.
        This method can be called externally also,
        but it is recommended that you initialize a new Parser instance with required arguments.
        :param kwargs:
        :return:
        """
        content = kwargs.get("content", False)
        if not content:
            content = self.raw_content
        if not content:
            raise ValueError("NO CONTENT FOUND")
        self._clear_multiple_newlines()  # replace a sequence of newlines with single new line
        self._parse_coments()
        self._clear_multiple_newlines()
        self._parse_variables()
        self._clear_multiple_newlines()
        self._parse_markdown()
        self._clear_multiple_newlines()
        self._parse_imports()
        self._clear_multiple_newlines()
        self._parse_blocks()
        self._parse_to_html()
        self._parse_to_normal()
        if self.render_layout:
            _soup = BeautifulSoup(self.html_content, 'html.parser')
            try:
                title = _soup.title.get_text()
            except AttributeError:
                pass
            _head = _soup.head
            try:
                _title_tag = _head.title
            except AttributeError:
                _title_tag = False
            if _title_tag:
                _title_tag.extract()
            _body_element = _soup.body
            if _body_element:
                _header_exists = _body_element.header is not None
                _footer_exists = _body_element.footer is not None
            else:
                _header_exists = False
                _footer_exists = False

            def parse_bs4tag_to_plain(tag):
                if isinstance(tag, Comment):
                    return f"<!--{str(tag)}-->"
                elif isinstance(tag, Tag):
                    return tag.prettify()
                elif isinstance(tag, NavigableString):
                    return str(tag)
                else:
                    return ''

            if _body_element:
                _content_before_header = ''.join([parse_bs4tag_to_plain(tag) for tag in _body_element.contents[
                                                                                        :_body_element.contents.index(
                                                                                            _body_element.header)]] if _header_exists else '')

                _content_after_header_before_footer = ''.join(
                    [parse_bs4tag_to_plain(tag) for tag in _body_element.contents[
                                                           _body_element.contents.index(
                                                               _body_element.header):_body_element.contents.index(
                                                               _body_element.footer) - 1]] if _header_exists and _footer_exists else ''.join(
                        [parse_bs4tag_to_plain(tag) for tag in _body_element.contents]))

                _content_after_footer = ''.join([parse_bs4tag_to_plain(tag) for tag in _body_element.contents[
                                                                                       _body_element.contents.index(
                                                                                           _body_element.footer) + 1:]]) if _footer_exists else ''
            if _head:
                headcontent = str("".join(
                    parse_bs4tag_to_plain(i) for i in
                    _head.contents) if _head and _head.contents else "").strip().replace(
                    "{", "#{#").replace("\n", '#&N#')
            if _body_element:
                preheader = _content_before_header.strip().replace("{", "#{#").replace("\n", '#&N#')
                children = _content_after_header_before_footer
                postfooter = _content_after_footer.strip().replace("{", "#{#").replace("\n", '#&N#')
                children = children.strip(postfooter)
            else:
                children = self.html_content
            for element in ["preheader", "postfooter"]:
                try:
                    if not locals()[element]:
                        del locals()[element]
                except (NameError, KeyError):
                    pass
            page = Parser(path=os.path.join(self.pages_root, "_layout.pypx"), render_layout=False)
            if "children" not in page.variables_list:
                print("ERROR: NO CHILDREN VARIABLE IN LAYOUT")
                raise ValueError("No \"children\" variables specified in the _layout.pypx")
            self.html_content = page.html_content
        if not self.variables:
            self._save_render()

    def _save_render(self):
        """
        checks if the page is a static page and saves it if it is static othewise does nothing.
        :return:
        """
        pass

    def transform_to_parsable(self, content):
        """
        Use this method to transform your content into a form that will be compatible with the parser

        This method is also used internally when importing css and js files
        :param content:
        :return:
        """
        pass

    def _render_saved(self):
        """
        This method checks if the source file is older than the compiled file and if it is older,
         it returs the compiled file otherwise it recompiles the file.
        :return:
        """
        pass

    def _parse_markdown(self):
        """
        Markdown parser (Support for markdown to be added soon)
        :return:
        """
        pass

    def create_sitemap(self, start_path_for_map="/"):
        """
        Creates sitemap.txt for pages in the pages folder with / (or the passed start path) as the path for all files.
        :param start_path_for_map:
        :return:
        """
        pass

    def _parse_to_normal(self):
        self.html_content = self.html_content.replace("#&n#", "\n").replace("#&N#", "\n")
        groups_to_normalize = re.compile("(#(..?)#)").findall(self.html_content)
        for group, value in groups_to_normalize:
            self.html_content = self.html_content.replace(group, value)

    def _clear_multiple_newlines(self):
        content = self.raw_content
        multiple_newlines = re.compile("(\n(\s*\n)+)").findall(content)
        for newlines, _ in multiple_newlines:
            content = content.replace(newlines, "\n")
        self.raw_content = content

    def _parse_blocks(self):
        content = self.raw_content
        result = []
        stack = []
        lines = content.split('\n')
        for line in lines:
            if not line:
                continue  # Skip empty lines
            indent_level = len(line) - len(line.lstrip())
            line = line.strip()
            while stack and stack[-1][0] >= indent_level:
                stack.pop()
            if stack:
                current_indent, current_list = stack[-1]
                while len(stack) > indent_level:
                    stack.pop()
                if line.startswith(";"):
                    new_list = line[1:-1]
                    line = "?:attribute?:"
                elif line.startswith("?:"):
                    line = f"<!--{line[2:-2]}-->"
                    new_list = []
                else:
                    new_list = []
                current_list.append([line, new_list])
                stack.append((indent_level, new_list))
            else:
                new_list = []
                result.append([line, new_list])
                stack.append((indent_level, new_list))
        self.blocks = result
        return result

    def _get_variable_value(self, variable_name, default_value=False, definded_in_html=False):
        """
        :param variable_name:
        :param default_value: This default value is used only in the case that there is no default value mentioned in the placeholder
        :return:
        """
        frame = inspect.currentframe()
        while frame:
            if variable_name in frame.f_locals:
                local_value = frame.f_locals[variable_name]
                value = local_value
                break
            frame = frame.f_back
        else:
            if self.raise_value_errors_while_importing and not definded_in_html:
                raise NameError(f"variable \"{variable_name}\" has not been defined")
            value = default_value
        return value

    def _parse_to_html(self, blocks=None):
        html = ""
        if blocks is None:
            blocks = self.blocks.copy()
        for block in blocks:
            if block[0] == "?:attribute?:":
                continue
            if block[1] and block[0]:
                if block[0].startswith("<"):
                    html += block[0] + self._parse_to_html(block[1])
                    continue
                html += f"<{block[0]}"
                for elem in block[1].copy():
                    if elem[0] == "?:attribute?:":
                        html += f" {elem[1]}"
                        block[1].remove(elem)
                if block[1]:
                    html += ">"
                    html += self._parse_to_html(block[1])
                    html += f"</{block[0]}>"
                else:
                    html += "/>"
            elif block[0] and not block[1]:
                html += " " + block[0]
            elif not block[0] and not block[1]:
                html += "<br>"
            else:
                html += f"<{block} />"
        self.html_content = html
        return html

    def _parse_variables(self):
        content = self.raw_content
        vars_regex = re.compile("(\{\s*([^#](?:.*)?)\s*})")
        self.variables_list = vars_regex.findall(content)
        var_list = []
        for var, var_name in self.variables_list:
            if len(var_name.split("=")) == 2:
                var_name, value = var_name.split("=")
                var_name = var_name.strip(" ")
                value = value.strip(" ")
                self.variables[var] = self._get_variable_value(var_name, value, True)
            else:
                self.variables[var] = self._get_variable_value(var_name)
            var_list.append(var_name)
        self.variables_list = var_list
        for var in self.variables:
            self.raw_content = self.raw_content.replace(var, str(self.variables[var]))

    def _parse_imports(self):
        content = self.raw_content.split("\n")
        for line in content:
            indent = len(line) - len(line.lstrip())
            tag = line.strip()
            if tag.startswith("[") and tag.endswith("]"):
                tag_vars_data = re.compile("\|(.*)\|").findall(tag)
                if tag_vars_data:
                    tag_vars = [[i.split("=")[0].strip(), i.split("=")[1].strip()] for i in tag_vars_data[0].split(";")
                                if len(i.split("=")) == 2]
                    tag = tag.replace(f"|{tag_vars_data[0]}|", "").strip()
                else:
                    tag_vars = []
                tag = tag[1:-1]
                for variable, value in tag_vars:
                    locals()[variable] = value
                tag = tag.strip()
                if tag not in self.imports:
                    self.imports.append(tag)
                html = Parser(path=os.path.join(self.module_root, tag), render_layout=False).html_content
                html = (" " * indent) + html
                self.raw_content = self.raw_content.replace(line, html)
                for variable, value in tag_vars:
                    del locals()[variable]
        return content

    def _parse_coments(self):
        raw_content = self.raw_content.split("\n")
        new_raw_content = []
        forwarded_count = 0
        for num, line in enumerate(raw_content.copy()):
            if forwarded_count > 0:
                forwarded_count -= 1
                continue
            while raw_content[num].count("?:") % 2 == 1:
                forwarded_count += 1
                raw_content[num] += " " + raw_content[num + forwarded_count]
                line = raw_content[num]
                spaces = re.compile("(\s\s+)").findall(line)
                spaces.pop(0)
                for space in spaces:
                    line = line.replace(space, " ")
            while "?:" in line:
                line = line.replace("?:", "<!--", 1).replace("?:", "-->", 1)
            new_raw_content.append(line)
        self.raw_content = "\n".join(new_raw_content)
        raw_content = self.raw_content.split("\n")
        new_raw_content = []
        forwarded_count = 0
        for num, line in enumerate(raw_content.copy()):
            if forwarded_count > 0:
                forwarded_count -= 1
                continue
            while raw_content[num].count("::") % 2 == 1:
                forwarded_count += 1
                raw_content[num] += " " + raw_content[num + forwarded_count]
                line = raw_content[num]
                spaces = re.compile("(\s\s+)").findall(line)
                spaces.pop(0)
                for space in spaces:
                    line = line.replace(space, " ")
            new_raw_content.append(line)
        self.raw_content = "\n".join(new_raw_content)
        content = self.raw_content
        comments_regex = re.compile("(::.*::)")
        for comment in comments_regex.findall(content):
            self.raw_content = self.raw_content.replace(comment, "")
        return self.raw_content

    def get_project_root(self):
        current_script = os.getcwd()
        ic = 0
        while not os.path.isfile(os.path.join(current_script, 'xtracto.config.py')):
            ic += 1
            try:
                current_script = os.path.dirname(current_script)
                if ic > 100:
                    raise FileNotFoundError("NO PROJECT CONFIGURATION FILE")
            except Exception as e:
                print(e)
                print("ERROR: NO PROJECT CONFIG FOUND")
                print("TO RESOLVE: CREATE PROJECT CONFIG 'xtracto.congig.py'")
                raise e
        self.project_root = current_script
        return current_script

    def load_config(self):
        def import_module_by_path(module_path):
            spec = importlib.util.spec_from_file_location("module_name", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        config = import_module_by_path(os.path.join(self.project_root, 'xtracto.config.py'))
        self.module_root = os.path.join(self.project_root, getattr(config, "modules_dir", "xtractocomponents"))
        self.pages_root = os.path.join(self.project_root, getattr(config, "pages_dir", "xtractopages"))
        self.strip_imports = getattr(config, 'strip_imports', True)
        self.raise_value_errors_while_importing = getattr(config, 'raise_value_errors_while_importing', True)

    def compile(self, start_path_for_map="/"):
        """
        This method will render non-dynamic pages to html and save it
        and create a sitemap in the pages directory with the name 'sitemap.txt'
        which assumes you have them all under the same start path.
        :return:
        """
        pass
        self.create_sitemap(start_path_for_map)


class App:
    """
    You can use this if you do not want any hassle setting up your server.
    This class will automatically create and run your app ant the specified port
    (default 5005) and host (default 0.0.0.0),
    and you can visit there, and it will automatically render your pages.
    this feature uses fastapi and uvicorn.
    """

    def __init__(self, _host="0.0.0.0", _port=5005):
        _app = FastAPI()
        _parser_instance_for_config = Parser()

        @_app.get("/favicon.ico")
        async def _favicon():
            return _images.favicon

        @_app.get("/{_path:path}")
        async def _render_page(_path="index"):
            if _path == "":
                _path += "index"
            if _path.startswith("_"):
                return Response("Not Allowed")
            try:
                _parsed = Parser(path=os.path.join(_parser_instance_for_config.pages_root, _path + ".pypx"))
            except FileNotFoundError:
                try:
                    _parsed = Parser(path=os.path.join(_parser_instance_for_config.pages_root, _path, "index.pypx"))
                except FileNotFoundError:
                    return Response("404", 404)
            return Response(_parsed.html_content)

        uvicorn.run(_app, host=_host, port=_port)


class Tests:
    def __init__(self, content, path):
        self.test_path = self.path_test(path)
        self.test_content = self.content_test(content)

    class path_test:
        def __init__(self, path):
            self.parser = Parser(path=path)

        def test(self):
            print("MODULES DIR : ", self.parser.module_root)
            print("TEST CONTENT : ")
            print(("-" * 25) + "_" + ("-" * 25))
            print(self.parser.raw_content)
            print(("-" * 25) + "x" + ("-" * 25))
            print("VARIABLES LIST :", self.parser.variables_list)
            print("VARIABLES :", self.parser.variables)
            print(("-" * 25) + "_" + ("-" * 25))
            print(self.parser.raw_content)
            print(("-" * 25) + "x" + ("-" * 25))
            print("BLOCKS : ", self.parser.blocks)
            print(("-" * 25) + "x" + ("-" * 25))
            print("HTML : ", self.parser.html_content)

    class content_test:
        def __init__(self, content):
            self.parser = Parser(content=content)

        def test(self):
            print("MODULES DIR : ", self.parser.module_root)
            print("TEST CONTENT : ")
            print(("-" * 25) + "_" + ("-" * 25))
            print(self.parser.raw_content)
            print(("-" * 25) + "x" + ("-" * 25))
            print("VARIABLES LIST :", self.parser.variables_list)
            print("VARIABLES :", self.parser.variables)
            print(("-" * 25) + "_" + ("-" * 25))
            print(self.parser.raw_content)
            print(("-" * 25) + "x" + ("-" * 25))
            print("BLOCKS : ", self.parser.blocks)
            print(("-" * 25) + "x" + ("-" * 25))
            print("HTML : ", self.parser.html_content)

    def call_tests(self):
        self.test_path.test()
        for i in range(3):
            print(("-" * 25) + "x" + ("-" * 25))
        self.test_content.test()


def test(file):
    Tests(open(file).read(), file).call_tests()
    App()


if __name__ == "__main__":
    test("testrawcontent.pypx")
