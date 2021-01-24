#!/usr/bin/python3

"""Unit tests for the generic code implementation"""

import unittest
import sys
import pickle
from importlib.machinery import ModuleSpec
from pyhp.compiler import generic


class TestCode(unittest.TestCase):
    """Test the generic code implementation"""
    def test_constants(self) -> None:
        """test the module level constants"""
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = generic.GenericCode([], spec)
        variables = {}
        list(code.execute(variables))   # modifies variables
        self.assertEqual(
            variables,
            {
                "__name__": "test",
                "__loader__": None,
                "__file__": "this test",
                "__path__": None,
                "__package__": "",
                "__cached__": None,
                "__spec__": spec
            }
        )

    def test_execute(self) -> None:
        """test the execution"""
        code = generic.GenericCode(
            [
                "1",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("__main__", None, origin=None, is_package=False)
        )
        numbers = []
        variables = {"numbers": numbers}
        for number in code.execute(variables):
            numbers.append(number)
        self.assertEqual(numbers, ["1", "2", "3", "4", "5"])

    def test_pickle(self) -> None:
        """test if generic code objects are pickleable"""
        code = generic.GenericCode(
            [
                "1",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("test", None, origin="this test", is_package=False)
        )
        code2 = pickle.loads(pickle.dumps(code))
        self.assertEqual(code2.sections, code.sections)
        self.assertEqual(code2.spec, code.spec)

    def test_equal(self) -> None:
        """test if equality between generic code objetcs works"""
        code = generic.GenericCode(
            [
                "1",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("test", None, origin="this test", is_package=False)
        )

        code2 = generic.GenericCode(
            [
                "1",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("test", None, origin="this test", is_package=False)
        )

        code3 = generic.GenericCode(
            [
                "X",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("test", None, origin="this test", is_package=False)
        )

        code4 = generic.GenericCode(
            [
                "1",
                "2",
                compile("numbers.append('3')", "<string>", "exec"),
                "4",
                compile("numbers.append('5')", "<string>", "exec"),
            ],
            ModuleSpec("X", None, origin="this test", is_package=False)
        )

        self.assertEqual(code, code2)
        self.assertNotEqual(code, code3)
        self.assertNotEqual(code, code4)
        self.assertNotEqual(code3, code4)


class TestBuilder(unittest.TestCase):
    """Test the generic code builder"""
    def test_build(self) -> None:
        """test the building of a generic code object"""
        builder = generic.GenericCodeBuilder(-1)
        builder.add_text("1", 1, 0)
        builder.add_code("numbers.append('2')", 2, 0)
        builder.add_code("numbers.append('3')", 3, 0)
        builder.add_text("4", 4, 0)
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        code2 = generic.GenericCode(
            (
                "1",
                compile("numbers.append('2')", "this test", "exec"),
                compile("numbers.append('3')", "this test", "exec"),
                "4"
            ),
            spec
        )
        self.assertEqual(code, code2)

    def test_copy(self) -> None:
        """test GenericCodeBuilder.copy"""
        builder = generic.GenericCodeBuilder(-1)
        builder.add_text("1", 1, 0)
        builder.add_code("numbers.append('2')", 2, 0)
        builder.add_code("numbers.append('3')", 3, 0)
        builder.add_text("4", 4, 0)
        builder2 = builder.copy()
        self.assertEqual(builder.sections, builder2.sections)
        builder2.add_text("test", 5, 0)
        self.assertNotEqual(builder.sections, builder2.sections)

    def test_empty(self) -> None:
        """test if an empty builder works"""
        builder = generic.GenericCodeBuilder(-1)
        code = builder.code(ModuleSpec("test", None, origin="this test", is_package=False))
        self.assertEqual(list(code.execute({})), [])

    def test_lineno(self) -> None:
        """test if line numbers are set correctly"""
        builder = generic.GenericCodeBuilder(-1)
        builder.add_code("x", 1, 99)    # offset starts with 0
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        try:
            list(code.execute({}))
        except NameError:
            _, _, traceback = sys.exc_info()
            self.assertEqual(traceback.tb_next.tb_next.tb_frame.f_code.co_filename, spec.origin)
            self.assertEqual(traceback.tb_next.tb_next.tb_frame.f_lineno, 100)
        else:
            raise RuntimeError("bad generic code executed without error")
