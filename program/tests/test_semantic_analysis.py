import sys
import os
import time
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from SemanticVisitor import SemanticVisitor
from AST.symbol_table import SemanticError


class TestSemanticAnalysis(unittest.TestCase):
    """Test suite for CompilScript semantic analysis."""
    
    def setUp(self):
        """Set up test fixture."""
        pass
    
    def parse_and_analyze(self, code: str):
        """Parse code and run semantic analysis."""
        visitor = SemanticVisitor()  # Create fresh visitor for each analysis
        input_stream = InputStream(code)
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = CompiscriptParser(stream)
        tree = parser.program()
        return visitor.visit(tree)
    
    def assert_semantic_error(self, code: str, expected_message_contains: str = None):
        """Assert that code raises a SemanticError."""
        with self.assertRaises(SemanticError) as context:
            self.parse_and_analyze(code)
        if expected_message_contains:
            self.assertIn(expected_message_contains, str(context.exception))


class TestTypeSystem(TestSemanticAnalysis):
    """Test cases for type system validation."""
    
    def test_arithmetic_operations_success(self):
        """Test successful arithmetic operations with compatible types."""
        # Integer arithmetic
        code = """
        var a: integer = 5;
        var b: integer = 3;
        var c: integer = a + b;
        var d: integer = a - b;
        var e: integer = a * b;
        var f: integer = a / b;
        """
        self.parse_and_analyze(code)
        
        # Integer arithmetic with different variables
        code = """
        var a2: integer = 5;
        var b2: integer = 3;
        var c2: integer = a2 + b2;
        var d2: integer = a2 - b2;
        var e2: integer = a2 * b2;
        var f2: integer = a2 / b2;
        """
        self.parse_and_analyze(code)

        # String arithmetic
        code = """
        var a: string = "hello";
        var b: string = "world";
        var c: string = a + b;
        """
        self.parse_and_analyze(code)
        
    
    def test_arithmetic_operations_failure(self):
        """Test arithmetic operations with incompatible types."""
        
        # Boolean arithmetic
        code = """
        var a: boolean = true;
        var b: boolean = false;
        var c: boolean = a + b;
        """
        self.assert_semantic_error(code)
    
    def test_logical_operations_success(self):
        """Test successful logical operations with boolean types."""
        code = """
        var a: boolean = true;
        var b: boolean = false;
        var c: boolean = a && b;
        var d: boolean = a || b;
        var e: boolean = !a;
        """
        self.parse_and_analyze(code)
    
    def test_logical_operations_failure(self):
        """Test logical operations with non-boolean types."""
        code = """
        var a: integer = 5;
        var b: integer = 3;
        var c: boolean = a && b;
        """
        self.assert_semantic_error(code)
    
    def test_comparison_operations_success(self):
        """Test successful comparison operations."""
        code = """
        var a: integer = 5;
        var b: integer = 3;
        var c: boolean = a == b;
        var d: boolean = a != b;
        var e: boolean = a < b;
        var f: boolean = a <= b;
        var g: boolean = a > b;
        var h: boolean = a >= b;
        """
        self.parse_and_analyze(code)
    
    def test_comparison_operations_failure(self):
        """Test comparison operations with incompatible types."""
        code = """
        var a: integer = 5;
        var b: string = "hello";
        var c: boolean = a == b;
        """
        self.assert_semantic_error(code)
    
    def test_assignment_type_compatibility_success(self):
        """Test successful type-compatible assignments."""
        code = """
        var a: integer = 5;
        var c: string = "hello";
        var d: boolean = true;
        """
        self.parse_and_analyze(code)
    
    def test_assignment_type_compatibility_failure(self):
        """Test assignment with incompatible types."""
        code = """
        var a: integer = "hello";
        """
        self.assert_semantic_error(code)
    
    def test_const_initialization_success(self):
        """Test successful const initialization."""
        code = """
        const a: integer = 5;
        const b: string = "hello";
        """
        self.parse_and_analyze(code)
    
    def test_const_reassignment_failure(self):
        """Test const reassignment after initialization."""
        code = """
        const a: integer = 5;
        a = 10;
        """
        self.assert_semantic_error(code)


