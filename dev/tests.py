import unittest as _unittest
from dev import Pypx, Parser, Utils, Log, FileManager


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
        file = FileManager.get_file_if_valid("validjs.js")
        with open("validjs.js") as f:
            cont = f.read()
        self.assertEqual(file, cont)

    def test_invalid_js(self):
        file = FileManager.get_file_if_valid("invalidjs.js")
        self.assertEqual(file, "")

    def test_css(self):
        FileManager.get_file_if_valid("valid.css")

    def test_invalid_css(self):
        FileManager.get_file_if_valid("invalid.css")


class TestParser(_unittest.TestCase):
    def test_basic(self):
        Parser(path="basic.pypx")

    def test_basic2(self):
        Parser(path="basic2.pypx")

    def test_component_parsing(self):
        _ = Parser(path="componentimport.pypx")
        buttonText = "k5"
        _.render()
        self.assertEqual(_.html_content, """<html><head><title>test component import</title></head><body><button type="submit" disabled>k5</button><input type=text /></input><div>other div</div><div class="test">This is The components div<br>which can be customized</div></body></html>""")
        Log.debug("VARIABLE VALUE: \""+buttonText + "\" HAS BEEN TESTED TO BE IMPORTED")

    def test_import_regex(self):
        r1 = Pypx().do_imports(content="[[component.pypx||parms=xyz||]]")
        r2 = Pypx().do_imports(content="[[component.pypx]]")
        r3 = Pypx().do_imports(content="""
        [[component.pypx
        ||
        parms=xyz
        ||
        ]]""")
        r4 = Pypx().do_imports(content="""
                [[component.pypx||
                parms=xyz
                ||param2=koak|#|#||
                ]]""")
        self.assertEqual(r1, r2)
        self.assertEqual(r3, r4.replace("\n        ", "\n"))

    def test_import(self):
        _ = Parser(path="import.pypx")
        _.render()
        self.assertEqual(_.html_content, """<html><head><title>testing import feature</title><script>function test() {
    return "null";
}
</div></body></html>""")

    def test_bundle(self):
        cont = "[{validjs.js}]"
        cont2 = """
        html
            [{validjs.js}]
            [{valid.css}]
            script
                ;;src=[{validjs2.js}];;
        """
        Pypx().generate_bundle(content=cont, path_name="bundletest")
        Pypx().generate_bundle(content=cont2, path_name="bundletest2")
        self.assertEqual(Parser(path="bundletest3.pypx").html_content, """<html>/bundletest3.pypx.b6d5f4c7.css<script src=/bundletest3.pypx.db984605.js /></script></html>""")


if __name__ == '__main__':
    _unittest.main()
