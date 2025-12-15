import os
import shutil
import unittest
from xtracto import Parser, Builder


class TestConfig:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.pages_dir = os.path.join(base_dir, "pages")
        self.modules_dir = os.path.join(base_dir, "components")
        self.build_dir = os.path.join(base_dir, "build")
        self.project_root = base_dir
        self.production = False
        self.reparse_tailwind = False
        os.makedirs(self.pages_dir, exist_ok=True)
        os.makedirs(self.modules_dir, exist_ok=True)
        with open(os.path.join(base_dir, "xtracto.config.py"), "w") as f:
            f.write(f'pages_dir = "pages"\nmodules_dir = "components"\nbuild_dir = "build"\n')


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_build_env")
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
    def test_build_basic(self):
        self.create_page("index.pypx", "h1\n    Hello")
        builder = Builder()
        builder.build()
        build_path = os.path.join(self.config.build_dir, "index.html")
        self.assertTrue(os.path.exists(build_path))
        with open(build_path) as f:
            content = f.read()
        self.assertIn("<h1>Hello\n</h1>", content)
    def test_build_with_import(self):
        self.create_page("page.pypx", "div\n    [[comp.pypx]]")
        self.create_component("comp.pypx", "span\n    Comp")
        builder = Builder()
        builder.build()
        with open(os.path.join(self.config.build_dir, "page.html")) as f:
            content = f.read()
        self.assertIn("<div><span>Comp</span></div>", content.replace("\n", ""))
    def test_production_mode_loading(self):
        self.create_page("prod.pypx", "p\n    Source")
        os.makedirs(self.config.build_dir, exist_ok=True)
        with open(os.path.join(self.config.build_dir, "prod.html"), "w") as f:
            f.write("<p>Built Content</p>")
        os.environ["env"] = "prod"  
        os.environ["env"] = "dev"  
        with open(os.path.join(self.test_dir, "xtracto.config.py"), "a") as f:
            f.write("production = True\n")
        parser = Parser(path="prod.pypx")
        parser.render()
        self.assertIn("Built Content", parser.html_content)
        self.assertNotIn("Source", parser.html_content)


if __name__ == "__main__":
    unittest.main()