class TestScopeManagement(TestSemanticAnalysis):
    """Test cases for scope management."""
    
    def test_variable_resolution_success(self):
        """Test successful variable resolution in different scopes."""
        code = """
        var global: integer = 10;
        
        function test(): void {
            var local: integer = 5;
            global = local;
        }
        """
        self.parse_and_analyze(code)
    
    def test_undeclared_variable_failure(self):
        """Test error for undeclared variable usage."""
        code = """
        function test(): void {
            undeclared = 5;
        }
        """
        self.assert_semantic_error(code, "no declarado")
    
    def test_redeclaration_failure(self):
        """Test error for identifier redeclaration in same scope."""
        code = """
        var a: integer = 5;
        var a: string = "hello";
        """
        self.assert_semantic_error(code, "ya existe")
    
    def test_nested_scope_access_success(self):
        """Test correct access to variables in nested blocks."""
        code = """
        var outer: integer = 10;
        {
            var inner: integer = 5;
            outer = inner;
        }
        """
        self.parse_and_analyze(code)
    
    def test_scope_isolation_success(self):
        """Test that inner scope variables don't leak to outer scope."""
        code = """
        {
            var inner: integer = 5;
        }
        var outer: integer = 10;
        """
        self.parse_and_analyze(code)


class TestFunctionsAndProcedures(TestSemanticAnalysis):
    """Test cases for functions and procedures."""
    
    def test_function_call_argument_validation_success(self):
        """Test successful function call with correct arguments."""
        code = """
        function add(a: integer, b: integer): integer {
            return a + b;
        }
        
        var result: integer = add(5, 3);
        """
        self.parse_and_analyze(code)
    
    def test_function_call_argument_validation_failure(self):
        """Test function call with wrong number of arguments."""
        code = """
        function add(a: integer, b: integer): integer {
            return a + b;
        }
        
        var result: integer = add(5);
        """
        self.assert_semantic_error(code)
    
    def test_return_type_validation_success(self):
        """Test successful return type validation."""
        code = """
        function getNumber(): integer {
            return 42;
        }
        """
        self.parse_and_analyze(code)
    
    def test_return_type_validation_failure(self):
        """Test return type mismatch."""
        code = """
        function getNumber(): integer {
            return "hello";
        }
        """
        self.assert_semantic_error(code)
    
    def test_recursive_functions_success(self):
        """Test successful recursive function."""
        code = """
        function factorial(n: integer): integer {
            if (n <= 1) {
                return 1;
            }
            return n * factorial(n - 1);
        }
        """
        self.parse_and_analyze(code)
    
    def test_function_redeclaration_failure(self):
        """Test error for multiple function declarations with same name."""
        code = """
        function test(): void { }
        function test(): integer { return 1; }
        """
        self.assert_semantic_error(code, "ya existe")


class TestControlFlow(TestSemanticAnalysis):
    """Test cases for control flow validation."""
    
    def test_boolean_conditions_success(self):
        """Test successful boolean conditions in control structures."""
        code = """
        var condition: boolean = true;
        
        if (condition) {
            // do something
        }
        
        while (condition) {
            condition = false;
        }
        
        for (var i: integer = 0; i < 10; i = i + 1) {
            // loop body
        }
        """
        self.parse_and_analyze(code)
    
    def test_non_boolean_conditions_failure(self):
        """Test error for non-boolean conditions."""
        code = """
        var number: integer = 5;
        if (number) {
            // this should fail
        }
        """
        self.assert_semantic_error(code)
    
    def test_break_continue_in_loops_success(self):
        """Test successful break and continue within loops."""
        code = """
        for (var i: integer = 0; i < 10; i = i + 1) {
            if (i == 5) {
                break;
            }
            if (i == 3) {
                continue;
            }
        }
        """
        self.parse_and_analyze(code)
    
    def test_break_continue_outside_loops_failure(self):
        """Test error for break/continue outside loops."""
        code = """
        function test(): void {
            break;
        }
        """
        self.assert_semantic_error(code)
    
    def test_return_in_function_success(self):
        """Test successful return within function."""
        code = """
        function test(): integer {
            return 42;
        }
        """
        self.parse_and_analyze(code)
    
    def test_return_outside_function_failure(self):
        """Test error for return outside function."""
        code = """
        return 42;
        """
        self.assert_semantic_error(code)


