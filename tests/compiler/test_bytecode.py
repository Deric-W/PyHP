#!/usr/bin/python3

"""Unit tests for the bytecode code implementation"""

import unittest
import sys
import ast
import pickle
from importlib.machinery import ModuleSpec
from pyhp.compiler import bytecode


TEST_AST = ast.Module(
    body=[
        ast.FunctionDef(
            name="<module>",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=ast.parse(
                "def test():\n yield '1'\n numbers.append('2')\n numbers.append('3')\n yield '4'",
                mode="exec"
            ).body[0].body,
            decorator_list=[],
            lineno=1,
            col_offset=0
        )
    ],
    type_ignores=[]
)


class TestCode(unittest.TestCase):
    """Test the bytecode code implementation"""
    def test_constants(self) -> None:
        """test the module level constants"""
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = bytecode.ByteCode(compile(TEST_AST, spec.origin, "exec"), spec)
        variables = {"numbers": []}
        list(code.execute(variables))   # modifies variables
        variables.pop("<module>")
        variables.pop("numbers")
        variables.pop("__builtins__")
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
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = bytecode.ByteCode(compile(TEST_AST, spec.origin, "exec"), spec)
        numbers = []
        variables = {"numbers": numbers}
        for number in code.execute(variables):
            numbers.append(number)
        self.assertEqual(numbers, ["1", "2", "3", "4"])

    def test_pickle(self) -> None:
        """test if generic code objects are pickleable"""
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = bytecode.ByteCode(compile(TEST_AST, spec.origin, "exec"), spec)
        code2 = pickle.loads(pickle.dumps(code))
        self.assertEqual(code2.code, code.code)
        self.assertEqual(code2.spec, code.spec)

    def test_equal(self) -> None:
        """test if equality between generic code objetcs works"""
        builder = bytecode.ByteCodeBuilder(-1)
        builder.add_code("print(1)", 0)
        builder.add_text("X", 0)
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        code2 = builder.code(spec)
        code3 = builder.code(ModuleSpec("X", None, origin="this test", is_package=False))
        builder.add_text("Y", 0)
        code4 = builder.code(spec)
        self.assertEqual(code, code2)
        self.assertNotEqual(code, code3)
        self.assertNotEqual(code, code4)


class TestBuilder(unittest.TestCase):
    """Test the generic code builder"""
    def test_build(self) -> None:
        """test the building of a generic code object"""
        builder = bytecode.ByteCodeBuilder(-1)
        builder.add_text("1", 0)
        builder.add_code("numbers.append('2')", 1)
        builder.add_code("numbers.append('3')", 2)
        builder.add_text("4", 3)
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        code2 = bytecode.ByteCode(
            compile(TEST_AST, spec.origin, "exec"),
            spec
        )
        self.assertEqual(code, code2)

    def test_copy(self) -> None:
        """test GenericCodeBuilder.copy"""
        builder = bytecode.ByteCodeBuilder(-1)
        builder.add_text("1", 0)
        builder.add_code("numbers.append('2')", 1)
        builder.add_code("numbers.append('3')", 2)
        builder.add_text("4", 3)
        builder2 = builder.copy()
        self.assertEqual(builder.nodes, builder2.nodes)
        builder2.add_text("test", 3)
        self.assertNotEqual(builder.nodes, builder2.nodes)

    def test_empty(self) -> None:
        """test if an empty builder works"""
        builder = bytecode.ByteCodeBuilder(-1)
        code = builder.code(ModuleSpec("test", None, origin="this test", is_package=False))
        self.assertEqual(list(code.execute({})), [])

    def test_lineno(self) -> None:
        """test if line numbers are set correctly"""
        builder = bytecode.ByteCodeBuilder(-1)
        builder.add_code("x", 99)    # offset starts with 0
        spec = ModuleSpec("test", None, origin="this test", is_package=False)
        code = builder.code(spec)
        try:
            list(code.execute({}))
        except NameError:
            _, _, traceback = sys.exc_info()
            self.assertEqual(traceback.tb_next.tb_frame.f_code.co_filename, spec.origin)
            self.assertEqual(traceback.tb_next.tb_frame.f_lineno, 100)
        else:
            raise RuntimeError("bad bytecode executed without error")

    def test_error_lineno(self) -> None:
        """test if the line numbers of syntax errors are correct"""
        builder = bytecode.ByteCodeBuilder(-1)
        try:
            builder.add_code("9***9", 99)    # offset starts with 0
        except SyntaxError as e:
            self.assertEqual(e.lineno, 100)
        else:
            raise RuntimeError("bad syntax compiled without error")

    def test_eq(self) -> None:
        """test ByteCodeBuilder.__eq__"""
        builders = [
            bytecode.ByteCodeBuilder(-1),
            bytecode.ByteCodeBuilder(0),
            bytecode.ByteCodeBuilder(-1),
            bytecode.ByteCodeBuilder(-1)
        ]
        builders[2].add_text("test", 0)
        builders[3].add_text("abc", 0)
        for index, builder in enumerate(builders):
            self.assertEqual(
                [builder],
                [b for b in builders if b == builder]
            )
