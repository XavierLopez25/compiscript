import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.instruction import (
    AssignInstruction,
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
    ArrayAccessInstruction,
    PropertyAccessInstruction,
    NewInstruction,
    CommentInstruction
)

class TestTACInstructions(unittest.TestCase):
    """Test cases for TAC instruction classes."""

    def test_assign_instruction_binary(self):
        """Test binary assignment instruction: x = y op z"""
        instr = AssignInstruction("t1", "a", "+", "b")
        self.assertEqual(str(instr), "t1 = a + b")

    def test_assign_instruction_unary(self):
        """Test unary assignment instruction: x = op y"""
        instr = AssignInstruction("t1", "a", "-")
        self.assertEqual(str(instr), "t1 = - a")

    def test_assign_instruction_simple(self):
        """Test simple assignment instruction: x = y"""
        instr = AssignInstruction("t1", "a")
        self.assertEqual(str(instr), "t1 = a")

    def test_goto_instruction(self):
        """Test unconditional goto instruction."""
        instr = GotoInstruction("L1")
        self.assertEqual(str(instr), "goto L1")

    def test_conditional_goto_simple(self):
        """Test simple conditional goto: if x goto L"""
        instr = ConditionalGotoInstruction("t1", "L1")
        self.assertEqual(str(instr), "if t1 goto L1")

    def test_conditional_goto_relational(self):
        """Test relational conditional goto: if x relop y goto L"""
        instr = ConditionalGotoInstruction("a", "L1", "b", "<")
        self.assertEqual(str(instr), "if a < b goto L1")

    def test_label_instruction(self):
        """Test label instruction."""
        instr = LabelInstruction("L1")
        self.assertEqual(str(instr), "L1:")

    def test_begin_func_instruction(self):
        """Test function begin instruction."""
        instr = BeginFuncInstruction("main", 2)
        self.assertEqual(str(instr), "BeginFunc main, 2")

    def test_end_func_instruction(self):
        """Test function end instruction."""
        instr = EndFuncInstruction("main")
        self.assertEqual(str(instr), "EndFunc main")

    def test_push_param_instruction(self):
        """Test parameter push instruction."""
        instr = PushParamInstruction("a")
        self.assertEqual(str(instr), "PushParam a")

    def test_call_instruction(self):
        """Test function call instruction."""
        instr = CallInstruction("func", 2)
        self.assertEqual(str(instr), "call func, 2")

    def test_call_instruction_with_return(self):
        """Test function call with return value."""
        instr = CallInstruction("func", 2, "t1")
        self.assertEqual(str(instr), "t1 = call func, 2")

    def test_pop_params_instruction(self):
        """Test parameter pop instruction."""
        instr = PopParamsInstruction(2)
        self.assertEqual(str(instr), "PopParams 2")

    def test_return_instruction(self):
        """Test return instruction without value."""
        instr = ReturnInstruction()
        self.assertEqual(str(instr), "return")

    def test_return_instruction_with_value(self):
        """Test return instruction with value."""
        instr = ReturnInstruction("t1")
        self.assertEqual(str(instr), "return t1")

    def test_array_access_instruction(self):
        """Test array access instruction."""
        instr = ArrayAccessInstruction("t1", "arr", "i")
        self.assertEqual(str(instr), "t1 = arr[i]")

    def test_array_assignment_instruction(self):
        """Test array assignment instruction."""
        instr = ArrayAccessInstruction("value", "arr", "i", True)
        self.assertEqual(str(instr), "arr[i] = value")

    def test_property_access_instruction(self):
        """Test property access instruction."""
        instr = PropertyAccessInstruction("t1", "obj", "field")
        self.assertEqual(str(instr), "t1 = obj.field")

    def test_property_assignment_instruction(self):
        """Test property assignment instruction."""
        instr = PropertyAccessInstruction("value", "obj", "field", True)
        self.assertEqual(str(instr), "obj.field = value")

    def test_new_instruction(self):
        """Test object creation instruction."""
        instr = NewInstruction("t1", "MyClass")
        self.assertEqual(str(instr), "t1 = new MyClass")

    def test_comment_instruction(self):
        """Test comment instruction."""
        instr = CommentInstruction("This is a comment")
        self.assertEqual(str(instr), "# This is a comment")

if __name__ == '__main__':
    unittest.main()