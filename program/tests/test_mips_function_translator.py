"""
Unit tests for MIPS Function Translator

Tests for Part 4/4: Function Calls, Activation Records & Peephole Optimization
"""

import os
import sys
import unittest
from typing import List

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tac.instruction import (
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
)

from mips.function_translator import FunctionTranslator
from mips.activation_record import ActivationRecordBuilder
from mips.calling_convention import CallingConvention
from mips.instruction import MIPSInstruction


class TestActivationRecord(unittest.TestCase):
    """Test activation record building and management."""

    def test_simple_activation_record(self):
        """Test building a simple activation record."""
        builder = ActivationRecordBuilder("test_func", param_count=2)
        builder.add_local_var("x", 4)
        builder.add_local_var("y", 4)
        record = builder.build()

        self.assertEqual(record.function_name, "test_func")
        self.assertEqual(record.param_count, 2)
        self.assertEqual(len(record.local_vars), 2)
        self.assertGreater(record.frame_size, 0)
        self.assertEqual(record.return_address_offset, -4)
        self.assertEqual(record.old_fp_offset, -8)

    def test_activation_record_with_saved_registers(self):
        """Test activation record with saved $s registers."""
        builder = ActivationRecordBuilder("test_func", param_count=1)
        builder.add_local_var("local", 4)
        builder.set_saved_registers(["$s0", "$s1", "$s2"])
        record = builder.build()

        self.assertEqual(len(record.saved_registers), 3)
        self.assertIn("$s0", record.saved_registers)

        # Check offsets
        s0_offset = record.get_saved_register_offset("$s0")
        self.assertIsNotNone(s0_offset)
        self.assertLess(s0_offset, 0)

    def test_frame_size_alignment(self):
        """Test that frame size is aligned to 8 bytes."""
        builder = ActivationRecordBuilder("test", param_count=0)
        builder.add_local_var("x", 1)  # 1 byte, but should align
        record = builder.build()

        # Frame size should be multiple of 8
        self.assertEqual(record.frame_size % 8, 0)

    def test_local_variable_offsets(self):
        """Test that local variables have correct offsets."""
        builder = ActivationRecordBuilder("test", param_count=0)
        builder.add_local_var("a", 4)
        builder.add_local_var("b", 4)
        builder.add_local_var("c", 4)
        record = builder.build()

        a_offset = record.get_local_offset("a")
        b_offset = record.get_local_offset("b")
        c_offset = record.get_local_offset("c")

        # All should be negative (below $fp)
        self.assertLess(a_offset, 0)
        self.assertLess(b_offset, 0)
        self.assertLess(c_offset, 0)

        # Should be 4 bytes apart
        self.assertEqual(b_offset - a_offset, -4)
        self.assertEqual(c_offset - b_offset, -4)


