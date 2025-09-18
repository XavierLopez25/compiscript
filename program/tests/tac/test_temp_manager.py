import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.temp_manager import TemporaryManager, ScopedTemporaryManager

class TestTemporaryManager(unittest.TestCase):
    """Test cases for TemporaryManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_manager = TemporaryManager()

    def test_new_temp_creation(self):
        """Test creation of new temporary variables."""
        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()

        self.assertEqual(temp1, "t1")
        self.assertEqual(temp2, "t2")
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertIn(temp2, self.temp_manager.get_active_temps())

    def test_temp_release_and_reuse(self):
        """Test temporary variable release and reuse."""
        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()

        # Release temp1
        self.temp_manager.release_temp(temp1)
        self.assertNotIn(temp1, self.temp_manager.get_active_temps())
        self.assertIn(temp1, self.temp_manager.get_available_temps())

        # New temp should reuse released temp1
        temp3 = self.temp_manager.new_temp()
        self.assertEqual(temp3, temp1)
        self.assertIn(temp3, self.temp_manager.get_active_temps())
        self.assertNotIn(temp3, self.temp_manager.get_available_temps())

    def test_multiple_temp_release(self):
        """Test releasing multiple temporaries at once."""
        temps = [self.temp_manager.new_temp() for _ in range(3)]

        self.temp_manager.release_temps(temps[:2])

        for temp in temps[:2]:
            self.assertNotIn(temp, self.temp_manager.get_active_temps())
            self.assertIn(temp, self.temp_manager.get_available_temps())

        self.assertIn(temps[2], self.temp_manager.get_active_temps())

    def test_is_temporary(self):
        """Test temporary variable identification."""
        self.assertTrue(self.temp_manager.is_temporary("t1"))
        self.assertTrue(self.temp_manager.is_temporary("t123"))
        self.assertFalse(self.temp_manager.is_temporary("var"))
        self.assertFalse(self.temp_manager.is_temporary("temp1"))
        self.assertFalse(self.temp_manager.is_temporary("t"))

    def test_scope_management(self):
        """Test scope-based temporary management."""
        # Create temps in global scope
        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()

        # Enter new scope
        self.temp_manager.enter_scope()
        temp3 = self.temp_manager.new_temp()
        temp4 = self.temp_manager.new_temp()

        # Exit scope - should release temps created in inner scope
        self.temp_manager.exit_scope()

        # temp3 and temp4 should be released, temp1 and temp2 should remain active
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertIn(temp2, self.temp_manager.get_active_temps())
        self.assertNotIn(temp3, self.temp_manager.get_active_temps())
        self.assertNotIn(temp4, self.temp_manager.get_active_temps())

    def test_nested_scopes(self):
        """Test nested scope management."""
        temp1 = self.temp_manager.new_temp()

        # First level scope
        self.temp_manager.enter_scope()
        temp2 = self.temp_manager.new_temp()

        # Second level scope
        self.temp_manager.enter_scope()
        temp3 = self.temp_manager.new_temp()

        # Exit second level
        self.temp_manager.exit_scope()
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertIn(temp2, self.temp_manager.get_active_temps())
        self.assertNotIn(temp3, self.temp_manager.get_active_temps())

        # Exit first level
        self.temp_manager.exit_scope()
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertNotIn(temp2, self.temp_manager.get_active_temps())

    def test_temp_count(self):
        """Test temporary variable counting."""
        initial_count = self.temp_manager.get_temp_count()

        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()

        self.assertEqual(self.temp_manager.get_temp_count(), initial_count + 2)

        # Releasing doesn't change total count
        self.temp_manager.release_temp(temp1)
        self.assertEqual(self.temp_manager.get_temp_count(), initial_count + 2)

    def test_reset(self):
        """Test manager reset functionality."""
        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()
        self.temp_manager.enter_scope()

        self.temp_manager.reset()

        self.assertEqual(self.temp_manager.get_temp_count(), 0)
        self.assertEqual(len(self.temp_manager.get_active_temps()), 0)
        self.assertEqual(len(self.temp_manager.get_available_temps()), 0)

    def test_optimization_stats(self):
        """Test optimization statistics."""
        temp1 = self.temp_manager.new_temp()
        temp2 = self.temp_manager.new_temp()
        self.temp_manager.release_temp(temp1)

        stats = self.temp_manager.optimize_usage()

        self.assertEqual(stats['total_created'], 2)
        self.assertEqual(stats['active_count'], 1)
        self.assertEqual(stats['available_count'], 1)
        self.assertEqual(stats['recycling_efficiency'], 50.0)

class TestScopedTemporaryManager(unittest.TestCase):
    """Test cases for ScopedTemporaryManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_manager = ScopedTemporaryManager()

    def test_context_manager(self):
        """Test context manager functionality."""
        temp1 = self.temp_manager.new_temp()

        with self.temp_manager:
            temp2 = self.temp_manager.new_temp()
            temp3 = self.temp_manager.new_temp()

            self.assertIn(temp2, self.temp_manager.get_active_temps())
            self.assertIn(temp3, self.temp_manager.get_active_temps())

        # After exiting context, inner temps should be released
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertNotIn(temp2, self.temp_manager.get_active_temps())
        self.assertNotIn(temp3, self.temp_manager.get_active_temps())

    def test_with_scope_function(self):
        """Test with_scope method."""
        temp1 = self.temp_manager.new_temp()

        def inner_function():
            temp2 = self.temp_manager.new_temp()
            temp3 = self.temp_manager.new_temp()
            return temp2, temp3

        result = self.temp_manager.with_scope(inner_function)
        temp2, temp3 = result

        # After function execution, inner temps should be released
        self.assertIn(temp1, self.temp_manager.get_active_temps())
        self.assertNotIn(temp2, self.temp_manager.get_active_temps())
        self.assertNotIn(temp3, self.temp_manager.get_active_temps())

if __name__ == '__main__':
    unittest.main()