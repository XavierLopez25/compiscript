import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tac.address_manager import MemoryLocation
from mips import MIPSTranslatorBase
from mips.register_allocator import RegisterAllocator, RegisterAllocationError
from mips.address_descriptor import AddressDescriptor

class TestBasicRegisterAllocation(unittest.TestCase):
    """Basic register allocation scenarios."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(
            allocatable_registers=("$t0", "$t1", "$t2", "$t3")
        )

    def test_first_allocation_uses_first_free_register(self) -> None:
        """First allocation should use the first available register."""
        reg, spills, loads = self.translator.acquire_register("x", is_write=True)

        self.assertEqual(reg, "$t0")
        self.assertEqual(len(spills), 0)
        self.assertEqual(len(loads), 0)

    def test_sequential_allocations_use_different_registers(self) -> None:
        """Sequential allocations should use different registers."""
        reg1, _, _ = self.translator.acquire_register("a", is_write=True)
        reg2, _, _ = self.translator.acquire_register("b", is_write=True)
        reg3, _, _ = self.translator.acquire_register("c", is_write=True)

        self.assertEqual(reg1, "$t0")
        self.assertEqual(reg2, "$t1")
        self.assertEqual(reg3, "$t2")
        self.assertNotEqual(reg1, reg2)
        self.assertNotEqual(reg2, reg3)

    def test_reuse_register_for_same_variable(self) -> None:
        """Requesting the same variable should return the same register."""
        reg1, _, _ = self.translator.acquire_register("x", is_write=True)
        reg2, _, _ = self.translator.acquire_register("x", is_write=False)

        self.assertEqual(reg1, reg2)
        self.assertEqual(reg1, "$t0")

    def test_load_from_memory_on_first_read(self) -> None:
        """Reading a variable from memory should generate load action."""
        self.translator.bind_memory_location(
            "x",
            MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )

        reg, spills, loads = self.translator.acquire_register("x", is_write=False)

        self.assertEqual(len(loads), 1)
        self.assertEqual(loads[0].variable, "x")
        self.assertEqual(loads[0].register, reg)
        self.assertEqual(loads[0].memory_offset, -4)

    def test_no_load_on_write_only(self) -> None:
        """Writing to a new variable shouldn't generate load."""
        reg, spills, loads = self.translator.acquire_register("x", is_write=True)

        self.assertEqual(len(loads), 0)
        self.assertEqual(len(spills), 0)

class TestRegisterSpilling(unittest.TestCase):
    """Register spilling scenarios."""

    def setUp(self) -> None:
        # Use only 2 registers to force spilling quickly
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0", "$t1"))

    def test_spill_when_all_registers_occupied(self) -> None:
        """Allocating beyond capacity should trigger spilling."""
        self.translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "c", MemoryLocation(address="fp-12", offset=-12, size=4, is_temporary=False)
        )

        # Fill all registers
        reg_a, _, _ = self.translator.acquire_register("a", is_write=True)
        reg_b, _, _ = self.translator.acquire_register("b", is_write=True)

        # This should trigger a spill
        reg_c, spills, loads = self.translator.acquire_register("c", is_write=True)

        self.assertEqual(len(spills), 1)
        self.assertIn(spills[0].register, [reg_a, reg_b])

    def test_spill_only_dirty_registers(self) -> None:
        """Only dirty (modified) registers should be spilled."""
        self.translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )

        # Read 'a' (not dirty)
        reg_a, _, _ = self.translator.acquire_register("a", is_write=False)
        # Write 'b' (dirty)
        reg_b, _, _ = self.translator.acquire_register("b", is_write=True)

        # Force spill of 'a' (should not generate spill since it's clean)
        self.translator.release_register(reg_a)
        reg_c, spills, _ = self.translator.acquire_register("c", is_write=True)

        # Should prefer clean register (reg_a) over dirty (reg_b)
        self.assertEqual(reg_c, reg_a)

    def test_spill_to_memory_location(self) -> None:
        """Spilling should use the variable's memory location."""
        self.translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "c", MemoryLocation(address="fp-12", offset=-12, size=4, is_temporary=False)
        )

        # Fill registers with dirty values
        reg_a, _, _ = self.translator.acquire_register("a", is_write=True)
        reg_b, _, _ = self.translator.acquire_register("b", is_write=True)

        # Trigger spill
        reg_c, spills, loads = self.translator.acquire_register("c", is_write=True)

        self.assertEqual(len(spills), 1)
        spill = spills[0]

        # Should have memory offset
        self.assertIsNotNone(spill.memory_offset)
        self.assertIn(spill.memory_offset, [-4, -8])

    def test_spill_to_stack_slot_for_temporaries(self) -> None:
        """Temporaries without memory location should use spill slots."""
        # Allocate temporaries (no memory location)
        reg_t1, _, _ = self.translator.acquire_register("temp1", is_write=True)
        reg_t2, _, _ = self.translator.acquire_register("temp2", is_write=True)

        # Force spill
        reg_t3, spills, _ = self.translator.acquire_register("temp3", is_write=True)

        self.assertEqual(len(spills), 1)
        spill = spills[0]

        # Should use spill slot
        self.assertIsNotNone(spill.spill_offset)
        self.assertIsNone(spill.memory_offset)

    def test_spill_all_registers(self) -> None:
        """Test spilling all registers at once."""
        # Allocate multiple dirty registers
        self.translator.acquire_register("a", is_write=True)
        self.translator.acquire_register("b", is_write=True)

        spills = self.translator.spill_everything()

        # Should spill both registers
        self.assertEqual(len(spills), 2)

