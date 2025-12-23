import os
import shutil
import time
import unittest
import logging
import re
from unittest.mock import patch, mock_open, MagicMock
from xtracto import Parser, Utils, Config, Log, Error, FileManager, Pypx, Builder


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


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_env_utils")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_add_content_at_indent(self):
        content = "line1\nline2\nline3"
        new_content = Utils.add_content_at_indent(2, 4, "inserted", content)
        expected = "line1\n    inserted\nline2\nline3"
        self.assertEqual(new_content, expected)

    def test_add_content_at_indent_invalid(self):
        content = "line1"
        # We must mock Log.error/debug to prevent it from calling Config() which might fail if not set up
        # also mock Config to not throw error
        with patch('xtracto.core.config.Config') as mock_config, \
                patch('xtracto.core.logging.Log.error') as mock_log_err, \
                patch('xtracto.core.logging.Log.debug') as mock_log_debug:
            mock_config.return_value.debug = True
            with self.assertRaises(ValueError):
                Utils.add_content_at_indent(5, 4, "inserted", content)
            # The log.error is called by the Log class
            mock_log_err.assert_called()

    def test_add_content_at_indent_invalid_debug(self):
        content = "line1"
        with patch('xtracto.core.config.Config') as mock_config, \
                patch('xtracto.core.logging.Log.error') as mock_log, \
                patch('xtracto.core.logging.Log.debug') as mock_debug:  # Mock Log.debug too
            mock_config.return_value.debug = True
            mock_config.return_value.log_level = "info"  # Must be a string
            with self.assertRaises(ValueError):
                Utils.add_content_at_indent(5, 4, "inserted", content)
            mock_log.assert_called()

    def test_get_project_root_fail(self):
        # We need to ensure Log.critical doesn't crash
        with patch("os.path.exists", return_value=False), \
                patch('xtracto.Log.critical'), \
                patch('xtracto.Log.debug'), \
                patch('xtracto.Config') as mock_config, \
                self.assertRaises(FileNotFoundError):
            mock_config.return_value.debug = True
            Utils.get_project_root()

    def test_layout_exists(self):
        with patch('xtracto.core.config.Config') as mock_config, \
                patch("os.path.exists", return_value=True):
            mock_config.return_value.project_root = self.test_dir
            self.assertTrue(Utils.layout_exists())

    def test_page_exists(self):
        with patch('xtracto.core.config.Config') as mock_config, \
                patch("os.path.exists", return_value=True):
            mock_config.return_value.pages_root = self.test_dir
            self.assertTrue(Utils.page_exists("somepage"))


class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_env_fm")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        # Mock Config to return our test dir as root
        self.config_patcher = patch('xtracto.core.config.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.return_value.module_root = self.test_dir
        self.mock_config.return_value.pages_root = self.test_dir

    def tearDown(self):
        self.config_patcher.stop()
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_path_traversal(self):
        with patch('xtracto.core.logging.XtractoLogger.critical') as mock_log:
            result = FileManager().get_file_if_valid("../../../etc/passwd")
            self.assertEqual(result, "")
            mock_log.assert_called()

    def test_path_traversal_drive(self):
        with patch('os.path.commonpath', side_effect=ValueError), \
                patch('xtracto.core.logging.XtractoLogger.critical') as mock_log:
            result = FileManager().get_file_if_valid("C:/windows/system32")
            self.assertEqual(result, "")
            mock_log.assert_called()

    def test_file_not_found(self):
        with patch('xtracto.core.logging.XtractoLogger.warning') as mock_log:
            result = FileManager().get_file_if_valid("non_existent.txt")
            self.assertEqual(result, "")
            mock_log.assert_called()

    def test_invalid_pypx(self):
        with open("bad.pypx", "w") as f:
            f.write("[[")  # Unbalanced
        with patch('xtracto.core.logging.XtractoLogger.error') as mock_log:
            # FileManager calls Parser, Parser calls Pypx which raises SyntaxError, FileManager catches generic Exception (WAIT, FileManager catches Exception for parsing pypx)
            # Actually Pypx raises SyntaxError.
            # Let's verify FileManager catches it.
            result = FileManager().get_file_if_valid("bad.pypx")
            self.assertEqual(result, "")
            mock_log.assert_called()

    def test_read_file_error(self):
        with open("test.txt", "w") as f:
            f.write("content")
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Read error")
            with patch('xtracto.core.logging.XtractoLogger.error') as mock_log:
                result = FileManager().get_file_if_valid("test.txt")
                self.assertEqual(result, "")
                mock_log.assert_called()


class TestParserExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_env_parser")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        os.makedirs(os.path.join(self.test_dir, "build"))
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        with open("xtracto.config.py", "w") as f:
            f.write("build_dir = 'build'")

    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_render_error(self):
        parser = Parser(content="test")
        with patch("jinja2.Environment.from_string", side_effect=Exception("Jinja Error")), \
                patch('xtracto.core.logging.XtractoLogger.error') as mock_log:
            parser.render()
            mock_log.assert_called()
            self.assertEqual(parser.html_content, parser.template_string)

    def test_production_build_load(self):
        # Create a build file
        with open("build/page.html", "w") as f:
            f.write("<h1>Built</h1>")

        # Mock Config to return production=True
        with patch('xtracto.Config') as mock_config:
            mock_config.return_value.production = True
            mock_config.return_value.build_dir = os.path.abspath("build")

            parser = Parser(path="page.pypx")
            self.assertEqual(parser.template_string, "<h1>Built</h1>")

    def test_load_tailwind(self):
        # Test requires a proper test environment
        import tempfile
        import shutil
        
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        try:
            os.chdir(test_dir)
            # Create minimal config with reparse_tailwind enabled
            with open("xtracto.config.py", "w") as f:
                f.write("pages_dir = 'pages'\nmodules_dir = 'components'\nreparse_tailwind = True\n")
            os.makedirs("pages", exist_ok=True)
            os.makedirs("components", exist_ok=True)
            
            # Patch Tailwind where it's used (in the xtracto module)
            with patch('xtracto.Tailwind') as MockTailwind:
                MockTailwind.return_value.generate.return_value = "/*tailwind-css*/"

                # Create a parser
                parser = Parser(content="div")
                
                # Set html_content directly with the placeholder (simulating what would happen
                # if the template contained the literal placeholder text)
                parser.html_content = "<style>{{generated_tailwind}}</style><div>content</div>"
                
                # Call _load_tailwind directly
                # parser._load_tailwind()
                
                # The tailwind should have been called and replaced the placeholder
                parser.render()
                print("OUTPUT")
                print(parser.html_content)
                print("END OUTPUT")
                self.assertIn("/*tailwind-css*/", parser.html_content)
                self.assertNotIn("{{generated_tailwind}}", parser.html_content)
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir)

    def test_load_tailwind_empty(self):
        # Test requires a proper test environment
        import tempfile
        import shutil
        
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        try:
            os.chdir(test_dir)
            # Create minimal config
            with open("xtracto.config.py", "w") as f:
                f.write("pages_dir = 'pages'\nmodules_dir = 'components'\nreparse_tailwind = True\n")
            os.makedirs("pages", exist_ok=True)
            os.makedirs("components", exist_ok=True)
            
            with patch('pytailwind.Tailwind') as MockTailwind:
                MockTailwind.return_value.generate.return_value = ""  # Empty

                parser = Parser(content="div")
                parser.render()
                # Content should still contain div (template_string) since no tailwind placeholder
                self.assertIn("div", parser.html_content)
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir)


