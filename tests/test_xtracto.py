import os
import shutil
import unittest
from xtracto import Parser


class TestConfig:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.pages_dir = os.path.join(base_dir, "pages")
        self.modules_dir = os.path.join(base_dir, "components")
        self.project_root = base_dir
        os.makedirs(self.pages_dir, exist_ok=True)
        os.makedirs(self.modules_dir, exist_ok=True)
        with open(os.path.join(base_dir, "xtracto.config.py"), "w") as f:
            f.write(f'pages_dir = "pages"\nmodules_dir = "components"\n')


class TestXtracto(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_env")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.config = TestConfig(self.test_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    def create_page(self, filename, content):
        with open(os.path.join(self.config.pages_dir, filename), "w") as f:
            f.write(content)
    def create_component(self, filename, content):
        with open(os.path.join(self.config.modules_dir, filename), "w") as f:
            f.write(content)
    def test_basic_rendering(self):
        self.create_page("index.pypx", "html\n    body\n        h1\n            Hello World")
        parser = Parser(path="index.pypx")
        parser.render()
        self.assertIn("<html><body><h1>Hello World</h1></body></html>", parser.html_content.replace("\n", ""))
    def test_variable_rendering(self):
        self.create_page("vars.pypx", "p\n    Value: {{my_var}}")
        parser = Parser(path="vars.pypx")
        parser.render(context={"my_var": "Test Value"})
        self.assertIn("Value: Test Value", parser.html_content)
    def test_default_variable(self):
        self.create_page("default.pypx", "p\n    Value: {{my_var=Default}}")
        parser = Parser(path="default.pypx")
        parser.render()
        self.assertIn("Value: Default", parser.html_content)
    def test_import_component(self):
        self.create_component("comp.pypx", "span\n    Component")
        self.create_page("import.pypx", "div\n    [[comp.pypx]]")
        parser = Parser(path="import.pypx")
        parser.render()
        self.assertIn("<span>Component</span>", parser.html_content.replace("\n", ""))
    def test_import_with_vars(self):
        self.create_component("comp_vars.pypx", "span\n    {{val}}")
        self.create_page("import_vars.pypx", "div\n    [[comp_vars.pypx || val='Passed']]")
        parser = Parser(path="import_vars.pypx")
        parser.render()
        self.assertIn("<span>Passed</span>", parser.html_content.replace("\n", ""))
    def test_nested_imports(self):
        self.create_component("child.pypx", "p\n    Child")
        self.create_component("parent.pypx", "div\n    [[child.pypx]]")
        self.create_page("nested.pypx", "section\n    [[parent.pypx]]")
        parser = Parser(path="nested.pypx")
        parser.render()
        content = parser.html_content.replace("\n", "")
        self.assertIn("<section><div><p>Child", content)
    def test_layout(self):
        with open(os.path.join(self.config.pages_dir, "_layout.pypx"), "w") as f:
            f.write("html\n    body\n        header\n        {{children}}\n        footer")
        self.create_page("page_layout.pypx", "main\n    Content")
        parser = Parser(path="page_layout.pypx")
        parser.render()
        content = parser.html_content.replace("\n", "")
        self.assertIn("header", content)
        self.assertIn("footer", content)
        self.assertIn("<main>Content", content)
    def test_missing_file(self):
        self.create_page("missing.pypx", "div\n    [[nonexistent.pypx]]")
        parser = Parser(path="missing.pypx")
        parser.render()
        self.assertIn("<div></div>", parser.html_content.replace("\n", ""))
    def test_jinja2_logic(self):
        self.create_page("logic.pypx", "{% if show %}\nshown\n{% else %}\nhidden\n{% endif %}")
        parser = Parser(path="logic.pypx")
        parser.render(context={"show": True})
        self.assertIn("shown", parser.html_content)
        parser.render(context={"show": False})
        self.assertIn("hidden", parser.html_content)


if __name__ == "__main__":
    unittest.main()