class TestCallingConvention(unittest.TestCase):
    """Test MIPS calling convention implementation."""

    def test_param_location_register(self):
        """Test that first 4 params go in $a0-$a3."""
        loc0 = CallingConvention.get_param_location(0, 4)
        loc1 = CallingConvention.get_param_location(1, 4)
        loc2 = CallingConvention.get_param_location(2, 4)
        loc3 = CallingConvention.get_param_location(3, 4)

        self.assertTrue(loc0.in_register)
        self.assertEqual(loc0.register, "$a0")
        self.assertTrue(loc1.in_register)
        self.assertEqual(loc1.register, "$a1")
        self.assertTrue(loc2.in_register)
        self.assertEqual(loc2.register, "$a2")
        self.assertTrue(loc3.in_register)
        self.assertEqual(loc3.register, "$a3")

    def test_param_location_stack(self):
        """Test that params 5+ go on stack."""
        loc4 = CallingConvention.get_param_location(4, 6)
        loc5 = CallingConvention.get_param_location(5, 6)

        self.assertFalse(loc4.in_register)
        self.assertIsNotNone(loc4.stack_offset)
        self.assertEqual(loc4.stack_offset, 0)  # First stack param

        self.assertFalse(loc5.in_register)
        self.assertEqual(loc5.stack_offset, 4)  # Second stack param

    def test_calling_context_creation(self):
        """Test creating a calling context."""
        context = CallingConvention.create_calling_context("foo", 6, True)

        self.assertEqual(context.function_name, "foo")
        self.assertEqual(context.param_count, 6)
        self.assertTrue(context.has_return_value)
        self.assertEqual(len(context.param_locations), 6)
        self.assertEqual(context.stack_space_needed, 8)  # 2 params * 4 bytes

    def test_push_param_constant(self):
        """Test pushing a constant parameter."""
        loc = CallingConvention.get_param_location(0, 1)
        instrs = CallingConvention.generate_push_param("42", loc)

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "li")
        self.assertEqual(instrs[0].operands[0], "$a0")
        self.assertEqual(instrs[0].operands[1], "42")

    def test_push_param_register(self):
        """Test pushing a register parameter."""
        loc = CallingConvention.get_param_location(0, 1)
        instrs = CallingConvention.generate_push_param("$t0", loc)

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "move")
        self.assertEqual(instrs[0].operands[0], "$a0")
        self.assertEqual(instrs[0].operands[1], "$t0")

    def test_pop_params(self):
        """Test popping parameters from stack."""
        # First 4 params don't need popping
        instrs = CallingConvention.generate_pop_params(4)
        self.assertEqual(len(instrs), 0)

        # 6 params means 2 on stack
        instrs = CallingConvention.generate_pop_params(6)
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "addi")
        self.assertEqual(instrs[0].operands[2], "8")  # 2 * 4 bytes

    def test_function_call_generation(self):
        """Test generating function call instruction."""
        instrs = CallingConvention.generate_function_call("my_func")

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "jal")
        self.assertEqual(instrs[0].operands[0], "my_func")

    def test_return_value_retrieval(self):
        """Test retrieving return value from $v0."""
        instrs = CallingConvention.generate_return_value_retrieval("result")

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "sw")
        self.assertEqual(instrs[0].operands[0], "$v0")

    def test_return_statement_constant(self):
        """Test return statement with constant."""
        instrs = CallingConvention.generate_return_statement("42")

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "li")
        self.assertEqual(instrs[0].operands[0], "$v0")
        self.assertEqual(instrs[0].operands[1], "42")

    def test_return_statement_register(self):
        """Test return statement with register."""
        instrs = CallingConvention.generate_return_statement("$t0")

        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "move")
        self.assertEqual(instrs[0].operands[0], "$v0")
        self.assertEqual(instrs[0].operands[1], "$t0")

    def test_caller_saved_registers(self):
        """Test caller-saved register list."""
        caller_saved = CallingConvention.get_caller_saved_registers()

        self.assertIn("$t0", caller_saved)
        self.assertIn("$a0", caller_saved)
        self.assertIn("$v0", caller_saved)
        self.assertNotIn("$s0", caller_saved)

    def test_callee_saved_registers(self):
        """Test callee-saved register list."""
        callee_saved = CallingConvention.get_callee_saved_registers()

        self.assertIn("$s0", callee_saved)
        self.assertIn("$fp", callee_saved)
        self.assertIn("$ra", callee_saved)
        self.assertNotIn("$t0", callee_saved)


class TestFunctionTranslator(unittest.TestCase):
    """Test function translator."""

    def setUp(self):
        """Set up test fixtures."""
        self.translator = FunctionTranslator()

    def test_translate_begin_func(self):
        """Test translating BeginFunc instruction."""
        instr = BeginFuncInstruction("test_func", 2)
        self.translator.translate_begin_func(instr)

        # Should generate prologue
        mips_code = self.translator.program_as_string()
        self.assertIn("addi", mips_code)  # Frame allocation
        self.assertIn("sw", mips_code)  # Save registers

    def test_translate_end_func(self):
        """Test translating EndFunc instruction."""
        # Need BeginFunc first
        begin = BeginFuncInstruction("test_func", 0)
        self.translator.translate_begin_func(begin)

        end = EndFuncInstruction("test_func")
        self.translator.translate_end_func(end)

        mips_code = self.translator.program_as_string()
        self.assertIn("lw", mips_code)  # Restore registers
        self.assertIn("jr", mips_code)  # Return

    def test_translate_simple_call(self):
        """Test translating a simple function call."""
        # Push 2 parameters
        push1 = PushParamInstruction("5")
        push2 = PushParamInstruction("3")
        self.translator.translate_push_param(push1)
        self.translator.translate_push_param(push2)

        # Call function
        call = CallInstruction("add_func", 2, "result")
        self.translator.translate_call(call)

        mips_code = self.translator.program_as_string()
        self.assertIn("$a0", mips_code)  # First param
        self.assertIn("$a1", mips_code)  # Second param
        self.assertIn("jal", mips_code)  # Call
        self.assertIn("add_func", mips_code)

    def test_translate_call_with_stack_params(self):
        """Test function call with more than 4 parameters."""
        # Push 6 parameters
        for i in range(6):
            push = PushParamInstruction(str(i))
            self.translator.translate_push_param(push)

        # Call function
        call = CallInstruction("multi_param_func", 6, None)
        self.translator.translate_call(call)

        mips_code = self.translator.program_as_string()
        # Should have register params and stack params
        self.assertIn("$a0", mips_code)
        self.assertIn("$sp", mips_code)  # Stack operations

    def test_translate_pop_params(self):
        """Test translating PopParams instruction."""
        pop = PopParamsInstruction(6)
        self.translator.translate_pop_params(pop)

        mips_code = self.translator.program_as_string()
        # Should adjust stack pointer
        self.assertIn("addi", mips_code)
        self.assertIn("$sp", mips_code)

    def test_translate_return_with_value(self):
        """Test return statement with value."""
        # Need function context
        begin = BeginFuncInstruction("test", 0)
        self.translator.translate_begin_func(begin)

        ret = ReturnInstruction("42")
        self.translator.translate_return(ret)

        mips_code = self.translator.program_as_string()
        self.assertIn("$v0", mips_code)  # Return value register

    def test_translate_return_void(self):
        """Test return statement without value."""
        # Need function context
        begin = BeginFuncInstruction("test", 0)
        self.translator.translate_begin_func(begin)

        ret = ReturnInstruction(None)
        self.translator.translate_return(ret)

        # Should still generate epilogue
        mips_code = self.translator.program_as_string()
        self.assertIn("jr", mips_code)

    def test_complete_function_translation(self):
        """Test translating a complete function."""
        # Function definition
        begin = BeginFuncInstruction("add_two", 2)
        self.translator.translate_begin_func(begin)

        # Function body would go here (handled by other translators)

        # Return
        ret = ReturnInstruction("result")
        self.translator.translate_return(ret)

        end = EndFuncInstruction("add_two")
        self.translator.translate_end_func(end)

        mips_code = self.translator.program_as_string()

        # Verify prologue
        self.assertIn("addi $sp", mips_code)  # Allocate frame
        self.assertIn("sw $ra", mips_code)  # Save return address
        self.assertIn("sw $fp", mips_code)  # Save frame pointer

        # Verify epilogue
        self.assertIn("lw $ra", mips_code)  # Restore return address
        self.assertIn("lw $fp", mips_code)  # Restore frame pointer
        self.assertIn("jr $ra", mips_code)  # Return

    def test_nested_function_calls(self):
        """Test translating nested function calls."""
        # Call to inner function
        push1 = PushParamInstruction("10")
        self.translator.translate_push_param(push1)
        call1 = CallInstruction("inner", 1, "temp")
        self.translator.translate_call(call1)
        pop1 = PopParamsInstruction(1)
        self.translator.translate_pop_params(pop1)

        # Call to outer function using result
        push2 = PushParamInstruction("temp")
        self.translator.translate_push_param(push2)
        call2 = CallInstruction("outer", 1, "result")
        self.translator.translate_call(call2)
        pop2 = PopParamsInstruction(1)
        self.translator.translate_pop_params(pop2)

        mips_code = self.translator.program_as_string()
        # Should have both function calls
        self.assertIn("inner", mips_code)
        self.assertIn("outer", mips_code)


