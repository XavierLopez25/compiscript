import sys
import os
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_semantic_test(file_path: str, expect_success: bool = True):
    """
    Run semantic analysis on a test file.
    
    Args:
        file_path: Path to the .cps test file
        expect_success: True if the file should pass, False if it should fail
    
    Returns:
        tuple: (success, output, error_message)
    """
    try:
        # Run the semantic analyzer
        result = subprocess.run(
            [sys.executable, '../Driver.py', file_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        success = result.returncode == 0
        output = result.stdout
        error_msg = result.stderr
        
        # Check if result matches expectation
        test_passed = success == expect_success
        
        return test_passed, output, error_msg
        
    except Exception as e:
        return False, "", str(e)

def main():
    """Run all semantic analysis tests."""
    print("🧪 CompilScript Semantic Analysis Test Runner")
    print("=" * 50)
    
    test_dir = Path(__file__).parent / "test_cases"
    
    # Test results tracking
    total_tests = 0
    passed_tests = 0
    
    # Test success cases
    print("\n✅ Testing Success Cases...")
    success_file = test_dir / "success_cases.cps"
    if success_file.exists():
        total_tests += 1
        passed, output, error = run_semantic_test(str(success_file), expect_success=True)
        if passed:
            passed_tests += 1
            print(f"  ✓ {success_file.name} - PASSED")
        else:
            print(f"  ✗ {success_file.name} - FAILED")
            if error:
                print(f"    Error: {error}")
    
    # Test failure cases
    print("\n❌ Testing Failure Cases...")
    failure_dir = test_dir / "failure_cases"
    if failure_dir.exists():
        for failure_file in failure_dir.glob("*.cps"):
            total_tests += 1
            passed, output, error = run_semantic_test(str(failure_file), expect_success=False)
            if passed:
                passed_tests += 1
                print(f"  ✓ {failure_file.name} - PASSED (correctly failed)")
            else:
                print(f"  ✗ {failure_file.name} - FAILED (should have failed)")
                if output:
                    print(f"    Unexpected success output: {output}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results Summary")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests found")
    
    # Run Python unit tests if available
    print("\n🐍 Running Python Unit Tests...")
    try:
        result = subprocess.run(
            [sys.executable, 'test_semantic_analysis.py'],
            cwd=os.path.dirname(__file__)
        )
        if result.returncode == 0:
            print("  ✓ Python unit tests passed")
        else:
            print("  ✗ Python unit tests failed")
    except Exception as e:
        print(f"  ⚠ Could not run Python unit tests: {e}")
    
    return passed_tests == total_tests

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)