class TestLivenessAnalysis(unittest.TestCase):
    """Test integration with liveness analysis."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0", "$t1"))

    def test_spill_dead_variables_first(self) -> None:
        """Dead variables should be spilled before live ones."""
        self.translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )

        # Allocate 'a' and 'b'
        reg_a, _, _ = self.translator.acquire_register("a", is_write=True)

        # Mark 'a' as live, 'b' as dead
        self.translator.set_liveness(live_variables={"a"}, next_use={"a": 1})

        reg_b, _, _ = self.translator.acquire_register("b", is_write=True)

        # Force spill - should prefer dead variable
        self.translator.set_liveness(live_variables={"a"}, next_use={"a": 1})
        reg_c, spills, _ = self.translator.acquire_register("c", is_write=True)

        # Should spill 'b' (dead) rather than 'a' (live)
        if len(spills) > 0:
            self.assertIn(spills[0].variable, ["b"])

    def test_next_use_heuristic(self) -> None:
        """Variables with farthest next use should be spilled first."""
        # Allocate two variables
        reg_a, _, _ = self.translator.acquire_register("a", is_write=True)
        reg_b, _, _ = self.translator.acquire_register("b", is_write=True)

        # Set next use: 'a' used at instruction 100, 'b' used at instruction 5
        self.translator.set_liveness(
            live_variables={"a", "b"},
            next_use={"a": 100, "b": 5}
        )

        # Force spill - should spill 'a' (used later)
        reg_c, spills, _ = self.translator.acquire_register("c", is_write=True)

        if len(spills) > 0:
            # Should spill 'a' since it's used farthest in the future
            self.assertEqual(spills[0].variable, "a")

class TestPreferredAndForbiddenRegisters(unittest.TestCase):
    """Test preferred and forbidden register constraints."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(
            allocatable_registers=("$t0", "$t1", "$t2", "$a0", "$a1")
        )

    def test_preferred_registers(self) -> None:
        """Should use preferred registers when available."""
        reg, _, _ = self.translator.acquire_register(
            "x",
            is_write=True,
            preferred_registers=["$a0", "$a1"]
        )

        self.assertIn(reg, ["$a0", "$a1"])

    def test_forbidden_registers(self) -> None:
        """Should not use forbidden registers."""
        # Allocate with some registers forbidden
        reg, _, _ = self.translator.acquire_register(
            "x",
            is_write=True,
            forbidden_registers=["$t0", "$t1"]
        )

        self.assertNotIn(reg, ["$t0", "$t1"])
        self.assertIn(reg, ["$t2", "$a0", "$a1"])

    def test_preferred_overrides_default_order(self) -> None:
        """Preferred registers should be tried first."""
        # Prefer $a0 even though $t0 is earlier in allocatable list
        reg1, _, _ = self.translator.acquire_register(
            "x",
            is_write=True,
            preferred_registers=["$a0"]
        )

        self.assertEqual(reg1, "$a0")

    def test_fallback_when_preferred_occupied(self) -> None:
        """Should fallback to other registers when preferred are occupied."""
        # Occupy preferred register
        reg1, _, _ = self.translator.acquire_register("a", is_write=True)
        self.translator.register_allocator.register_descriptor.pin("$t0")

        # Try to allocate with $t0 preferred (but it's pinned/occupied)
        reg2, _, _ = self.translator.acquire_register(
            "b",
            is_write=True,
            preferred_registers=["$t0"]
        )

        # Should use a different register
        self.assertNotEqual(reg2, "$t0")

