import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.control_flow_generator import ControlFlowTACGenerator
from tac.base_generator import TACGenerationError
from AST.ast_nodes import *


class TestControlFlowTACGenerator(unittest.TestCase):
    """Control-flow TAC generation scenarios."""

    def setUp(self):
        self.generator = ControlFlowTACGenerator()

    def _instruction_strings(self):
        return [str(instr) for instr in self.generator.get_instructions()]

    def test_if_statement_without_else(self):
        condition = Variable("cond")
        then_block = Block([AssignmentStatement(Variable("x"), Literal(1, Type.INTEGER))])
        node = IfStatement(condition, then_block)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertEqual(instructions[0], "if cond == 0 goto if_false1")
        self.assertEqual(instructions[1], "x = 1")
        self.assertEqual(instructions[-1], "if_false1:")

    def test_if_else_nested(self):
        inner_then = Block([AssignmentStatement(Variable("y"), Literal(2, Type.INTEGER))])
        inner_if = IfStatement(Variable("inner"), inner_then)
        outer_then = Block([AssignmentStatement(Variable("x"), Literal(1, Type.INTEGER))])
        outer_else = Block([inner_if])
        node = IfStatement(Variable("cond"), outer_then, outer_else)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertIn("if cond == 0 goto if_false1", instructions)
        self.assertIn("goto if_end2", instructions)
        self.assertIn("if_false1:", instructions)
        self.assertIn("if inner == 0 goto if_false3", instructions)
        self.assertIn("if_end2:", instructions)

    def test_while_with_break_and_continue(self):
        break_stmt = BreakStatement()
        continue_stmt = ContinueStatement()
        body = Block([
            IfStatement(Variable("stop"), Block([break_stmt])),
            continue_stmt,
            AssignmentStatement(Variable("i"), BinaryOperation(Variable("i"), Literal(1, Type.INTEGER), '+'))
        ])
        node = WhileStatement(Variable("cond"), body)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertIn("while_start1:", instructions)
        self.assertIn("if cond == 0 goto while_end2", instructions)
        self.assertIn("goto while_end2", instructions)
        self.assertIn("goto while_start1", instructions)
        self.assertEqual(instructions[-1], "while_end2:")

    def test_for_loop_with_continue(self):
        init = VariableDeclaration("i", TypeNode('integer'), Literal(0, Type.INTEGER))
        condition = BinaryOperation(Variable("i"), Literal(10, Type.INTEGER), '<')
        update = AssignmentStatement(Variable("i"), BinaryOperation(Variable("i"), Literal(1, Type.INTEGER), '+'))
        body = Block([
            AssignmentStatement(Variable("sum"), BinaryOperation(Variable("sum"), Variable("i"), '+')),
            ContinueStatement()
        ])
        node = ForStatement(init, condition, update, body)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertIn("i = 0", instructions)
        self.assertIn("for_cond1:", instructions)
        self.assertIn("if t1 == 0 goto for_end3", instructions)
        self.assertIn("goto for_update2", instructions)
        self.assertIn("for_update2:", instructions)
        self.assertIn("goto for_cond1", instructions)
        self.assertEqual(instructions[-1], "for_end3:")

    def test_do_while_loop(self):
        body = Block([AssignmentStatement(Variable("x"), Literal(5, Type.INTEGER))])
        node = DoWhileStatement(body, Variable("cond"))

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertEqual(instructions[0], "do_start1:")
        self.assertIn("do_cond2:", instructions)
        self.assertIn("if cond != 0 goto do_start1", instructions)
        self.assertIn("do_end3:", instructions)

    def test_switch_statement_with_default(self):
        case_one = SwitchCase(Literal(1, Type.INTEGER), [BreakStatement()])
        case_two = SwitchCase(Literal(2, Type.INTEGER), [AssignmentStatement(Variable("x"), Literal(2, Type.INTEGER))])
        default_block = [AssignmentStatement(Variable("x"), Literal(0, Type.INTEGER))]
        node = SwitchStatement(Variable("value"), [case_one, case_two], default_block)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertIn("if value == 1 goto case2", instructions)
        self.assertIn("if value == 2 goto case3", instructions)
        self.assertIn("goto switch_default4", instructions)
        self.assertIn("case2:", instructions)
        self.assertIn("case3:", instructions)
        self.assertIn("switch_default4:", instructions)
        self.assertTrue(any(instr.endswith("goto switch_end1") for instr in instructions if instr.startswith("goto")))
        self.assertIn("switch_end1:", instructions)

    def test_foreach_loop(self):
        body = Block([
            AssignmentStatement(Variable("sum"), BinaryOperation(Variable("sum"), Variable("item"), '+'))
        ])
        node = ForEachStatement("item", Variable("arr"), body)

        self.generator.visit(node)
        instructions = self._instruction_strings()

        self.assertIn("t1 = 0", instructions)
        self.assertIn("t2 = len arr", instructions)
        self.assertIn("foreach_start1:", instructions)
        self.assertIn("if t1 >= t2 goto foreach_end3", instructions)
        self.assertIn("t3 = arr[t1]", instructions)
        self.assertIn("item = t3", instructions)
        self.assertIn("foreach_continue2:", instructions)
        self.assertIn("t1 = t1 + 1", instructions)
        self.assertIn("foreach_end3:", instructions)

    def test_break_outside_loop_raises(self):
        with self.assertRaises(TACGenerationError):
            self.generator.visit(BreakStatement())

    def test_continue_outside_loop_raises(self):
        with self.assertRaises(TACGenerationError):
            self.generator.visit(ContinueStatement())

    def test_unresolved_labels_after_generation(self):
        node = WhileStatement(Variable("cond"), Block([]))
        self.generator.visit(node)
        self.assertEqual(self.generator.label_manager.unresolved_labels(), [])


if __name__ == '__main__':
    unittest.main()
