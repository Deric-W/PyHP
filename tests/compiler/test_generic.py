#!/usr/bin/python3

"""Unit tests for the generic code implementation"""

import unittest
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


class TestBuilder(unittest.TestCase):
    """Test the generic code builder"""
    def test_build(self) -> None:
        """test the building of a generic code object"""
        builder = generic.GenericCodeBuilder(0)
        builder.add_text("1", 0)
        builder.add_code("numbers.append('2')", 0)
        builder.add_code("numbers.append('3')", 0)
        builder.add_text("4", 0)
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        self.assertEqual(spec, code.spec)
        self.assertEqual(
            code.sections,
            (
                "1",
                compile("numbers.append('2')", "this test", "exec"),
                compile("numbers.append('3')", "this test", "exec"),
                "4"
            )
        )

    def test_copy(self) -> None:
        """test GenericCodeBuilder.copy"""
        builder = generic.GenericCodeBuilder(0)
        builder.add_text("1", 0)
        builder.add_code("numbers.append('2')", 0)
        builder.add_code("numbers.append('3')", 0)
        builder.add_text("4", 0)
        builder2 = builder.copy()
        self.assertEqual(builder.sections, builder2.sections)
        builder2.add_text("test", 0)
        self.assertNotEqual(builder.sections, builder2.sections)