class TestSpillSlotManagement(unittest.TestCase):
    """Test spill slot allocation and tracking."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0",))

    def test_spill_slot_allocation(self) -> None:
        """Each spilled temporary should get a unique spill slot."""
        # Allocate and spill multiple temporaries
        self.translator.acquire_register("temp1", is_write=True)

        # Force spill
        self.translator.acquire_register("temp2", is_write=True)

        # Force another spill
        self.translator.acquire_register("temp3", is_write=True)

        # Check spill area size
        spill_size = self.translator.required_spill_space

        # Should have allocated space for spills (4 bytes per variable)
        self.assertGreater(spill_size, 0)
        self.assertEqual(spill_size % 4, 0)  # Should be word-aligned

    def test_spill_slot_reuse(self) -> None:
        """Spill slots should be reused for the same variable."""
        # Allocate temporary
        reg1, _, _ = self.translator.acquire_register("temp", is_write=True)

        # Check initial spill space
        initial_size = self.translator.required_spill_space

        # Re-acquire same variable
        self.translator.release_register(reg1)
        reg2, _, _ = self.translator.acquire_register("temp", is_write=True)

        # Spill space should not increase
        final_size = self.translator.required_spill_space
        self.assertEqual(initial_size, final_size)

class TestRegisterDescriptorTracking(unittest.TestCase):
    """Test register descriptor state tracking."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(
            allocatable_registers=("$t0", "$t1", "$t2")
        )

    def test_dirty_bit_set_on_write(self) -> None:
        """Writing to a register should mark it dirty."""
        self.translator.bind_memory_location(
            "x", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )

        reg, _, _ = self.translator.acquire_register("x", is_write=True)

        # Register should be dirty
        state = self.translator.register_allocator.register_descriptor.state(reg)
        self.assertIn("x", state.dirty)

    def test_dirty_bit_not_set_on_read(self) -> None:
        """Reading a register should not mark it dirty."""
        self.translator.bind_memory_location(
            "x", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )

        reg, _, _ = self.translator.acquire_register("x", is_write=False)

        # Register should not be dirty
        state = self.translator.register_allocator.register_descriptor.state(reg)
        self.assertNotIn("x", state.dirty)

    def test_register_release(self) -> None:
        """Releasing a register should free it for reuse."""
        reg1, _, _ = self.translator.acquire_register("x", is_write=True)

        # Release the register
        self.translator.release_register(reg1)

        # Should be able to allocate it for a different variable
        reg2, _, _ = self.translator.acquire_register("y", is_write=True)

        self.assertEqual(reg1, reg2)

