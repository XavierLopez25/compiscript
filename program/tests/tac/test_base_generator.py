import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.base_generator import TACGenerator, BaseTACVisitor, TACGenerationError
from tac.instruction import AssignInstruction, LabelInstruction, CommentInstruction
from AST.ast_nodes import ASTNode, Variable, BinaryOperation

class MockTACGenerator(TACGenerator):
    """Mock implementation of TACGenerator for testing."""

    def generate(self, ast_node: ASTNode):
        """Mock implementation that returns a test temporary."""
        return "t1"

class MockTACVisitor(BaseTACVisitor):
    """Mock implementation of BaseTACVisitor for testing."""

    def visit_Variable(self, node):
        """Visit a variable node."""
        return node.name

    def visit_BinaryOperation(self, node):
        """Visit a binary operation node."""
        left = self.visit(node.left)
        right = self.visit(node.right)
        result = self.new_temp()

        # Generate TAC for binary operation
        instr = AssignInstruction(result, left, node.operator, right)
        self.emit(instr)

        return result

class TestTACGenerator(unittest.TestCase):
    """Test cases for TACGenerator base class."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = MockTACGenerator()

    def test_instruction_emission(self):
        """Test instruction emission."""
        instr1 = AssignInstruction("t1", "a", "+", "b")
        instr2 = LabelInstruction("L1")

        self.generator.emit(instr1)
        self.generator.emit(instr2)

        instructions = self.generator.get_instructions()
        self.assertEqual(len(instructions), 2)
        self.assertEqual(instructions[0], instr1)
        self.assertEqual(instructions[1], instr2)

    def test_multiple_instruction_emission(self):
        """Test emitting multiple instructions at once."""
        instructions = [
            AssignInstruction("t1", "a", "+", "b"),
            LabelInstruction("L1"),
            CommentInstruction("Test comment")
        ]

        self.generator.emit_list(instructions)

        emitted = self.generator.get_instructions()
        self.assertEqual(len(emitted), 3)
        self.assertEqual(emitted, instructions)

    def test_temporary_variable_management(self):
        """Test temporary variable generation and release."""
        temp1 = self.generator.new_temp()
        temp2 = self.generator.new_temp()

        self.assertEqual(temp1, "t1")
        self.assertEqual(temp2, "t2")

        # Release temp1
        self.generator.release_temp(temp1)

        # Next temp should reuse temp1
        temp3 = self.generator.new_temp()
        self.assertEqual(temp3, temp1)

    def test_label_generation(self):
        """Test label generation."""
        label1 = self.generator.new_label()
        label2 = self.generator.new_label("LOOP")

        self.assertEqual(label1, "L1")
        self.assertEqual(label2, "LOOP2")

    def test_scope_management(self):
        """Test scope entry and exit."""
        temp1 = self.generator.new_temp()

        self.generator.enter_scope()
        temp2 = self.generator.new_temp()
        temp3 = self.generator.new_temp()

        # Exit scope should release temps created in scope
        self.generator.exit_scope()

        # temp1 should still be active, temp2 and temp3 should be released
        active_temps = self.generator.temp_manager.get_active_temps()
        self.assertIn(temp1, active_temps)
        self.assertNotIn(temp2, active_temps)
        self.assertNotIn(temp3, active_temps)

    def test_tac_code_generation(self):
        """Test TAC code string generation."""
        self.generator.emit(AssignInstruction("t1", "a", "+", "b"))
        self.generator.emit(LabelInstruction("L1"))
        self.generator.emit(CommentInstruction("Test"))

        tac_code = self.generator.get_tac_code()
        expected = "t1 = a + b\nL1:\n# Test"
        self.assertEqual(tac_code, expected)

    def test_clear_instructions(self):
        """Test clearing instructions."""
        self.generator.emit(AssignInstruction("t1", "a", "+", "b"))
        self.generator.emit(LabelInstruction("L1"))

        self.assertEqual(len(self.generator.get_instructions()), 2)

        self.generator.clear_instructions()
        self.assertEqual(len(self.generator.get_instructions()), 0)

    def test_reset_functionality(self):
        """Test generator reset."""
        # Generate some state
        self.generator.emit(AssignInstruction("t1", "a", "+", "b"))
        self.generator.new_temp()
        self.generator.new_label()

        # Reset
        self.generator.reset()

        # Check state is cleared
        self.assertEqual(len(self.generator.get_instructions()), 0)
        self.assertEqual(self.generator.temp_manager.get_temp_count(), 0)

        # Next temp and label should start from 1
        temp = self.generator.new_temp()
        label = self.generator.new_label()
        self.assertEqual(temp, "t1")
        self.assertEqual(label, "L1")

    def test_statistics(self):
        """Test generation statistics."""
        self.generator.emit(AssignInstruction("t1", "a", "+", "b"))
        self.generator.emit(LabelInstruction("L1"))
        temp1 = self.generator.new_temp()
        temp2 = self.generator.new_temp()
        self.generator.release_temp(temp1)

        stats = self.generator.get_statistics()

        self.assertEqual(stats['instructions_generated'], 2)
        self.assertIn('temporary_stats', stats)
        self.assertIn('address_stats', stats)
        self.assertIn('label_stats', stats)

class TestBaseTACVisitor(unittest.TestCase):
    """Test cases for BaseTACVisitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.visitor = MockTACVisitor()

    def test_visit_method_dispatch(self):
        """Test visitor method dispatch to specific visit methods."""
        var_node = Variable("test_var")
        result = self.visitor.visit(var_node)

        self.assertEqual(result, "test_var")

    def test_visit_binary_operation(self):
        """Test visiting a binary operation AST node."""
        left = Variable("a")
        right = Variable("b")
        binary_op = BinaryOperation(left, right, "+")

        result = self.visitor.visit(binary_op)

        # Should generate a temporary and TAC instruction
        self.assertEqual(result, "t1")
        instructions = self.visitor.get_instructions()
        self.assertEqual(len(instructions), 1)
        self.assertEqual(str(instructions[0]), "t1 = a + b")

    def test_generic_visit(self):
        """Test generic visit for nodes without specific handlers."""
        # Create a mock AST node without a specific visit method
        class MockNode(ASTNode):
            pass

        mock_node = MockNode()
        result = self.visitor.visit(mock_node)

        self.assertIsNone(result)

    def test_generate_method(self):
        """Test generate method (which delegates to visit)."""
        var_node = Variable("test_var")
        result = self.visitor.generate(var_node)

        self.assertEqual(result, "test_var")

    def test_none_node_handling(self):
        """Test handling of None nodes."""
        result = self.visitor.visit(None)
        self.assertIsNone(result)

class TestTACGenerationError(unittest.TestCase):
    """Test cases for TACGenerationError exception."""

    def test_error_without_node(self):
        """Test error creation without AST node."""
        error = TACGenerationError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsNone(error.node)

    def test_error_with_node(self):
        """Test error creation with AST node."""
        node = Variable("test_var")
        node.line = 10
        node.column = 5

        error = TACGenerationError("Test error message", node)
        self.assertEqual(str(error), "Line 10:5: Test error message")
        self.assertEqual(error.node, node)

    def test_error_with_node_no_location(self):
        """Test error creation with AST node without location info."""
        node = Variable("test_var")

        error = TACGenerationError("Test error message", node)
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.node, node)

if __name__ == '__main__':
    unittest.main()
