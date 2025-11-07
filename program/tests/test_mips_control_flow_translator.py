import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tac.address_manager import MemoryLocation
from tac.instruction import (
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
)
from mips import MIPSTranslatorBase, ControlFlowTranslator, LabelResolutionError


class TestControlFlowTranslator(unittest.TestCase):
    """Tests for MIPS control flow translation."""

    def setUp(self) -> None:
        """Set up translator for each test."""
        self.base_translator = MIPSTranslatorBase()
        self.translator = ControlFlowTranslator(self.base_translator)

        # Bind some test variables to memory
        self.base_translator.bind_memory_location(
            "cond", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.base_translator.bind_memory_location(
            "x", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )
        self.base_translator.bind_memory_location(
            "y", MemoryLocation(address="fp-12", offset=-12, size=4, is_temporary=False)
        )

    def _get_emitted_code(self) -> str:
        """Helper to get emitted MIPS code as a single string."""
        return "\n".join(str(instr) for instr in self.base_translator.text_section)

    # ===== Unconditional Jumps =====

    def test_unconditional_goto(self) -> None:
        """Test: goto L1"""
        instruction = GotoInstruction("L1")
        self.translator.translate_goto(instruction)

        code = self._get_emitted_code()
        self.assertIn("j L1", code)
        self.assertTrue(self.translator.label_manager.is_referenced("L1"))

    def test_multiple_gotos(self) -> None:
        """Test multiple goto instructions."""
        self.translator.translate_goto(GotoInstruction("L1"))
        self.translator.translate_goto(GotoInstruction("L2"))
        self.translator.translate_goto(GotoInstruction("L1"))  # Reference L1 again

        code = self._get_emitted_code()
        self.assertEqual(code.count("j L1"), 2)
        self.assertEqual(code.count("j L2"), 1)

    # ===== Simple Conditional Branches =====

    def test_simple_conditional_goto_variable(self) -> None:
        """Test: if cond goto L1"""
        instruction = ConditionalGotoInstruction("cond", "L1")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should load cond and branch if non-zero
        self.assertIn("lw", code)
        self.assertIn("bnez", code)
        self.assertIn("L1", code)

    def test_simple_conditional_goto_constant(self) -> None:
        """Test: if 5 goto L1"""
        instruction = ConditionalGotoInstruction("5", "L1")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should load constant 5 and branch
        self.assertIn("li", code)
        self.assertIn("5", code)
        self.assertIn("bnez", code)

    # ===== Relational Conditional Branches =====

    def test_conditional_goto_equals(self) -> None:
        """Test: if x == y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", "==")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use beq instruction
        self.assertIn("beq", code)
        self.assertIn("L1", code)

    def test_conditional_goto_not_equals(self) -> None:
        """Test: if x != y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", "!=")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use bne instruction
        self.assertIn("bne", code)
        self.assertIn("L1", code)

    def test_conditional_goto_less_than(self) -> None:
        """Test: if x < y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", "<")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use slt followed by bnez
        self.assertIn("slt", code)
        self.assertIn("bnez", code)
        self.assertIn("L1", code)

    def test_conditional_goto_less_equal(self) -> None:
        """Test: if x <= y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", "<=")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use slt followed by beqz
        # (if y < x is false, then x <= y)
        self.assertIn("slt", code)
        self.assertIn("beqz", code)
        self.assertIn("L1", code)

    def test_conditional_goto_greater_than(self) -> None:
        """Test: if x > y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", ">")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use slt followed by bnez
        # (check if y < x)
        self.assertIn("slt", code)
        self.assertIn("bnez", code)
        self.assertIn("L1", code)

    def test_conditional_goto_greater_equal(self) -> None:
        """Test: if x >= y goto L1"""
        instruction = ConditionalGotoInstruction("x", "L1", "y", ">=")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should use slt followed by beqz
        # (if x < y is false, then x >= y)
        self.assertIn("slt", code)
        self.assertIn("beqz", code)
        self.assertIn("L1", code)

    def test_conditional_with_constants(self) -> None:
        """Test: if 5 < 10 goto L1"""
        instruction = ConditionalGotoInstruction("5", "L1", "10", "<")
        self.translator.translate_conditional_goto(instruction)

        code = self._get_emitted_code()
        # Should load both constants
        self.assertEqual(code.count("li"), 2)
        self.assertIn("slt", code)
        self.assertIn("bnez", code)

    # ===== Label Emission =====

    def test_label_emission(self) -> None:
        """Test: L1:"""
        instruction = LabelInstruction("L1")
        self.translator.translate_label(instruction)

        code = self._get_emitted_code()
        self.assertIn("L1:", code)
        self.assertTrue(self.translator.label_manager.is_defined("L1"))

    def test_multiple_labels(self) -> None:
        """Test multiple label definitions."""
        self.translator.translate_label(LabelInstruction("L1"))
        self.translator.translate_label(LabelInstruction("L2"))
        self.translator.translate_label(LabelInstruction("L3"))

        code = self._get_emitted_code()
        self.assertIn("L1:", code)
        self.assertIn("L2:", code)
        self.assertIn("L3:", code)

    # ===== Label Validation =====

    def test_duplicate_label_error(self) -> None:
        """Test that duplicate labels raise an error."""
        self.translator.translate_label(LabelInstruction("L1"))
        with self.assertRaises(LabelResolutionError):
            self.translator.translate_label(LabelInstruction("L1"))

    def test_undefined_label_detection(self) -> None:
        """Test detection of undefined labels."""
        # Reference a label without defining it
        self.translator.translate_goto(GotoInstruction("undefined_label"))

        # Validation should fail
        with self.assertRaises(LabelResolutionError):
            self.translator.validate_labels()

    def test_valid_label_resolution(self) -> None:
        """Test that defined and referenced labels validate successfully."""
        # Define and reference the same label
        self.translator.translate_label(LabelInstruction("L1"))
        self.translator.translate_goto(GotoInstruction("L1"))

        # Should validate without error
        self.translator.validate_labels()

    # ===== Control Flow Patterns =====

    def test_if_statement_pattern(self) -> None:
        """
        Test typical if statement pattern:
            if cond == 0 goto if_false1
            # then block
            goto if_end2
        if_false1:
            # else block
        if_end2:
        """
        # if cond == 0 goto if_false1
        self.translator.translate_conditional_goto(
            ConditionalGotoInstruction("cond", "if_false1", "0", "==")
        )

        # goto if_end2
        self.translator.translate_goto(GotoInstruction("if_end2"))

        # if_false1:
        self.translator.translate_label(LabelInstruction("if_false1"))

        # if_end2:
        self.translator.translate_label(LabelInstruction("if_end2"))

        code = self._get_emitted_code()
        self.assertIn("beq", code)
        self.assertIn("j if_end2", code)
        self.assertIn("if_false1:", code)
        self.assertIn("if_end2:", code)

        # Should validate successfully
        self.translator.validate_labels()

    def test_while_loop_pattern(self) -> None:
        """
        Test typical while loop pattern:
        while_start1:
            if cond == 0 goto while_end2
            # loop body
            goto while_start1
        while_end2:
        """
        # while_start1:
        self.translator.translate_label(LabelInstruction("while_start1"))

        # if cond == 0 goto while_end2
        self.translator.translate_conditional_goto(
            ConditionalGotoInstruction("cond", "while_end2", "0", "==")
        )

        # goto while_start1
        self.translator.translate_goto(GotoInstruction("while_start1"))

        # while_end2:
        self.translator.translate_label(LabelInstruction("while_end2"))

        code = self._get_emitted_code()
        self.assertIn("while_start1:", code)
        self.assertIn("while_end2:", code)
        self.assertIn("j while_start1", code)

        # Should validate successfully
        self.translator.validate_labels()

    def test_for_loop_pattern(self) -> None:
        """
        Test typical for loop pattern:
        for_cond1:
            if i >= 10 goto for_end3
            # loop body
            goto for_update2
        for_update2:
            # update code
            goto for_cond1
        for_end3:
        """
        # for_cond1:
        self.translator.translate_label(LabelInstruction("for_cond1"))

        # if i >= 10 goto for_end3
        self.translator.translate_conditional_goto(
            ConditionalGotoInstruction("x", "for_end3", "10", ">=")
        )

        # goto for_update2
        self.translator.translate_goto(GotoInstruction("for_update2"))

        # for_update2:
        self.translator.translate_label(LabelInstruction("for_update2"))

        # goto for_cond1
        self.translator.translate_goto(GotoInstruction("for_cond1"))

        # for_end3:
        self.translator.translate_label(LabelInstruction("for_end3"))

        code = self._get_emitted_code()
        self.assertIn("for_cond1:", code)
        self.assertIn("for_update2:", code)
        self.assertIn("for_end3:", code)

        # Should validate successfully
        self.translator.validate_labels()

    def test_nested_conditionals(self) -> None:
        """Test nested if statements."""
        # Outer if
        self.translator.translate_conditional_goto(
            ConditionalGotoInstruction("x", "outer_false", "0", "==")
        )

        # Inner if
        self.translator.translate_conditional_goto(
            ConditionalGotoInstruction("y", "inner_false", "0", "==")
        )

        self.translator.translate_goto(GotoInstruction("inner_end"))
        self.translator.translate_label(LabelInstruction("inner_false"))
        self.translator.translate_label(LabelInstruction("inner_end"))

        self.translator.translate_goto(GotoInstruction("outer_end"))
        self.translator.translate_label(LabelInstruction("outer_false"))
        self.translator.translate_label(LabelInstruction("outer_end"))

        # Should validate successfully
        self.translator.validate_labels()

    # ===== Edge Cases =====

    def test_unsupported_operator_error(self) -> None:
        """Test that unsupported operators raise an error."""
        instruction = ConditionalGotoInstruction("x", "L1", "y", "===")  # Invalid
        with self.assertRaises(ValueError):
            self.translator.translate_conditional_goto(instruction)

    def test_reset_clears_state(self) -> None:
        """Test that reset clears the translator state."""
        self.translator.translate_label(LabelInstruction("L1"))
        self.translator.translate_goto(GotoInstruction("L1"))

        self.translator.reset()

        # Label manager should be empty
        self.assertFalse(self.translator.label_manager.is_defined("L1"))
        self.assertFalse(self.translator.label_manager.is_referenced("L1"))


class TestLabelManager(unittest.TestCase):
    """Tests for the LabelManager class."""

    def setUp(self):
        from mips.label_manager import LabelManager
        self.manager = LabelManager()

    def test_define_label(self):
        """Test label definition."""
        self.manager.define_label("L1")
        self.assertTrue(self.manager.is_defined("L1"))

    def test_reference_label(self):
        """Test label reference."""
        self.manager.reference_label("L1")
        self.assertTrue(self.manager.is_referenced("L1"))

    def test_undefined_labels(self):
        """Test detection of undefined labels."""
        self.manager.reference_label("L1")
        self.manager.reference_label("L2")
        self.manager.define_label("L1")

        undefined = self.manager.get_undefined_labels()
        self.assertEqual(undefined, ["L2"])

    def test_unreferenced_labels(self):
        """Test detection of unreferenced labels."""
        self.manager.define_label("L1")
        self.manager.define_label("L2")
        self.manager.reference_label("L1")

        unreferenced = self.manager.get_unreferenced_labels()
        self.assertEqual(unreferenced, ["L2"])

    def test_generate_unique_labels(self):
        """Test unique label generation."""
        l1 = self.manager.generate_unique_label("test")
        l2 = self.manager.generate_unique_label("test")
        l3 = self.manager.generate_unique_label("other")

        self.assertEqual(l1, "test1")
        self.assertEqual(l2, "test2")
        self.assertEqual(l3, "other1")

    def test_validation_fails_on_undefined(self):
        """Test that validation fails with undefined labels."""
        self.manager.reference_label("undefined")
        with self.assertRaises(LabelResolutionError):
            self.manager.validate()

    def test_validation_succeeds(self):
        """Test that validation succeeds when all labels are defined."""
        self.manager.define_label("L1")
        self.manager.reference_label("L1")
        self.manager.validate()  # Should not raise


class TestLoopPatternDetector(unittest.TestCase):
    """Tests for the LoopPatternDetector class."""

    def setUp(self):
        from mips.loop_translator import LoopPatternDetector
        self.detector = LoopPatternDetector()

    def test_detect_while_loop(self):
        """Test while loop detection."""
        loop_info = self.detector.detect_while_loop("while_start1")
        self.assertIsNotNone(loop_info)
        self.assertEqual(loop_info.header_label, "while_start1")
        self.assertEqual(loop_info.exit_label, "while_end1")
        self.assertEqual(loop_info.loop_type, "while")

    def test_detect_for_loop(self):
        """Test for loop detection."""
        loop_info = self.detector.detect_for_loop("for_cond1")
        self.assertIsNotNone(loop_info)
        self.assertEqual(loop_info.header_label, "for_cond1")
        self.assertEqual(loop_info.exit_label, "for_end1")
        self.assertEqual(loop_info.continue_label, "for_update1")
        self.assertEqual(loop_info.loop_type, "for")

    def test_detect_do_while_loop(self):
        """Test do-while loop detection."""
        loop_info = self.detector.detect_do_while_loop("do_start1")
        self.assertIsNotNone(loop_info)
        self.assertEqual(loop_info.header_label, "do_start1")
        self.assertEqual(loop_info.exit_label, "do_end1")
        self.assertEqual(loop_info.loop_type, "do-while")

    def test_detect_foreach_loop(self):
        """Test foreach loop detection."""
        loop_info = self.detector.detect_foreach_loop("foreach_start1")
        self.assertIsNotNone(loop_info)
        self.assertEqual(loop_info.header_label, "foreach_start1")
        self.assertEqual(loop_info.exit_label, "foreach_end1")
        self.assertEqual(loop_info.continue_label, "foreach_continue1")
        self.assertEqual(loop_info.loop_type, "foreach")

    def test_detect_any_loop(self):
        """Test generic loop detection."""
        loop_info = self.detector.detect_loop("while_start5")
        self.assertIsNotNone(loop_info)
        self.assertEqual(loop_info.loop_type, "while")

    def test_no_loop_detected(self):
        """Test that non-loop labels return None."""
        loop_info = self.detector.detect_loop("random_label")
        self.assertIsNone(loop_info)


if __name__ == "__main__":
    unittest.main()