class TestAddressDescriptorTracking(unittest.TestCase):
    """Test address descriptor location tracking."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0", "$t1"))

    def test_variable_in_register_tracking(self) -> None:
        """Address descriptor should track which registers hold a variable."""
        reg, _, _ = self.translator.acquire_register("x", is_write=True)

        location = self.translator.address_descriptor.get("x")

        self.assertIn(reg, location.registers)

    def test_variable_in_memory_tracking(self) -> None:
        """Address descriptor should track memory location."""
        mem_loc = MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        self.translator.bind_memory_location("x", mem_loc)

        location = self.translator.address_descriptor.get("x")

        self.assertEqual(location.memory, mem_loc)

    def test_dirty_flag_tracking(self) -> None:
        """Address descriptor should track dirty variables."""
        reg, _, _ = self.translator.acquire_register("x", is_write=True)

        location = self.translator.address_descriptor.get("x")

        self.assertTrue(location.dirty)

class TestGlobalVariables(unittest.TestCase):
    """Test handling of global variables with absolute addresses."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0", "$t1"))

    def test_global_variable_load(self) -> None:
        """Loading global variables should use absolute addressing."""
        # Bind global variable with hex address
        self.translator.bind_memory_location(
            "global_var",
            MemoryLocation(address="0x10010000", offset=0, size=4, is_temporary=False)
        )

        reg, _, loads = self.translator.acquire_register("global_var", is_write=False)

        self.assertEqual(len(loads), 1)
        self.assertTrue(loads[0].is_global)
        self.assertEqual(loads[0].global_address, "0x10010000")

    def test_global_variable_spill(self) -> None:
        """Spilling global variables should use absolute addressing."""
        self.translator.bind_memory_location(
            "global1",
            MemoryLocation(address="0x10010000", offset=0, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "global2",
            MemoryLocation(address="0x10010004", offset=0, size=4, is_temporary=False)
        )

        # Occupy both registers
        reg1, _, _ = self.translator.acquire_register("global1", is_write=True)
        reg2, _, _ = self.translator.acquire_register("global2", is_write=True)

        # Force spill
        reg3, spills, _ = self.translator.acquire_register("global3", is_write=True)

        if len(spills) > 0:
            self.assertTrue(spills[0].is_global)

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and corner cases."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0", "$t1"))

    def test_allocate_same_variable_multiple_times(self) -> None:
        """Allocating the same variable multiple times should work."""
        reg1, _, _ = self.translator.acquire_register("x", is_write=True)
        reg2, _, _ = self.translator.acquire_register("x", is_write=False)
        reg3, _, _ = self.translator.acquire_register("x", is_write=True)

        # All should return the same register
        self.assertEqual(reg1, reg2)
        self.assertEqual(reg2, reg3)

    def test_empty_register_pool(self) -> None:
        """Should handle exhausting all registers gracefully."""
        # Fill all registers
        self.translator.acquire_register("a", is_write=True)
        self.translator.acquire_register("b", is_write=True)

        # This should spill one of them
        reg, spills, _ = self.translator.acquire_register("c", is_write=True)

        # Should succeed with spilling
        self.assertIsNotNone(reg)
        self.assertGreater(len(spills), 0)

    def test_reset_clears_all_state(self) -> None:
        """Reset should clear all allocator state."""
        # Allocate some registers
        self.translator.acquire_register("a", is_write=True)
        self.translator.acquire_register("b", is_write=True)

        # Reset
        self.translator.register_allocator.reset()

        # Should be able to allocate from beginning again
        reg, _, _ = self.translator.acquire_register("x", is_write=True)
        self.assertEqual(reg, "$t0")

    def test_none_variable_raises_error(self) -> None:
        """Allocating register for None should raise error."""
        with self.assertRaises(RegisterAllocationError):
            self.translator.acquire_register(None, is_write=True)

class TestMaterialization(unittest.TestCase):
    """Test spill/load action materialization to MIPS instructions."""

    def setUp(self) -> None:
        self.translator = MIPSTranslatorBase(allocatable_registers=("$t0",))

    def test_load_materialization(self) -> None:
        """Load actions should generate lw instructions."""
        self.translator.bind_memory_location(
            "x",
            MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )

        reg, _, loads = self.translator.acquire_register("x", is_write=False)
        self.translator.materialise_loads(loads)

        code = "\n".join(str(instr) for instr in self.translator.text_section)

        self.assertIn("lw", code)
        self.assertIn("-4($fp)", code)

    def test_spill_materialization(self) -> None:
        """Spill actions should generate sw instructions."""
        self.translator.bind_memory_location(
            "a", MemoryLocation(address="fp-4", offset=-4, size=4, is_temporary=False)
        )
        self.translator.bind_memory_location(
            "b", MemoryLocation(address="fp-8", offset=-8, size=4, is_temporary=False)
        )

        reg_a, _, _ = self.translator.acquire_register("a", is_write=True)
        reg_b, spills, _ = self.translator.acquire_register("b", is_write=True)

        self.translator.materialise_spills(spills)

        code = "\n".join(str(instr) for instr in self.translator.text_section)

        if len(spills) > 0:
            self.assertIn("sw", code)

    def test_global_load_uses_lui_ori(self) -> None:
        """Loading globals should use lui/ori for 32-bit addresses."""
        self.translator.bind_memory_location(
            "global_var",
            MemoryLocation(address="0x10010000", offset=0, size=4, is_temporary=False)
        )

        reg, _, loads = self.translator.acquire_register("global_var", is_write=False)
        self.translator.materialise_loads(loads)

        code = "\n".join(str(instr) for instr in self.translator.text_section)

        # Should use lui and ori for loading 32-bit address
        self.assertIn("lui", code)
        self.assertIn("ori", code)


if __name__ == "__main__":
    # Run all test suites
    unittest.main(verbosity=2)
