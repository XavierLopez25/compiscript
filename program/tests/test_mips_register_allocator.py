import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tac.address_manager import MemoryLocation
from mips import MIPSTranslatorBase


class TestMIPSRegisterAllocator(unittest.TestCase):
    """Unit tests for the Part 1 MIPS infrastructure."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0",))

    def test_allocate_register_loads_from_memory(self) -> None:
        """Reading a variable loads it from its canonical memory location."""
        self.translator.bind_memory_location(
            "x",
            MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False),
        )

        self.translator.set_liveness(set(), {})
        register, spills, loads = self.translator.acquire_register("x")

        self.assertEqual(register, "$t0")
        self.assertFalse(spills)
        self.assertEqual(len(loads), 1)

        self.translator.materialise_loads(loads)
        emitted = [str(node) for node in self.translator.text_section]
        self.assertIn("\tlw $t0, -4($fp)", emitted[0])

    def test_spilling_dirty_register_emits_store(self) -> None:
        """When the allocator needs a register it spills dirty values."""
        self.translator.bind_memory_location(
            "a",
            MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False),
        )
        self.translator.bind_memory_location(
            "b",
            MemoryLocation(address="fp-12", offset=-12, size=4, is_temporary=False),
        )

        self.translator.set_liveness({"a"}, {"a": 1})
        reg_a, spills, loads = self.translator.acquire_register("a", is_write=True)
        self.translator.materialise_spills(spills)
        self.translator.materialise_loads(loads)
        self.assertEqual(reg_a, "$t0")

        # Request another register, forcing a spill of the dirty value in $t0.
        self.translator.set_liveness(set(), {})
        reg_b, spill_actions, load_actions = self.translator.acquire_register("b")

        self.translator.materialise_spills(spill_actions)
        self.translator.materialise_loads(load_actions)

        emitted = [str(node) for node in self.translator.text_section]
        self.assertTrue(any("sw $t0, -8($fp)" in line for line in emitted))
        self.assertTrue(any("lw $t0, -12($fp)" in line for line in emitted))
        self.assertEqual(reg_b, "$t0")

    def test_spill_slot_tracking(self) -> None:
        """Registers without memory homes allocate spill slots on the stack."""
        self.translator.set_liveness(set(), {})
        register, spills, loads = self.translator.acquire_register("temp", is_write=True)

        self.assertEqual(register, "$t0")
        self.assertFalse(spills)
        self.assertFalse(loads)
        self.assertEqual(self.translator.required_spill_space, 4)


if __name__ == "__main__":
    unittest.main()