class TestClassesAndObjects(TestSemanticAnalysis):
    """Test cases for classes and objects."""
    
    def test_property_access_success(self):
        """Test successful property access."""
        code = """
        class Person {
            var name: string;
            var age: integer;
            
            function constructor(name: string, age: integer): void {
                this.name = name;
                this.age = age;
            }
            
            function getName(): string {
                return this.name;
            }
        }
        
        var person: Person = new Person("John", 25);
        var name: string = person.getName();
        """
        self.parse_and_analyze(code)
    
    def test_property_access_failure(self):
        """Test error for accessing non-existent property."""
        code = """
        class Person {
            var name: string;
            function constructor(): void { }
        }
        
        var person: Person = new Person();
        var invalid = person.nonExistent;
        """
        self.assert_semantic_error(code, "does not exist")
    
    def test_constructor_validation_success(self):
        """Test successful constructor call."""
        code = """
        class Point {
            var x: integer;
            var y: integer;
            
            function constructor(x: integer, y: integer): void {
                this.x = x;
                this.y = y;
            }
        }
        
        var point: Point = new Point(10, 20);
        """
        self.parse_and_analyze(code)
    
    def test_this_reference_success(self):
        """Test successful this reference within class methods."""
        code = """
        class Counter {
            var value: integer;
            
            function constructor(): void {
                this.value = 0;
            }
            
            function increment(): void {
                this.value = this.value + 1;
            }
        }
        """
        self.parse_and_analyze(code)


class TestArraysAndDataStructures(TestSemanticAnalysis):
    """Test cases for arrays and data structures."""
    
    def test_array_element_type_verification_success(self):
        """Test successful array with consistent element types."""
        code = """
        var numbers: integer[] = [1, 2, 3, 4, 5];
        var strings: string[] = ["hello", "world"];
        """
        self.parse_and_analyze(code)
    
    def test_array_element_type_verification_failure(self):
        """Test error for array with inconsistent element types."""
        code = """
        var mixed = [1, "hello", true];
        """
        self.assert_semantic_error(code)
    
    def test_array_index_validation_success(self):
        """Test successful array index access."""
        code = """
        var numbers: integer[] = [1, 2, 3];
        var first: integer = numbers[0];
        var last: integer = numbers[2];
        """
        self.parse_and_analyze(code)
    
    def test_array_index_validation_failure(self):
        """Test error for invalid array index access."""
        code = """
        var number: integer = 5;
        var invalid = number[0];  // accessing non-array as array
        """
        self.assert_semantic_error(code)


class TestGeneralSemanticRules(TestSemanticAnalysis):
    """Test cases for general semantic rules."""
    
    def test_meaningful_expressions_success(self):
        """Test successful meaningful expressions."""
        code = """
        var a: integer = 5;
        var b: integer = 3;
        var result: integer = a * b;
        """
        self.parse_and_analyze(code)
    
    def test_meaningless_expressions_failure(self):
        """Test error for semantically meaningless expressions."""
        code = """
        function test(): void { }
        var invalid = test * 5;  // multiplying function by number
        """
        self.assert_semantic_error(code)
    
    def test_duplicate_declarations_failure(self):
        """Test error for duplicate variable declarations."""
        code = """
        function test(param: integer, param: string): void { }
        """
        self.assert_semantic_error(code, "ya existe")
    
    def test_type_inference_success(self):
        """Test successful type inference for untyped variables."""
        code = """
        var inferred = 42;        // should infer integer
        var inferred2 = 314;      // should infer integer
        var inferred3 = "hello";  // should infer string
        var inferred4 = true;     // should infer boolean
        """
        self.parse_and_analyze(code)