class TestPeepholeOptimizer(unittest.TestCase):
    """Test peephole optimizer."""

    def setUp(self):
        """Set up test fixtures."""
        from mips.peephole_optimizer import PeepholeOptimizer
        self.optimizer = PeepholeOptimizer()

    def test_redundant_load_elimination(self):
        """Test elimination of redundant load-store pairs."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("lw", ("$t0", "x")),
            MIPSInstruction("sw", ("$t0", "x")),  # Redundant
        ]

        optimized = optimizer.optimize(instructions)
        self.assertEqual(len(optimized), 1)
        self.assertEqual(optimized[0].opcode, "lw")

    def test_algebraic_simplification(self):
        """Test algebraic simplifications."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("add", ("$t0", "$t1", "$zero")),
        ]

        optimized = optimizer.optimize(instructions)
        self.assertEqual(len(optimized), 1)
        self.assertEqual(optimized[0].opcode, "move")

    def test_strength_reduction(self):
        """Test strength reduction (mul → sll)."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("mul", ("$t0", "$t1", "4")),
        ]

        optimized = optimizer.optimize(instructions)
        self.assertEqual(len(optimized), 1)
        self.assertEqual(optimized[0].opcode, "sll")
        self.assertEqual(optimized[0].operands[2], "2")  # log2(4)

    def test_constant_folding(self):
        """Test constant folding."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("li", ("$t0", "5")),
            MIPSInstruction("li", ("$t1", "3")),
            MIPSInstruction("add", ("$t2", "$t0", "$t1")),
        ]

        optimized = optimizer.optimize(instructions)
        # Should fold to li $t2, 8
        has_folded = any(
            isinstance(i, MIPSInstruction) and i.opcode == "li" and "$t2" in i.operands and "8" in i.operands
            for i in optimized
        )
        self.assertTrue(has_folded)

    def test_redundant_move_elimination(self):
        """Test elimination of redundant moves."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("move", ("$t0", "$t0")),  # Redundant
        ]

        optimized = optimizer.optimize(instructions)
        self.assertEqual(len(optimized), 0)

    def test_optimization_stats(self):
        """Test that optimizer tracks statistics."""
        from mips.peephole_optimizer import PeepholeOptimizer
        optimizer = PeepholeOptimizer()

        instructions = [
            MIPSInstruction("add", ("$t0", "$t1", "$zero")),
            MIPSInstruction("mul", ("$t2", "$t3", "2")),
        ]

        optimizer.optimize(instructions)
        stats = optimizer.get_stats()

        self.assertGreater(stats.total_optimizations(), 0)
        self.assertGreater(stats.passes_executed, 0)


if __name__ == "__main__":
    unittest.main()
