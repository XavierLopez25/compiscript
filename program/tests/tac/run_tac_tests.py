#!/usr/bin/env python3
"""
Test runner for TAC (Three Address Code) components.

This script runs all TAC-related tests and provides a comprehensive
report of the test results.
"""

import unittest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def run_tac_tests():
    """Run all TAC component tests."""
    # Discover and run all tests in the tac test directory
    loader = unittest.TestLoader()
    test_dir = os.path.dirname(__file__)
    suite = loader.discover(test_dir, pattern='test_*.py')

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*50)
    print("TAC TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1)) * 100:.1f}%")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tac_tests()
    sys.exit(0 if success else 1)