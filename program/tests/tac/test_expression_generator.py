import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.expression_generator import ExpressionTACGenerator
from tac.base_generator import TACGenerationError
from tac.instruction import (
    AssignInstruction,
    ConditionalGotoInstruction,
    GotoInstruction,
    LabelInstruction,
    ArrayAccessInstruction,
    PropertyAccessInstruction,
    CommentInstruction
)
from AST.ast_nodes import *

class TestExpressionTACGenerator(unittest.TestCase):
    """Test cases for ExpressionTACGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = ExpressionTACGenerator()

    def test_literal_generation(self):
        """Test TAC generation for literals."""
        # Integer literal
        int_literal = Literal(42, Type.INTEGER)
        result = self.generator.visit(int_literal)
        self.assertEqual(result, "42")

        # Float literal
        float_literal = Literal(3.14, Type.FLOAT)
        result = self.generator.visit(float_literal)
        self.assertEqual(result, "3.14")

        # String literal
        string_literal = Literal("hello", Type.STRING)
        result = self.generator.visit(string_literal)
        self.assertEqual(result, "hello")

        # Boolean literal
        bool_literal = Literal(True, Type.BOOLEAN)
        result = self.generator.visit(bool_literal)
        self.assertEqual(result, "True")

    def test_null_literal_generation(self):
        """Test TAC generation for null literal."""
        null_literal = NullLiteral()
        result = self.generator.visit(null_literal)
        self.assertEqual(result, "null")

    def test_variable_generation(self):
        """Test TAC generation for variables."""
        variable = Variable("x")
        result = self.generator.visit(variable)
        self.assertEqual(result, "x")

    def test_arithmetic_binary_operations(self):
        """Test TAC generation for arithmetic binary operations."""
        operators = ['+', '-', '*', '/', '%']

        for op in operators:
            with self.subTest(operator=op):
                self.generator.clear_instructions()

                left = Variable("a")
                right = Variable("b")
                binary_op = BinaryOperation(left, right, op)

                result = self.generator.visit(binary_op)

                # Should generate one temporary
                self.assertTrue(result.startswith('t'))

                # Should emit one assignment instruction
                instructions = self.generator.get_instructions()
                self.assertEqual(len(instructions), 1)

                instr = instructions[0]
                self.assertIsInstance(instr, AssignInstruction)
                self.assertEqual(instr.target, result)
                self.assertEqual(instr.operand1, "a")
                self.assertEqual(instr.operator, op)
                self.assertEqual(instr.operand2, "b")

    def test_relational_binary_operations(self):
        """Test TAC generation for relational binary operations."""
        operators = ['==', '!=', '<', '>', '<=', '>=']

        for op in operators:
            with self.subTest(operator=op):
                self.generator.clear_instructions()

                left = Variable("x")
                right = Variable("y")
                binary_op = BinaryOperation(left, right, op)

                result = self.generator.visit(binary_op)

                # Should generate one temporary
                self.assertTrue(result.startswith('t'))

                # Should emit one assignment instruction
                instructions = self.generator.get_instructions()
                self.assertEqual(len(instructions), 1)

                instr = instructions[0]
                self.assertIsInstance(instr, AssignInstruction)
                self.assertEqual(instr.target, result)
                self.assertEqual(instr.operand1, "x")
                self.assertEqual(instr.operator, op)
                self.assertEqual(instr.operand2, "y")

    def test_boolean_and_shortcircuit(self):
        """Test TAC generation for boolean AND with short-circuit evaluation."""
        self.generator.clear_instructions()

        left = Variable("a")
        right = Variable("b")
        and_op = BinaryOperation(left, right, '&&')

        result = self.generator.visit(and_op)

        # Should generate one temporary for result
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have: conditional jump, right evaluation, assignment, goto, label, assignment, end label
        self.assertGreater(len(instructions), 3)

        # First instruction should be conditional jump for short-circuit
        self.assertIsInstance(instructions[0], ConditionalGotoInstruction)

        # Should have labels for control flow
        label_count = sum(1 for instr in instructions if isinstance(instr, LabelInstruction))
        self.assertGreaterEqual(label_count, 2)

    def test_boolean_or_shortcircuit(self):
        """Test TAC generation for boolean OR with short-circuit evaluation."""
        self.generator.clear_instructions()

        left = Variable("a")
        right = Variable("b")
        or_op = BinaryOperation(left, right, '||')

        result = self.generator.visit(or_op)

        # Should generate one temporary for result
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have multiple instructions for short-circuit logic
        self.assertGreater(len(instructions), 3)

        # First instruction should be conditional jump for short-circuit
        self.assertIsInstance(instructions[0], ConditionalGotoInstruction)

    def test_unary_operations(self):
        """Test TAC generation for unary operations."""
        operators = ['-', '!']

        for op in operators:
            with self.subTest(operator=op):
                self.generator.clear_instructions()

                operand = Variable("x")
                unary_op = UnaryOperation(operand, op)

                result = self.generator.visit(unary_op)

                # Should generate one temporary
                self.assertTrue(result.startswith('t'))

                # Should emit one assignment instruction
                instructions = self.generator.get_instructions()
                self.assertEqual(len(instructions), 1)

                instr = instructions[0]
                self.assertIsInstance(instr, AssignInstruction)
                self.assertEqual(instr.target, result)
                self.assertEqual(instr.operand1, "x")
                self.assertEqual(instr.operator, op)
                self.assertIsNone(instr.operand2)

    def test_variable_assignment(self):
        """Test TAC generation for variable assignment."""
        self.generator.clear_instructions()

        target = Variable("x")
        value = Variable("y")
        assignment = AssignmentStatement(target, value)

        result = self.generator.visit(assignment)

        # Should return the target variable name
        self.assertEqual(result, "x")

        # Should emit one assignment instruction
        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, AssignInstruction)
        self.assertEqual(instr.target, "x")
        self.assertEqual(instr.operand1, "y")
        self.assertIsNone(instr.operator)
        self.assertIsNone(instr.operand2)

    def test_array_assignment(self):
        """Test TAC generation for array element assignment."""
        self.generator.clear_instructions()

        array = Variable("arr")
        index = Variable("i")
        target = IndexExpression(array, index)
        value = Variable("val")
        assignment = AssignmentStatement(target, value)

        result = self.generator.visit(assignment)

        # Should return the value variable name
        self.assertEqual(result, "val")

        # Should emit one array access instruction
        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, ArrayAccessInstruction)
        self.assertEqual(instr.target, "val")
        self.assertEqual(instr.array, "arr")
        self.assertEqual(instr.index, "i")
        self.assertTrue(instr.is_assignment)

    def test_property_assignment(self):
        """Test TAC generation for property assignment."""
        self.generator.clear_instructions()

        obj = Variable("obj")
        target = PropertyAccess(obj, "field")
        value = Variable("val")
        assignment = AssignmentStatement(target, value)

        result = self.generator.visit(assignment)

        # Should return the value variable name
        self.assertEqual(result, "val")

        # Should emit one property access instruction
        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, PropertyAccessInstruction)
        self.assertEqual(instr.target, "val")
        self.assertEqual(instr.object_ref, "obj")
        self.assertEqual(instr.property_name, "field")
        self.assertTrue(instr.is_assignment)

    def test_ternary_operation(self):
        """Test TAC generation for ternary conditional operation."""
        self.generator.clear_instructions()

        condition = Variable("cond")
        true_expr = Variable("a")
        false_expr = Variable("b")
        ternary = TernaryOp(condition, true_expr, false_expr)

        result = self.generator.visit(ternary)

        # Should generate one temporary for result
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have multiple instructions for conditional logic
        self.assertGreater(len(instructions), 3)

        # Should have conditional jump for condition
        conditional_jumps = [instr for instr in instructions
                           if isinstance(instr, ConditionalGotoInstruction)]
        self.assertGreaterEqual(len(conditional_jumps), 1)

        # Should have labels for control flow
        labels = [instr for instr in instructions if isinstance(instr, LabelInstruction)]
        self.assertGreaterEqual(len(labels), 2)

    def test_array_access(self):
        """Test TAC generation for array element access."""
        self.generator.clear_instructions()

        array = Variable("arr")
        index = Variable("i")
        access = IndexExpression(array, index)

        result = self.generator.visit(access)

        # Should generate one temporary
        self.assertTrue(result.startswith('t'))

        # Should emit one array access instruction
        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, ArrayAccessInstruction)
        self.assertEqual(instr.target, result)
        self.assertEqual(instr.array, "arr")
        self.assertEqual(instr.index, "i")
        self.assertFalse(instr.is_assignment)

    def test_property_access(self):
        """Test TAC generation for property access."""
        self.generator.clear_instructions()

        obj = Variable("obj")
        access = PropertyAccess(obj, "field")

        result = self.generator.visit(access)

        # Should generate one temporary
        self.assertTrue(result.startswith('t'))

        # Should emit one property access instruction
        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, PropertyAccessInstruction)
        self.assertEqual(instr.target, result)
        self.assertEqual(instr.object_ref, "obj")
        self.assertEqual(instr.property_name, "field")
        self.assertFalse(instr.is_assignment)

    def test_array_literal(self):
        """Test TAC generation for array literal."""
        self.generator.clear_instructions()

        elements = [Literal(1, Type.INTEGER), Literal(2, Type.INTEGER), Literal(3, Type.INTEGER)]
        array_literal = ArrayLiteral(elements)

        result = self.generator.visit(array_literal)

        # Should generate one temporary for array
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have comment + array creation + element assignments
        self.assertGreater(len(instructions), 3)

        # First should be comment
        self.assertIsInstance(instructions[0], CommentInstruction)

        # Should have array assignments for each element
        array_assignments = [instr for instr in instructions
                           if isinstance(instr, ArrayAccessInstruction) and instr.is_assignment]
        self.assertEqual(len(array_assignments), 3)

    def test_complex_expression(self):
        """Test TAC generation for complex nested expressions."""
        self.generator.clear_instructions()

        # Expression: (a + b) * (c - d)
        a = Variable("a")
        b = Variable("b")
        c = Variable("c")
        d = Variable("d")

        add_op = BinaryOperation(a, b, '+')
        sub_op = BinaryOperation(c, d, '-')
        mul_op = BinaryOperation(add_op, sub_op, '*')

        result = self.generator.visit(mul_op)

        # Should generate temporary for final result
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have 3 instructions: t1 = a + b, t2 = c - d, t3 = t1 * t2
        self.assertEqual(len(instructions), 3)

        # All should be assignment instructions
        for instr in instructions:
            self.assertIsInstance(instr, AssignInstruction)

    def test_temporary_management(self):
        """Test proper temporary variable management."""
        self.generator.clear_instructions()

        # Create multiple operations to generate temporaries
        a = Variable("a")
        b = Variable("b")
        c = Variable("c")

        op1 = BinaryOperation(a, b, '+')
        op2 = BinaryOperation(op1, c, '*')

        result = self.generator.visit(op2)

        # Should use sequential temporary names
        instructions = self.generator.get_instructions()
        temps_used = set()

        for instr in instructions:
            if isinstance(instr, AssignInstruction):
                if instr.target.startswith('t'):
                    temps_used.add(instr.target)

        # Should have used exactly 2 temporaries
        self.assertEqual(len(temps_used), 2)
        self.assertIn('t1', temps_used)
        self.assertIn('t2', temps_used)

    def test_operator_precedence_helpers(self):
        """Test operator precedence helper methods."""
        # Test boolean operator check
        self.assertTrue(self.generator._is_boolean_operator('&&'))
        self.assertTrue(self.generator._is_boolean_operator('||'))
        self.assertTrue(self.generator._is_boolean_operator('=='))
        self.assertTrue(self.generator._is_boolean_operator('!'))
        self.assertFalse(self.generator._is_boolean_operator('+'))

        # Test arithmetic operator check
        self.assertTrue(self.generator._is_arithmetic_operator('+'))
        self.assertTrue(self.generator._is_arithmetic_operator('*'))
        self.assertFalse(self.generator._is_arithmetic_operator('&&'))

        # Test precedence values
        self.assertGreater(self.generator._get_operator_precedence('*'),
                          self.generator._get_operator_precedence('+'))
        self.assertGreater(self.generator._get_operator_precedence('!'),
                          self.generator._get_operator_precedence('&&'))

    def test_string_concatenation(self):
        """Test TAC generation for string concatenation."""
        self.generator.clear_instructions()

        # Create string literals with proper types
        left = Literal("Hello", Type.STRING)
        right = Literal(" World", Type.STRING)
        concat_op = BinaryOperation(left, right, '+')

        result = self.generator.visit(concat_op)

        # Should generate one temporary
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        # Should have comment and concatenation instruction
        self.assertEqual(len(instructions), 2)

        # First should be comment
        self.assertIsInstance(instructions[0], CommentInstruction)
        self.assertIn("String concatenation", str(instructions[0]))

        # Second should be assignment with str_concat operator
        instr = instructions[1]
        self.assertIsInstance(instr, AssignInstruction)
        self.assertEqual(instr.operator, "str_concat")

    def test_numeric_type_conversion(self):
        """Test automatic type conversions for numeric operations."""
        self.generator.clear_instructions()

        # Integer + Float should promote integer to float
        int_var = Variable("a")
        int_var.type = Type.INTEGER
        float_var = Variable("b")
        float_var.type = Type.FLOAT

        add_op = BinaryOperation(int_var, float_var, '+')

        result = self.generator.visit(add_op)

        instructions = self.generator.get_instructions()
        # Should have conversion instruction + operation instruction
        self.assertGreaterEqual(len(instructions), 2)

        # Check for int_to_float conversion
        conversion_found = any(
            isinstance(instr, AssignInstruction) and instr.operator == "int_to_float"
            for instr in instructions
        )
        self.assertTrue(conversion_found, "Should generate int_to_float conversion")

    def test_type_validation_helpers(self):
        """Test type validation helper methods."""
        # Test numeric type check
        self.assertTrue(self.generator._is_numeric_type(Type.INTEGER))
        self.assertTrue(self.generator._is_numeric_type(Type.FLOAT))
        self.assertFalse(self.generator._is_numeric_type(Type.STRING))
        self.assertFalse(self.generator._is_numeric_type(Type.BOOLEAN))

        # Test string literal detection
        string_lit = Literal("test", Type.STRING)
        int_lit = Literal(42, Type.INTEGER)
        var = Variable("x")

        self.assertTrue(self.generator._is_string_literal(string_lit))
        self.assertFalse(self.generator._is_string_literal(int_lit))
        self.assertFalse(self.generator._is_string_literal(var))

    # ============ FAILURE TESTS (TEST-003) ============

    def test_incompatible_string_operations(self):
        """Test that invalid string operations raise errors."""
        # String - String should fail
        left = Literal("Hello", Type.STRING)
        right = Literal("World", Type.STRING)

        invalid_ops = ['-', '*', '/', '%', '<', '>', '<=', '>=']

        for op in invalid_ops:
            with self.subTest(operator=op):
                binary_op = BinaryOperation(left, right, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                self.assertIn("String operands only support concatenation", str(context.exception))

    def test_incompatible_boolean_operations(self):
        """Test that invalid boolean operations raise errors."""
        left = Literal(True, Type.BOOLEAN)
        right = Literal(False, Type.BOOLEAN)

        invalid_ops = ['+', '-', '*', '/', '%', '<', '>', '<=', '>=']

        for op in invalid_ops:
            with self.subTest(operator=op):
                binary_op = BinaryOperation(left, right, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                self.assertIn("Boolean operands don't support operator", str(context.exception))

    def test_arithmetic_with_non_numeric(self):
        """Test that arithmetic operations with non-numeric types fail."""
        string_val = Literal("test", Type.STRING)
        int_val = Literal(42, Type.INTEGER)
        bool_val = Literal(True, Type.BOOLEAN)

        arithmetic_ops = ['+', '-', '*', '/', '%']

        # Test string with number
        for op in arithmetic_ops:
            if op == '+':  # Skip +, as it's valid for string concatenation
                continue

            with self.subTest(operator=f"string {op} int"):
                binary_op = BinaryOperation(string_val, int_val, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                # Should get string-specific error message
                self.assertIn("String operands only support concatenation", str(context.exception))

        # Test boolean with number
        for op in arithmetic_ops:
            with self.subTest(operator=f"boolean {op} int"):
                binary_op = BinaryOperation(bool_val, int_val, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                # Should get boolean-specific error message
                self.assertIn("Boolean operands don't support operator", str(context.exception))

    def test_relational_with_non_numeric(self):
        """Test that relational operations with non-numeric types fail."""
        string_val = Literal("test", Type.STRING)
        int_val = Literal(42, Type.INTEGER)
        bool_val = Literal(True, Type.BOOLEAN)

        relational_ops = ['<', '>', '<=', '>=']

        # Test string comparisons
        for op in relational_ops:
            with self.subTest(operator=f"string {op} int"):
                binary_op = BinaryOperation(string_val, int_val, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                # Should get string-specific error message
                self.assertIn("String operands only support concatenation", str(context.exception))

        # Test boolean comparisons
        for op in relational_ops:
            with self.subTest(operator=f"boolean {op} int"):
                binary_op = BinaryOperation(bool_val, int_val, op)

                with self.assertRaises(TACGenerationError) as context:
                    self.generator.visit(binary_op)

                # Should get boolean-specific error message
                self.assertIn("Boolean operands don't support operator", str(context.exception))

    def test_mixed_invalid_types(self):
        """Test complex invalid type combinations."""
        self.generator.clear_instructions()

        # Try to multiply string by boolean
        string_val = Literal("hello", Type.STRING)
        bool_val = Literal(True, Type.BOOLEAN)

        binary_op = BinaryOperation(string_val, bool_val, '*')

        with self.assertRaises(TACGenerationError) as context:
            self.generator.visit(binary_op)

        # Should catch the string type error first
        self.assertIn("String operands only support concatenation", str(context.exception))

    def test_error_messages_include_node_info(self):
        """Test that error messages include node information when available."""
        # Create a node with line/column info
        left = Literal("test", Type.STRING)
        right = Literal(42, Type.INTEGER)
        binary_op = BinaryOperation(left, right, '-')
        binary_op.line = 10
        binary_op.column = 5

        with self.assertRaises(TACGenerationError) as context:
            self.generator.visit(binary_op)

        # Error should include line/column information
        error_msg = str(context.exception)
        self.assertIn("Line 10:5", error_msg)

    def test_graceful_handling_without_type_info(self):
        """Test that operations work gracefully when type information is missing."""
        self.generator.clear_instructions()

        # Create nodes without type information
        left = Variable("a")  # No type set
        right = Variable("b")  # No type set
        binary_op = BinaryOperation(left, right, '+')

        # Should not raise an error due to missing type info
        result = self.generator.visit(binary_op)

        # Should generate normal arithmetic operation
        self.assertTrue(result.startswith('t'))

        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 1)

        instr = instructions[0]
        self.assertIsInstance(instr, AssignInstruction)
        self.assertEqual(instr.operator, '+')

if __name__ == '__main__':
    unittest.main()