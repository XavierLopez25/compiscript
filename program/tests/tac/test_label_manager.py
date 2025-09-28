import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.label_manager import LabelManager


class DummyGenerator:
    def __init__(self):
        self.counter = 0

    def __call__(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}{self.counter}"


class TestLabelManager(unittest.TestCase):
    """LabelManager behaviour specifications."""

    def setUp(self):
        self.generator = DummyGenerator()
        self.manager = LabelManager(self.generator)

    def test_unique_label_generation(self):
        first = self.manager.new_label()
        second = self.manager.new_label("LOOP")
        third = self.manager.new_label()

        self.assertEqual(first, "L1")
        self.assertEqual(second, "LOOP2")
        self.assertEqual(third, "L3")

    def test_loop_and_switch_contexts(self):
        break_label = self.manager.new_label("loop_break")
        continue_label = self.manager.new_label("loop_cont")
        switch_break = self.manager.new_label("switch_break")

        self.manager.push_loop(break_label, continue_label)
        self.assertTrue(self.manager.has_loop_context())
        self.assertEqual(self.manager.current_break_label(), break_label)
        self.assertEqual(self.manager.current_continue_label(), continue_label)

        self.manager.push_switch(switch_break)
        self.assertEqual(self.manager.current_break_label(), switch_break)

        self.manager.pop_switch()
        self.manager.pop_loop()
        self.assertFalse(self.manager.has_loop_context())

    def test_unresolved_label_tracking(self):
        label = self.manager.new_label("target")
        self.manager.reference_label(label)

        unresolved = self.manager.unresolved_labels()
        self.assertIn(label, unresolved)

        self.manager.define_label(label)
        self.assertEqual(self.manager.unresolved_labels(), [])


if __name__ == '__main__':
    unittest.main()