class DetailedTestResult(unittest.TestResult):
    """Custom test result class that tracks detailed test information."""
    
    def __init__(self):
        super().__init__()
        self.test_results = []
        self.start_time = None
        self.end_time = None
        
    def startTestRun(self):
        """Called before any tests are executed."""
        super().startTestRun()
        self.start_time = time.time()
        print("\n" + "="*80)
        print("🧪 COMPISCRIPT SEMANTIC ANALYSIS TEST SUITE")
        print("="*80)
    
    def stopTestRun(self):
        """Called after all tests have been executed."""
        super().stopTestRun()
        self.end_time = time.time()
        self._print_detailed_summary()
        self._save_resume_file()
    
    def startTest(self, test):
        """Called before each test method."""
        super().startTest(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"\n🔍 Running: {test_name}")
    
    def addSuccess(self, test):
        """Called when a test passes."""
        super().addSuccess(test)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"   ✅ PASSED: {test_name}")
        self.test_results.append({
            'name': test_name,
            'status': 'PASSED',
            'category': test.__class__.__name__,
            'method': test._testMethodName,
            'doc': test._testMethodDoc or '',
            'error': None
        })
    
    def addError(self, test, err):
        """Called when a test has an error."""
        super().addError(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"   ❌ ERROR: {test_name}")
        print(f"      {str(err[1])}")
        self.test_results.append({
            'name': test_name,
            'status': 'ERROR',
            'category': test.__class__.__name__,
            'method': test._testMethodName,
            'doc': test._testMethodDoc or '',
            'error': str(err[1])
        })
    
    def addFailure(self, test, err):
        """Called when a test fails."""
        super().addFailure(test, err)
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"   ❌ FAILED: {test_name}")
        print(f"      {str(err[1])}")
        self.test_results.append({
            'name': test_name,
            'status': 'FAILED',
            'category': test.__class__.__name__,
            'method': test._testMethodName,
            'doc': test._testMethodDoc or '',
            'error': str(err[1])
        })
    
    def _print_detailed_summary(self):
        """Print a detailed summary of test results."""
        duration = self.end_time - self.start_time
        
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        # Overall statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASSED'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAILED'])
        error_tests = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"   ❌ Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   ⚠️  Errors: {error_tests} ({error_tests/total_tests*100:.1f}%)")
        print(f"   ⏱️  Duration: {duration:.2f} seconds")
        
        # Results by category
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0, 'error': 0}
            categories[cat][result['status'].lower()] += 1
        
        print(f"\n📋 Results by Category:")
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            passed_cat = stats['passed']
            print(f"   {category}:")
            print(f"      ✅ {passed_cat}/{total_cat} passed ({passed_cat/total_cat*100:.1f}%)")
            if stats['failed'] > 0:
                print(f"      ❌ {stats['failed']} failed")
            if stats['error'] > 0:
                print(f"      ⚠️  {stats['error']} errors")
        
        # Failed/Error tests detail
        failed_or_error = [r for r in self.test_results if r['status'] in ['FAILED', 'ERROR']]
        if failed_or_error:
            print(f"\n🔍 Failed/Error Tests Detail:")
            for result in failed_or_error:
                status_icon = "❌" if result['status'] == 'FAILED' else "⚠️"
                print(f"   {status_icon} {result['name']}")
                print(f"      {result['doc']}")
                print(f"      Error: {result['error']}")
                print()
        
        # Success indicator
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Semantic analysis is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests + error_tests} test(s) need attention.")
        
        print("\n" + "="*80)
    
    def _save_resume_file(self):
        """Save test results to a resume file for later analysis."""
        resume_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': self.end_time - self.start_time,
            'summary': {
                'total': len(self.test_results),
                'passed': len([r for r in self.test_results if r['status'] == 'PASSED']),
                'failed': len([r for r in self.test_results if r['status'] == 'FAILED']),
                'error': len([r for r in self.test_results if r['status'] == 'ERROR'])
            },
            'results': self.test_results
        }
        
        resume_file = Path(__file__).parent / 'test_resume.json'
        try:
            with open(resume_file, 'w', encoding='utf-8') as f:
                json.dump(resume_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Resume saved to: {resume_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save resume file: {e}")


class DetailedTestRunner:
    """Custom test runner that uses DetailedTestResult."""
    
    def run(self, test_suite):
        """Run the test suite with detailed reporting."""
        result = DetailedTestResult()
        test_suite.run(result)
        return result


def load_previous_resume():
    """Load and display previous test results if available."""
    resume_file = Path(__file__).parent / 'test_resume.json'
    if resume_file.exists():
        try:
            with open(resume_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"\n📄 Previous test run ({data['timestamp']}):")
            summary = data['summary']
            print(f"   Total: {summary['total']}, Passed: {summary['passed']}, Failed: {summary['failed']}, Errors: {summary['error']}")
            print(f"   Duration: {data['duration']:.2f} seconds")
            return True
        except Exception as e:
            print(f"\n⚠️  Could not load previous resume: {e}")
    return False


if __name__ == '__main__':
    # Load previous results if available
    load_previous_resume()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestTypeSystem,
        TestScopeManagement, 
        TestFunctionsAndProcedures,
        TestControlFlow,
        TestClassesAndObjects,
        TestArraysAndDataStructures,
        TestGeneralSemanticRules
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed reporting
    runner = DetailedTestRunner()
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)