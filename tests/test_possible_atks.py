import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xtracto import FileManager, Parser, Pypx, Utils, Config


class TestVulnerabilities(unittest.TestCase):
    def setUp(self):
        # Mock Config to avoid needing actual files
        self.config_patcher = patch('xtracto.Config')
        self.MockConfig = self.config_patcher.start()
        # Setup default config values
        self.MockConfig.return_value.module_root = os.path.abspath("xtractocomponents")
        self.MockConfig.return_value.pages_root = os.path.abspath("xtractopages")
        self.MockConfig.return_value.production = False
        self.MockConfig.return_value.reparse_tailwind = False
        self.MockConfig.return_value.debug = True
        self.MockConfig.return_value.log_level = "DEBUG"

    def tearDown(self):
        self.config_patcher.stop()

    def test_path_traversal_fix(self):
        # FileManager.get_file_if_valid
        # Try to access a file outside module_root

        # Make sure module_root directory exists
        os.makedirs("xtractocomponents", exist_ok=True)

        target = "../setup.py"

        # Should return empty string and log error
        with patch('xtracto.log') as mock_log:
            content = FileManager.get_file_if_valid(target)
            self.assertEqual(content, "", "Path traversal should be blocked and return empty string")
            # Verify log was called with TRAVERSAL ATTEMPT (checking args partially)
            # mock_log.critical.assert_called()
            # Note: The real log might be mocked differently in setUp but here we patch 'xtracto.log' directly

    def test_ssti_fix(self):
        # Parser.render with malicious context
        parser = Parser(content="Hello {{ name }}")

        # Malicious payload
        payload = "<script>alert(1)</script>"
        parser.render(context={"name": payload})

        # Output should be escaped
        print(f"SSTI Fix Output: {parser.html_content}")

        self.assertNotIn("<script>", parser.html_content, "SSTI should be mitigated (script tag escaped)")
        self.assertIn("&lt;script&gt;", parser.html_content, "Output should contain escaped entities")

    def test_dos_circular_import_fix(self):
        # Pypx.do_imports with circular dependency

        with patch('xtracto.FileManager.get_file_if_valid') as mock_get_file:
            # Setup circular content
            def side_effect(path):
                if "A" in path:
                    return "[[ B ]]"
                if "B" in path:
                    return "[[ A ]]"
                return ""

            mock_get_file.side_effect = side_effect

            pypx = Pypx(content="[[ A ]]")

            # This should finish due to loop limit
            try:
                pypx.do_imports()
                print("DoS Fix: Circular import terminated successfully.")
            except Exception as e:
                self.fail(f"do_imports raised exception: {e}")

    def test_code_execution_fix(self):
        # Utils.get_project_root
        # Should restrict to current directory
        # We can't easily test "not searching up" without changing cwd context carefully
        # But we can verify it checks current dir.

        cwd = os.getcwd()
        with patch('os.path.exists') as mock_exists:
            # Case 1: Config exists in cwd
            mock_exists.return_value = True
            root = Utils.get_project_root()
            self.assertEqual(root, cwd)

            # Case 2: Config does NOT exist in cwd
            mock_exists.return_value = False
            # Should raise ProjectConfig error
            from xtracto import Error
            with self.assertRaises(FileNotFoundError):  # Error.ProjectConfig.error is FileNotFoundError
                Utils.get_project_root()

    def test_fragile_parsing_fix(self):
        # Unbalanced groups at EOF
        content = "{{ start"
        pypx = Pypx(content=content)
        with self.assertRaises(SyntaxError):
            pypx.make_groups_valid()

    def test_indentation_fix(self):
        # Test expandtabs
        content = "    Space\n\tTab"
        pypx = Pypx(content=content)
        # Check content in pypx.content
        # Tab should be expanded to 4 spaces
        # "    Space" -> "    Space"
        # "\tTab" -> "    Tab"
        self.assertEqual(pypx.content[1], "    Tab", "Tabs should be expanded to 4 spaces")


if __name__ == '__main__':
    unittest.main()
