import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.function_generator import FunctionTACGenerator
from tac.instruction import (
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
    CommentInstruction,
    LabelInstruction
)
from AST.ast_nodes import (
    FunctionDeclaration,
    CallExpression,
    ReturnStatement,
    Parameter,
    Block,
    TypeNode,
    Variable,
    Literal,
    Type
)


class TestFunctionTACGenerator(unittest.TestCase):
    """Test suite for FunctionTACGenerator (Part 4/4)."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = FunctionTACGenerator()

    def test_simple_function_declaration(self):
        """Test TAC generation for simple function declaration."""
        # func add(a: int, b: int): int { return a + b; }
        param_a = Parameter("a", TypeNode("int"))
        param_b = Parameter("b", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(42, Type.INTEGER))  # Simplified for test
        body = Block([return_stmt])

        func_decl = FunctionDeclaration(
            name="add",
            parameters=[param_a, param_b],
            return_type=TypeNode("int"),
            body=body
        )

        result = self.generator.visit_FunctionDeclaration(func_decl)
        instructions = self.generator.get_instructions()

        # Verify function structure
        self.assertIsNone(result)  # Function declarations don't return values
        self.assertTrue(len(instructions) >= 4)  # At least prologue, label, return, epilogue

        # Check for required instructions
        instruction_types = [type(instr).__name__ for instr in instructions]
        self.assertIn('CommentInstruction', instruction_types)
        self.assertIn('BeginFuncInstruction', instruction_types)
        self.assertIn('LabelInstruction', instruction_types)
        self.assertIn('ReturnInstruction', instruction_types)
        self.assertIn('EndFuncInstruction', instruction_types)

    def test_function_call_with_parameters(self):
        """Test TAC generation for function call with parameters."""
        # call add(5, 3)
        arg1 = Literal(5, Type.INTEGER)
        arg2 = Literal(3, Type.INTEGER)
        callee = Variable("add")

        call_expr = CallExpression(callee, [arg1, arg2])

        # First register the function
        param_a = Parameter("a", TypeNode("int"))
        param_b = Parameter("b", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(42, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("add", [param_a, param_b], TypeNode("int"), body)
        self.generator.visit_FunctionDeclaration(func_decl)

        # Clear instructions and test call
        self.generator.clear_instructions()
        result = self.generator.visit_CallExpression(call_expr)

        instructions = self.generator.get_instructions()

        # Should return a temporary for the result
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith('t'))

        # Check instruction sequence
        push_count = sum(1 for instr in instructions if isinstance(instr, PushParamInstruction))
        call_count = sum(1 for instr in instructions if isinstance(instr, CallInstruction))
        pop_count = sum(1 for instr in instructions if isinstance(instr, PopParamsInstruction))

        self.assertEqual(push_count, 2)  # Two parameters
        self.assertEqual(call_count, 1)  # One call
        self.assertEqual(pop_count, 1)   # One pop params

    def test_void_function_call(self):
        """Test TAC generation for void function call."""
        # First register a void function
        param_x = Parameter("x", TypeNode("int"))
        body = Block([])  # Empty body
        func_decl = FunctionDeclaration("printNum", [param_x], TypeNode("void"), body)
        self.generator.visit_FunctionDeclaration(func_decl)

        # Clear and test call
        self.generator.clear_instructions()

        arg = Literal(42, Type.INTEGER)
        callee = Variable("printNum")
        call_expr = CallExpression(callee, [arg])

        result = self.generator.visit_CallExpression(call_expr)

        # Void functions should not return a temporary
        self.assertIsNone(result)

    def test_return_statement_with_value(self):
        """Test TAC generation for return statement with value."""
        # return 42;
        return_value = Literal(42, Type.INTEGER)
        return_stmt = ReturnStatement(return_value)

        result = self.generator.visit_ReturnStatement(return_stmt)
        instructions = self.generator.get_instructions()

        self.assertIsNone(result)  # Return statements don't produce values
        self.assertEqual(len(instructions), 1)
        self.assertIsInstance(instructions[0], ReturnInstruction)
        self.assertIsNotNone(instructions[0].value)

    def test_return_statement_void(self):
        """Test TAC generation for void return statement."""
        # return;
        return_stmt = ReturnStatement(None)

        result = self.generator.visit_ReturnStatement(return_stmt)
        instructions = self.generator.get_instructions()

        self.assertIsNone(result)
        self.assertEqual(len(instructions), 1)
        self.assertIsInstance(instructions[0], ReturnInstruction)
        self.assertIsNone(instructions[0].value)

    def test_function_with_multiple_parameters(self):
        """Test function declaration with multiple parameters."""
        # func calculate(a: int, b: int, c: float, d: boolean): float { return 0.0; }
        params = [
            Parameter("a", TypeNode("int")),
            Parameter("b", TypeNode("int")),
            Parameter("c", TypeNode("float")),
            Parameter("d", TypeNode("boolean"))
        ]
        return_stmt = ReturnStatement(Literal(0.0, Type.FLOAT))
        body = Block([return_stmt])

        func_decl = FunctionDeclaration("calculate", params, TypeNode("float"), body)

        self.generator.visit_FunctionDeclaration(func_decl)
        instructions = self.generator.get_instructions()

        # Find BeginFunc instruction
        begin_func = None
        for instr in instructions:
            if isinstance(instr, BeginFuncInstruction):
                begin_func = instr
                break

        self.assertIsNotNone(begin_func)
        self.assertEqual(begin_func.name, "calculate")
        self.assertEqual(begin_func.param_count, 4)

    def test_function_activation_record_management(self):
        """Test that activation records are properly managed."""
        # Test nested function calls and scope management
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])

        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        # Check initial state
        self.assertIsNone(self.generator.address_manager.get_current_function())

        # Visit function
        self.generator.visit_FunctionDeclaration(func_decl)

        # Should return to initial state
        self.assertIsNone(self.generator.address_manager.get_current_function())

    def test_function_info_registry(self):
        """Test function information registry."""
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])

        func_decl = FunctionDeclaration("testFunc", [param], TypeNode("int"), body)
        self.generator.visit_FunctionDeclaration(func_decl)

        # Get function info
        info = self.generator.get_function_info("testFunc")
        self.assertIsNotNone(info)
        self.assertEqual(info['name'], "testFunc")
        self.assertEqual(info['parameter_count'], 1)
        self.assertEqual(info['parameters'], ['x'])
        self.assertEqual(info['return_type'], "int")
        self.assertTrue(info['has_return_value'])

    def test_error_handling_wrong_parameter_count(self):
        """Test error handling for incorrect parameter count."""
        # Register function with 2 parameters
        params = [Parameter("a", TypeNode("int")), Parameter("b", TypeNode("int"))]
        body = Block([ReturnStatement(Literal(0, Type.INTEGER))])
        func_decl = FunctionDeclaration("add", params, TypeNode("int"), body)
        self.generator.visit_FunctionDeclaration(func_decl)

        # Try to call with wrong number of arguments
        callee = Variable("add")
        call_expr = CallExpression(callee, [Literal(5, Type.INTEGER)])  # Only 1 arg instead of 2

        with self.assertRaises(Exception):  # Should raise TACGenerationError
            self.generator.visit_CallExpression(call_expr)

    def test_default_return_values(self):
        """Test default return value generation."""
        self.assertEqual(self.generator._get_default_value("int"), "0")
        self.assertEqual(self.generator._get_default_value("float"), "0.0")
        self.assertEqual(self.generator._get_default_value("boolean"), "false")
        self.assertEqual(self.generator._get_default_value("string"), '""')
        self.assertEqual(self.generator._get_default_value("unknown"), "0")

    def test_program_tac_generation(self):
        """Test TAC generation for entire program."""
        # Create a simple program with function
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(42, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("main", [param], TypeNode("int"), body)

        # Simulate program node
        class MockProgram:
            def __init__(self, statements):
                self.statements = statements

        program = MockProgram([func_decl])
        tac_lines = self.generator.generate_program_tac(program)

        self.assertIsInstance(tac_lines, list)
        self.assertTrue(len(tac_lines) > 0)
        self.assertTrue(any("BeginFunc main" in line for line in tac_lines))
        self.assertTrue(any("EndFunc main" in line for line in tac_lines))

    def test_recursive_function_handling(self):
        """Test handling of recursive function calls."""
        # func factorial(n: int): int {
        #   if (n <= 1) return 1;
        #   return n * factorial(n - 1);
        # }
        param_n = Parameter("n", TypeNode("int"))
        # Simplified recursive call for test
        recursive_call = CallExpression(Variable("factorial"), [Literal(1, Type.INTEGER)])
        return_stmt = ReturnStatement(recursive_call)
        body = Block([return_stmt])

        func_decl = FunctionDeclaration("factorial", [param_n], TypeNode("int"), body)

        # Should handle registration and call without issues
        self.generator.visit_FunctionDeclaration(func_decl)
        instructions = self.generator.get_instructions()

        # Should contain function setup and call instructions
        instruction_types = [type(instr).__name__ for instr in instructions]
        self.assertIn('BeginFuncInstruction', instruction_types)
        self.assertIn('CallInstruction', instruction_types)
        self.assertIn('EndFuncInstruction', instruction_types)


class TestFunctionIntegration(unittest.TestCase):
    """Integration tests for function TAC generation with other components."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = FunctionTACGenerator()

    def test_generator_statistics(self):
        """Test statistics gathering from function generator."""
        # Create simple function
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        self.generator.visit_FunctionDeclaration(func_decl)
        stats = self.generator.get_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn('instructions_generated', stats)
        self.assertIn('temporary_stats', stats)
        self.assertIn('address_stats', stats)
        self.assertIn('label_stats', stats)
        self.assertGreater(stats['instructions_generated'], 0)

    def test_generator_reset(self):
        """Test generator reset functionality."""
        # Generate some instructions
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        self.generator.visit_FunctionDeclaration(func_decl)
        self.assertGreater(len(self.generator.get_instructions()), 0)

        # Reset and verify clean state
        self.generator.reset()
        self.assertEqual(len(self.generator.get_instructions()), 0)
        self.assertEqual(len(self.generator._function_registry), 0)


if __name__ == '__main__':
    unittest.main()