class TestPypxExtended(unittest.TestCase):
    def test_unbalanced_groups(self):
        parser = Pypx(content="[[ test")
        with self.assertRaises(SyntaxError):
            parser.parse()

    def test_layout_no_children(self):
        # This test verifies that a warning is logged when layout doesn't have {{children}}
        # We need to set up a proper test environment
        import tempfile
        import shutil
        
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        try:
            os.chdir(test_dir)
            # Create minimal config
            with open("xtracto.config.py", "w") as f:
                f.write("pages_dir = 'pages'\nmodules_dir = 'components'\n")
            os.makedirs("pages", exist_ok=True)
            os.makedirs("components", exist_ok=True)
            
            # Create layout without {{children}} placeholder
            with open("pages/_layout.pypx", "w") as f:
                f.write("html\n    body\n        No children placeholder")
            
            # Capture warning
            with patch('xtracto.log.warn') as mock_warn:
                parser = Pypx(content="content")
                parser.use_layout()
                mock_warn.assert_called_with("Layout file does not contain {{children}} placeholder")
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir)

    def test_import_recursion(self):
        # This test verifies circular import detection
        # The error is logged to the global log, which is a module-level XtractoLogger instance
        import tempfile
        import shutil
        
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        
        try:
            os.chdir(test_dir)
            # Create minimal config
            with open("xtracto.config.py", "w") as f:
                f.write("pages_dir = 'pages'\nmodules_dir = 'components'\n")
            os.makedirs("pages", exist_ok=True)
            os.makedirs("components", exist_ok=True)
            
            # Create circular import files
            with open("components/a.pypx", "w") as f:
                f.write("[[b.pypx]]")
            with open("components/b.pypx", "w") as f:
                f.write("[[a.pypx]]")
            
            # Parse - should hit recursion limit but not crash
            parser = Pypx(content="[[a.pypx]]")
            # This should complete without hanging or crashing
            # The recursion limit is 100, so it will eventually stop
            result = parser.do_imports("[[a.pypx]]")
            # Just verify it completed (didn't hang)
            self.assertIsNotNone(result)
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir)

    def test_make_groups_valid_multiline(self):
        # Test multiline
        content = "div\n {{ \n var \n }}"
        parser = Pypx(content=content)
        parser.make_groups_valid()
        # Check that #&N# is inserted
        self.assertTrue(any("#&N#" in line for line in parser.parsing))


class TestLog(unittest.TestCase):
    def test_logging(self):
        # Patch Config to prevent it from failing and causing recursion
        with patch('xtracto.core.logging.Log.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with patch('requestez.helpers.get_logger') as mock_ez_logger:
                mock_ez_logger.return_value = mock_logger

                # Test that Log methods work without crashing
                # The new Log class has fallback to new logger
                Log.critical("msg")
                Log.error("msg")
                Log.warn("msg")
                Log.info("msg")
                Log.debug("msg")
                Log.xtracto_initiated()


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_env_builder")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create a sample project structure
        os.makedirs("pages/sub")
        with open("pages/index.pypx", "w") as f:
            f.write("h1\n Index")
        with open("pages/sub/about.pypx", "w") as f:
            f.write("h1\n About")
        with open("pages/_layout.pypx", "w") as f:
            f.write("layout")

    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_build_process(self):
        # Create config file for this test environment
        with open("xtracto.config.py", "w") as f:
            f.write("pages_dir = 'pages'\nmodules_dir = 'components'\nbuild_dir = 'build'\n")
        os.makedirs("components", exist_ok=True)

        builder = Builder()
        builder.build()

        self.assertTrue(os.path.exists("build/index.html"))
        self.assertTrue(os.path.exists("build/sub/about.html"))
        self.assertFalse(os.path.exists("build/_layout.html"))


if __name__ == "__main__":
    unittest.main()
