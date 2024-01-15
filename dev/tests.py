import unittest as _unittest
from dev import *


class TestInsertUtil(_unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestInsertUtil, self).__init__(*args, **kwargs)
        self.initial_file_content = "Line 1\nLine 2\nLine 3"

    def test_add_content_at_indent_same_depth(self):
        expected_result = "Line 1\n    New content\nLine 2\nLine 3"
        result = Utils.add_content_at_indent(2, 4, "New content", self.initial_file_content)
        self.assertEqual(result, expected_result)

    def test_add_content_at_indent_greater_depth(self):
        expected_result = "Line 1\n    New content\nLine 2\nLine 3"
        result = Utils.add_content_at_indent(2, 4, "New content", self.initial_file_content)
        self.assertEqual(result, expected_result)

    def test_add_content_at_indent_lower_depth(self):
        expected_result = "New content\nLine 1\nLine 2\nLine 3"
        result = Utils.add_content_at_indent(1, 0, "New content", self.initial_file_content)
        self.assertEqual(result, expected_result)

    def test_add_content_at_indent_invalid_line_number(self):
        with self.assertRaises(ValueError):
            Utils.add_content_at_indent(0, 4, "New content", self.initial_file_content)


class TestLogger(_unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestLogger, self).__init__(*args, **kwargs)
        self.test_content = "Test Logger Printing"

    def test_acritical(self):
        Log.critical(self.test_content)

    def test_berror(self):
        Log.error(self.test_content)

    def test_cwarn(self):
        Log.warn(self.test_content)

    def test_dinfo(self):
        Log.info(self.test_content)

    def test_edebug(self):
        Log.debug(self.test_content)


class TestValiableRetriver(_unittest.TestCase):
    def test_variable_retriving(self):
        test = "Test Value"
        value = Utils.get_variable_value_from_nearest_frame("test")
        self.assertEqual(test, value)


class TestFileValidator(_unittest.TestCase):
    def test_js(self):
        file = FileManager.get_file_if_valid("./test/validjs.js")
        with open("./test/validjs.js") as f:
            cont = f.read()
        self.assertEqual(file, cont)

    def test_invalid_js(self):
        file = FileManager.get_file_if_valid("./test/invalidjs.js")
        self.assertEqual(file, "")

    def test_css(self):
        file = FileManager.get_file_if_valid("./test/valid.css")

    def test_invalid_css(self):
        file = FileManager.get_file_if_valid("./test/invalid.css")


class TestParser(_unittest.TestCase):
    def test_basic(self):
        Parser(path="./test/basic.pypx")

    def test_basic2(self):
        Parser(path="./test/basic2.pypx")

    def test_component_parsing(self):
        _ = Parser(path="./test/component.pypx")
        buttonText = "k5"
        _.render()
        log.info(_.html_content)

    def test_import_regex(self):
        Pypx().do_imports(content="[[./test/component.pypx||parms=xyz||]]")
        Pypx().do_imports(content="[[./test/component.pypx]]")
        Pypx().do_imports(content="""
        [[./test/component.pypx||
        parms=xyz
        ||
        ]]""")
        Pypx().do_imports(content="""
                [[./test/component.pypx||
                parms=xyz
                ||param2=koak|#|#||
                ]]""")

    def test_import(self):
        _ = Parser(path="./test/import.pypx")
        _.render()
        log.info(_.html_content)

    def test_bundle(self):
        cont = "[{./test/validjs.js}]"
        cont2 = """
        html
            [{./test/validjs.js}]
            [{./test/valid.css}]
            script
                ;;src=[{./test/validjs2.js}];;
        """
        Pypx().generate_bundle(content=cont, path_name="./test/bundletest")
        Pypx().generate_bundle(content=cont2, path_name="./test/bundletest2")
        log.info(Parser(path="./test/bundletest3.pypx").html_content)


if __name__ == '__main__':
    _unittest.main()
