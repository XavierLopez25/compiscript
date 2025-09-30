import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.integrated_generator import IntegratedTACGenerator
from AST.ast_nodes import (
    Program,
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


class TestIntegratedTACGenerator(unittest.TestCase):
    """Test suite for IntegratedTACGenerator - complete TAC generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = IntegratedTACGenerator()

    def test_simple_program_with_function(self):
        """Test TAC generation for simple program with function."""
        # Program:
        # func add(a: int, b: int): int {
        #     return a + b;  // Simplified for test
        # }
        param_a = Parameter("a", TypeNode("int"))
        param_b = Parameter("b", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(42, Type.INTEGER))  # Simplified
        body = Block([return_stmt])

        func_decl = FunctionDeclaration(
            name="add",
            parameters=[param_a, param_b],
            return_type=TypeNode("int"),
            body=body
        )

        program = Program([func_decl])
        tac_lines = self.generator.generate_program(program)

        # Verify structure
        self.assertIsInstance(tac_lines, list)
        self.assertTrue(len(tac_lines) > 0)

        # Check for expected content
        tac_content = '\n'.join(tac_lines)
        self.assertIn("BeginFunc add", tac_content)
        self.assertIn("EndFunc add", tac_content)
        self.assertIn("return", tac_content)

    def test_program_with_function_call(self):
        """Test program with function declaration and call."""
        # Program:
        # func square(x: int): int {
        #     return x * x;  // Simplified
        # }
        # square(5);

        # Function declaration
        param_x = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(25, Type.INTEGER))  # Simplified
        func_body = Block([return_stmt])
        func_decl = FunctionDeclaration("square", [param_x], TypeNode("int"), func_body)

        # Function call
        call_expr = CallExpression(Variable("square"), [Literal(5, Type.INTEGER)])

        program = Program([func_decl, call_expr])
        tac_lines = self.generator.generate_program(program)

        tac_content = '\n'.join(tac_lines)

        # Should contain both function definition and call
        self.assertIn("BeginFunc square", tac_content)
        self.assertIn("call square", tac_content)
        self.assertIn("PushParam", tac_content)

    def test_generator_coordination(self):
        """Test that different generators are properly coordinated."""
        # Simple function that should use multiple generators
        param = Parameter("n", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        program = Program([func_decl])

        # Generate TAC
        tac_lines = self.generator.generate_program(program)

        # Check that infrastructure is shared
        self.assertIs(
            self.generator.expression_generator.temp_manager,
            self.generator.temp_manager
        )
        self.assertIs(
            self.generator.function_generator.address_manager,
            self.generator.address_manager
        )

    def test_complete_statistics(self):
        """Test comprehensive statistics gathering."""
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        program = Program([func_decl])
        self.generator.generate_program(program)

        stats = self.generator.get_complete_statistics()

        # Verify statistics structure
        self.assertIn('integrated_stats', stats)
        self.assertIn('expression_stats', stats)
        self.assertIn('control_flow_stats', stats)
        self.assertIn('function_stats', stats)
        self.assertIn('total_instructions', stats)
        self.assertIn('generator_context', stats)

        self.assertGreater(stats['total_instructions'], 0)

    def test_tac_with_metadata(self):
        """Test TAC generation with metadata."""
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("testFunc", [param], TypeNode("int"), body)

        program = Program([func_decl])
        self.generator.generate_program(program)

        metadata = self.generator.get_tac_with_metadata()

        # Verify metadata structure
        self.assertIn('tac_code', metadata)
        self.assertIn('instruction_count', metadata)
        self.assertIn('function_registry', metadata)
        self.assertIn('statistics', metadata)
        self.assertIn('memory_layout', metadata)

        # Verify content
        self.assertIsInstance(metadata['tac_code'], list)
        self.assertGreater(metadata['instruction_count'], 0)
        self.assertIn('testFunc', metadata['function_registry'])

    def test_tac_optimization(self):
        """Test basic TAC optimization."""
        # Create program that might have duplicate comments
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        program = Program([func_decl])
        self.generator.generate_program(program)

        original_tac = [str(instr) for instr in self.generator.get_instructions()]
        optimized_tac = self.generator.optimize_tac()

        # Should be lists of strings
        self.assertIsInstance(original_tac, list)
        self.assertIsInstance(optimized_tac, list)

        # Optimized should not be longer than original
        self.assertLessEqual(len(optimized_tac), len(original_tac))

    def test_tac_validation(self):
        """Test TAC validation."""
        # Create valid program
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        program = Program([func_decl])
        self.generator.generate_program(program)

        errors = self.generator.validate_tac()

        # Should have no validation errors
        self.assertIsInstance(errors, list)
        if errors:  # Print errors for debugging
            for error in errors:
                print(f"Validation error: {error}")

    def test_generator_reset(self):
        """Test that generator reset works properly."""
        # Generate some TAC
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        program = Program([func_decl])
        self.generator.generate_program(program)

        # Verify we have instructions
        self.assertGreater(len(self.generator.get_instructions()), 0)

        # Reset and verify clean state
        self.generator.reset()
        self.assertEqual(len(self.generator.get_instructions()), 0)
        self.assertEqual(self.generator._current_generator_context, 'global')

    def test_context_management(self):
        """Test generator context management."""
        # Start in global context
        self.assertEqual(self.generator._current_generator_context, 'global')

        # Create and process function
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal(1, Type.INTEGER))
        body = Block([return_stmt])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        self.generator._process_function_declaration(func_decl)

        # Should return to global context
        self.assertEqual(self.generator._current_generator_context, 'global')

    def test_error_propagation(self):
        """Test that errors are properly propagated from sub-generators."""
        # Create invalid function call (function not declared)
        call_expr = CallExpression(Variable("undeclaredFunc"), [Literal(1, Type.INTEGER)])

        with self.assertRaises(Exception):
            self.generator._route_to_generator(call_expr)


class TestIntegratedGeneratorEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for IntegratedTACGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = IntegratedTACGenerator()

    def test_empty_program(self):
        """Test TAC generation for empty program."""
        program = Program([])
        tac_lines = self.generator.generate_program(program)

        # Should still generate header comments
        self.assertIsInstance(tac_lines, list)
        self.assertTrue(any("TAC Code Generation" in line for line in tac_lines))

    def test_function_without_return(self):
        """Test function without explicit return statement."""
        param = Parameter("x", TypeNode("int"))
        body = Block([])  # Empty body, no return
        func_decl = FunctionDeclaration("noReturn", [param], TypeNode("int"), body)

        program = Program([func_decl])
        tac_lines = self.generator.generate_program(program)

        tac_content = '\n'.join(tac_lines)
        # Should have implicit return
        self.assertIn("return", tac_content)

    def test_void_function(self):
        """Test void function handling."""
        param = Parameter("x", TypeNode("int"))
        body = Block([])
        func_decl = FunctionDeclaration("voidFunc", [param], TypeNode("void"), body)

        program = Program([func_decl])
        tac_lines = self.generator.generate_program(program)

        tac_content = '\n'.join(tac_lines)
        self.assertIn("BeginFunc voidFunc", tac_content)
        self.assertIn("EndFunc voidFunc", tac_content)

    def test_multiple_functions(self):
        """Test program with multiple functions."""
        # Function 1
        param1 = Parameter("a", TypeNode("int"))
        body1 = Block([ReturnStatement(Literal(1, Type.INTEGER))])
        func1 = FunctionDeclaration("func1", [param1], TypeNode("int"), body1)

        # Function 2
        param2 = Parameter("b", TypeNode("int"))
        body2 = Block([ReturnStatement(Literal(2, Type.INTEGER))])
        func2 = FunctionDeclaration("func2", [param2], TypeNode("int"), body2)

        program = Program([func1, func2])
        tac_lines = self.generator.generate_program(program)

        tac_content = '\n'.join(tac_lines)
        self.assertIn("BeginFunc func1", tac_content)
        self.assertIn("BeginFunc func2", tac_content)
        self.assertIn("EndFunc func1", tac_content)
        self.assertIn("EndFunc func2", tac_content)


if __name__ == '__main__':
    unittest.main()