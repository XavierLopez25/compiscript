import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.address_manager import AddressManager, ActivationRecord, MemoryLocation

class TestAddressManager(unittest.TestCase):
    """Test cases for AddressManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.addr_manager = AddressManager()

    def test_global_variable_allocation(self):
        """Test global variable allocation."""
        location = self.addr_manager.allocate_global_var("global_var", 4)

        self.assertEqual(location.address, "global_global_var")
        self.assertEqual(location.size, 4)
        self.assertFalse(location.is_temporary)

        # Allocating same variable should return same location
        location2 = self.addr_manager.allocate_global_var("global_var", 4)
        self.assertEqual(location.address, location2.address)

    def test_activation_record_creation(self):
        """Test activation record creation."""
        params = ["param1", "param2"]
        record = self.addr_manager.create_activation_record("test_func", params)

        self.assertEqual(record.function_name, "test_func")
        self.assertEqual(record.parameters, params)
        self.assertIn("param1", record.local_vars)
        self.assertIn("param2", record.local_vars)

        # Parameters should have positive offsets
        self.assertGreater(record.local_vars["param1"], 0)
        self.assertGreater(record.local_vars["param2"], 0)

    def test_local_variable_allocation(self):
        """Test local variable allocation within activation record."""
        params = ["param1"]
        self.addr_manager.create_activation_record("test_func", params)

        location = self.addr_manager.allocate_local_var("local_var", 4)

        self.assertTrue(location.address.startswith("fp"))
        self.assertEqual(location.size, 4)
        self.assertFalse(location.is_temporary)

    def test_temporary_variable_allocation(self):
        """Test temporary variable allocation."""
        params = ["param1"]
        self.addr_manager.create_activation_record("test_func", params)

        location = self.addr_manager.allocate_temp_var("t1", 4)

        self.assertTrue(location.address.startswith("fp"))
        self.assertEqual(location.size, 4)
        self.assertTrue(location.is_temporary)

    def test_variable_location_lookup(self):
        """Test variable location lookup."""
        # Test global variable lookup
        self.addr_manager.allocate_global_var("global_var", 4)
        location = self.addr_manager.get_variable_location("global_var")
        self.assertIsNotNone(location)
        self.assertEqual(location.address, "global_global_var")

        # Test local variable lookup
        params = ["param1"]
        self.addr_manager.create_activation_record("test_func", params)
        self.addr_manager.allocate_local_var("local_var", 4)

        location = self.addr_manager.get_variable_location("local_var")
        self.assertIsNotNone(location)
        self.assertTrue(location.address.startswith("fp"))

        # Test parameter lookup
        location = self.addr_manager.get_variable_location("param1")
        self.assertIsNotNone(location)
        self.assertTrue(location.address.startswith("fp"))

        # Test non-existent variable
        location = self.addr_manager.get_variable_location("non_existent")
        self.assertIsNone(location)

    def test_function_scope_management(self):
        """Test function scope entry and exit."""
        # Enter function
        params = ["param1", "param2"]
        record = self.addr_manager.enter_function("test_func", params)

        self.assertEqual(self.addr_manager.get_current_function(), "test_func")
        self.assertIsNotNone(record)

        # Exit function
        exited_record = self.addr_manager.exit_function()
        self.assertEqual(exited_record.function_name, "test_func")
        self.assertIsNone(self.addr_manager.get_current_function())

    def test_nested_function_scopes(self):
        """Test nested function scopes."""
        # Enter first function
        self.addr_manager.enter_function("func1", ["p1"])
        self.assertEqual(self.addr_manager.get_current_function(), "func1")

        # Enter second function
        self.addr_manager.enter_function("func2", ["p2"])
        self.assertEqual(self.addr_manager.get_current_function(), "func2")

        # Exit second function
        self.addr_manager.exit_function()
        self.assertEqual(self.addr_manager.get_current_function(), "func1")

        # Exit first function
        self.addr_manager.exit_function()
        self.assertIsNone(self.addr_manager.get_current_function())

    def test_label_generation(self):
        """Test unique label generation."""
        label1 = self.addr_manager.generate_label()
        label2 = self.addr_manager.generate_label()
        label3 = self.addr_manager.generate_label("LOOP")

        self.assertEqual(label1, "L1")
        self.assertEqual(label2, "L2")
        self.assertEqual(label3, "LOOP3")

        # Labels should be unique
        self.assertNotEqual(label1, label2)

    def test_activation_record_size(self):
        """Test activation record size calculation."""
        params = ["param1", "param2"]
        self.addr_manager.enter_function("test_func", params)

        # Add local variables
        self.addr_manager.allocate_local_var("local1", 4)
        self.addr_manager.allocate_local_var("local2", 4)

        # Add temporary variables
        self.addr_manager.allocate_temp_var("t1", 4)
        self.addr_manager.allocate_temp_var("t2", 4)

        size = self.addr_manager.get_activation_record_size()
        self.assertGreater(size, 0)

        # The actual size calculation is based on max(initial_size, largest_negative_offset + size)
        # Initial: 8 (ret addr + fp) + 2 params * 4 = 16
        # locals: local1 at -4, local2 at -8
        # temps: t1 at -12, t2 at -16 (largest offset)
        # Final size: max(16, 16 + 4) = 20
        expected_size = 20
        self.assertEqual(size, expected_size)

    def test_reset_functionality(self):
        """Test address manager reset."""
        # Create some state
        self.addr_manager.allocate_global_var("global_var", 4)
        self.addr_manager.enter_function("test_func", ["param1"])
        self.addr_manager.generate_label()

        # Reset
        self.addr_manager.reset()

        # Check state is cleared
        self.assertIsNone(self.addr_manager.get_current_function())
        self.assertIsNone(self.addr_manager.get_variable_location("global_var"))

        # Next label should start from 1 again
        label = self.addr_manager.generate_label()
        self.assertEqual(label, "L1")

    def test_statistics(self):
        """Test address manager statistics."""
        # Create some state
        self.addr_manager.allocate_global_var("global1", 4)
        self.addr_manager.allocate_global_var("global2", 8)
        self.addr_manager.enter_function("test_func", ["param1"])
        self.addr_manager.generate_label()
        self.addr_manager.generate_label()

        stats = self.addr_manager.get_statistics()

        self.assertEqual(stats['global_vars_count'], 2)
        self.assertEqual(stats['global_memory_size'], 12)  # 4 + 8
        self.assertEqual(stats['active_functions'], 1)
        self.assertEqual(stats['labels_generated'], 2)
        self.assertGreater(stats['current_stack_size'], 0)

class TestActivationRecord(unittest.TestCase):
    """Test cases for ActivationRecord class."""

    def test_activation_record_creation(self):
        """Test activation record instantiation."""
        params = ["param1", "param2"]
        record = ActivationRecord(
            function_name="test_func",
            parameters=params,
            local_vars={},
            temp_vars={}
        )

        self.assertEqual(record.function_name, "test_func")
        self.assertEqual(record.parameters, params)
        self.assertEqual(record.total_size, 0)
        self.assertEqual(record.frame_pointer_offset, 4)

class TestMemoryLocation(unittest.TestCase):
    """Test cases for MemoryLocation class."""

    def test_memory_location_creation(self):
        """Test memory location instantiation."""
        location = MemoryLocation(
            address="fp-8",
            offset=-8,
            size=4,
            is_temporary=True
        )

        self.assertEqual(location.address, "fp-8")
        self.assertEqual(location.offset, -8)
        self.assertEqual(location.size, 4)
        self.assertTrue(location.is_temporary)

if __name__ == '__main__':
    unittest.main()