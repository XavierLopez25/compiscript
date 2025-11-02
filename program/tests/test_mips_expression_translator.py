import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tac.address_manager import MemoryLocation
from tac.instruction import AssignInstruction
from mips import MIPSTranslatorBase
from mips.expression_translator import ExpressionTranslator


class TestExpressionTranslator(unittest.TestCase):
    def setUp(self) -> None:
        """Set up translator for each test."""
        self.base_translator = MIPSTranslatorBase()
        self.translator = ExpressionTranslator(self.base_translator)

        self.base_translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.base_translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )
        self.base_translator.bind_memory_location(
            "x", MemoryLocation(address="fp-12", offset=-12, size=4, is_temporary=False)
        )

    def _get_emitted_code(self) -> str:
        """Helper to get emitted MIPS code as a single string."""
        return "\n".join(str(instr) for instr in self.base_translator.text_section)

    # Arithmetic operations
    def test_addition_variables(self) -> None:
        """Test: t1 = a + b"""
        instruction = AssignInstruction("t1", "a", "+", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        # Should load a and b, then add them
        self.assertIn("lw", code)
        self.assertIn("add", code)

    def test_addition_with_constant(self) -> None:
        """Test: t1 = a + 5"""
        instruction = AssignInstruction("t1", "a", "+", "5")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        # Should use addi for immediate addition
        self.assertIn("lw", code)  # Load a
        self.assertIn("addi", code)  # Add immediate 5

    def test_subtraction(self) -> None:
        """Test: t1 = a - b"""
        instruction = AssignInstruction("t1", "a", "-", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sub", code)

    def test_multiplication(self) -> None:
        """Test: t1 = a * b"""
        instruction = AssignInstruction("t1", "a", "*", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("mul", code)

    def test_division(self) -> None:
        """Test: t1 = a / b"""
        instruction = AssignInstruction("t1", "a", "/", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("div", code)
        self.assertIn("mflo", code)  # Get quotient

    def test_modulo(self) -> None:
        """Test: t1 = a % b"""
        instruction = AssignInstruction("t1", "a", "%", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("div", code)
        self.assertIn("mfhi", code)  # Get remainder

    # Unary operations
    def test_unary_negation(self) -> None:
        """Test: t1 = -a"""
        instruction = AssignInstruction("t1", "a", "-", None)
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sub", code)
        self.assertIn("$zero", code)  # Should be: sub $dest, $zero, $src

    def test_logical_not(self) -> None:
        """Test: t1 = !a"""
        instruction = AssignInstruction("t1", "a", "!", None)
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sltiu", code)  # Set less than immediate unsigned

    # Comparison operations
    def test_less_than(self) -> None:
        """Test: t1 = a < b"""
        instruction = AssignInstruction("t1", "a", "<", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("slt", code)

    def test_less_than_immediate(self) -> None:
        """Test: t1 = a < 10"""
        instruction = AssignInstruction("t1", "a", "<", "10")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("slti", code)  # Set less than immediate

    def test_greater_than(self) -> None:
        """Test: t1 = a > b"""
        instruction = AssignInstruction("t1", "a", ">", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        # Should use slt with swapped operands
        self.assertIn("slt", code)

    def test_less_or_equal(self) -> None:
        """Test: t1 = a <= b"""
        instruction = AssignInstruction("t1", "a", "<=", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("slt", code)
        self.assertIn("xori", code)  # Negation

    def test_greater_or_equal(self) -> None:
        """Test: t1 = a >= b"""
        instruction = AssignInstruction("t1", "a", ">=", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("slt", code)
        self.assertIn("xori", code)

    def test_equal(self) -> None:
        """Test: t1 = a == b"""
        instruction = AssignInstruction("t1", "a", "==", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sub", code)
        self.assertIn("sltiu", code)

    def test_not_equal(self) -> None:
        """Test: t1 = a != b"""
        instruction = AssignInstruction("t1", "a", "!=", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sub", code)
        self.assertIn("sltu", code)

    # Logical operations
    def test_logical_and(self) -> None:
        """Test: t1 = a && b"""
        instruction = AssignInstruction("t1", "a", "&&", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("sltu", code)  # Convert to boolean
        self.assertIn("and", code)   # Bitwise AND

    def test_logical_or(self) -> None:
        """Test: t1 = a || b"""
        instruction = AssignInstruction("t1", "a", "||", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("or", code)
        self.assertIn("sltu", code)

    def test_bitwise_and(self) -> None:
        """Test: t1 = a & b"""
        instruction = AssignInstruction("t1", "a", "&", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("and", code)

    def test_bitwise_or(self) -> None:
        """Test: t1 = a | b"""
        instruction = AssignInstruction("t1", "a", "|", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("or", code)

    def test_bitwise_xor(self) -> None:
        """Test: t1 = a ^ b"""
        instruction = AssignInstruction("t1", "a", "^", "b")
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("xor", code)

    # Simple assignments
    def test_simple_assignment_variable(self) -> None:
        """Test: t1 = a"""
        instruction = AssignInstruction("t1", "a", None, None)
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("lw", code)   # Load a
        self.assertIn("move", code)  # Move to destination

    def test_simple_assignment_constant(self) -> None:
        """Test: t1 = 42"""
        instruction = AssignInstruction("t1", "42", None, None)
        self.translator.translate_assignment(instruction)

        code = self._get_emitted_code()
        self.assertIn("li", code)  # Load immediate
        self.assertIn("42", code)

    # Integration tests
    def test_complex_expression(self) -> None:
        """Test sequence: t1 = a + b; t2 = t1 * 2"""
        # First operation
        instr1 = AssignInstruction("t1", "a", "+", "b")
        self.translator.translate_assignment(instr1)

        # Second operation
        instr2 = AssignInstruction("t2", "t1", "*", "2")
        self.translator.translate_assignment(instr2)

        code = self._get_emitted_code()
        # Should see addition and multiplication
        self.assertIn("add", code)
        self.assertIn("mul", code)

    def test_register_reuse(self) -> None:
        """Test that registers are reused efficiently."""
        # Multiple operations that should reuse registers
        instructions = [
            AssignInstruction("t1", "10", None, None),
            AssignInstruction("t2", "20", None, None),
            AssignInstruction("t3", "t1", "+", "t2"),
        ]

        for instr in instructions:
            self.translator.translate_assignment(instr)

        code = self._get_emitted_code()
        # Should successfully generate code without running out of registers
        self.assertIn("li", code)
        self.assertIn("add", code)

if __name__ == "__main__":
    unittest.main()
