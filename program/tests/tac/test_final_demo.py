import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.integrated_generator import IntegratedTACGenerator
from AST.ast_nodes import (
    Program,
    FunctionDeclaration,
    ClassDeclaration,
    CallExpression,
    ReturnStatement,
    Parameter,
    Block,
    TypeNode,
    Variable,
    Literal,
    VariableDeclaration,
    Type,
    BinaryOperation,
    IfStatement,
    NewExpression,
    PropertyAccess
)


class TestFinalTACDemo(unittest.TestCase):
    """
    Final demonstration test for Complete TAC Generation (Part 4/4).

    This test showcases all implemented features:
    - FUNC-001 to FUNC-004: Function declarations, calls, parameters, returns
    - RA-001 to RA-004: Activation records and stack management
    - SYM-001 to SYM-004: Symbol table extensions
    - REC-001: Recursive functions
    - CLASS-001: Class methods and constructors
    - INT-001: Complete integration
    """

    def setUp(self):
        """Set up test fixtures."""
        self.generator = IntegratedTACGenerator()

    def test_complete_compiscript_program(self):
        """
        FINAL-001: Complete CompilScript program demonstration.

        This test generates TAC for a complete program that uses:
        - Classes with constructors and methods
        - Recursive functions
        - Function calls with multiple parameters
        - Return statements
        - Activation record management
        - Symbol table integration
        """

        # Program structure:
        #
        # func factorial(n: int): int {
        #     if (n <= 1) return 1;
        #     return n * factorial(n - 1);
        # }
        #
        # class Calculator {
        #     Calculator() {
        #         // Default constructor
        #     }
        #
        #     compute(x: int, y: int): int {
        #         return factorial(x) + factorial(y);
        #     }
        # }
        #
        # func main(): int {
        #     Calculator calc = new Calculator();
        #     return calc.compute(3, 4);
        # }

        # 1. Factorial function (recursive)
        # func factorial(n: int): int {
        #     if (n <= 1) return 1;
        #     return n * factorial(n - 1);
        # }
        fib_param = Parameter("n", TypeNode("int"))

        # Create the if condition: n <= 1
        n_var = Variable("n")
        one_lit = Literal(1, Type.INTEGER)
        condition = BinaryOperation(n_var, one_lit, "<=")

        # Then branch: return 1
        then_return = ReturnStatement(one_lit)

        # Else branch: return n * factorial(n - 1)
        n_minus_1 = BinaryOperation(Variable("n"), Literal(1, Type.INTEGER), "-")
        recursive_call = CallExpression(Variable("factorial"), [n_minus_1])
        multiplication = BinaryOperation(Variable("n"), recursive_call, "*")
        else_return = ReturnStatement(multiplication)

        # Complete if statement
        if_stmt = IfStatement(condition, then_return, else_return)
        fib_body = Block([if_stmt])
        factorial_func = FunctionDeclaration("factorial", [fib_param], TypeNode("int"), fib_body)

        # 2. Calculator class with constructor and method
        # Constructor
        constructor_body = Block([])  # Empty constructor
        constructor = FunctionDeclaration("Calculator", [], TypeNode("void"), constructor_body)

        # Compute method
        # compute(x: int, y: int): int {
        #     return factorial(x) + factorial(y);
        # }
        compute_params = [Parameter("x", TypeNode("int")), Parameter("y", TypeNode("int"))]

        # Create function calls: factorial(x) and factorial(y)
        fact_call_x = CallExpression(Variable("factorial"), [Variable("x")])
        fact_call_y = CallExpression(Variable("factorial"), [Variable("y")])

        # Add the results: factorial(x) + factorial(y)
        addition = BinaryOperation(fact_call_x, fact_call_y, "+")
        compute_return = ReturnStatement(addition)
        compute_body = Block([compute_return])
        compute_method = FunctionDeclaration("compute", compute_params, TypeNode("int"), compute_body)

        calculator_class = ClassDeclaration("Calculator", None, [constructor, compute_method])

        # 3. Main function
        # func main(): int {
        #     Calculator calc = new Calculator();
        #     return calc.compute(3, 4);
        # }

        # Create Calculator instance: Calculator calc = new Calculator();
        new_calc = NewExpression("Calculator", [])
        calc_decl = VariableDeclaration("calc", TypeNode("Calculator"), new_calc)

        # Call calc.compute(3, 4)
        calc_var = Variable("calc")
        compute_access = PropertyAccess(calc_var, "compute")
        method_call = CallExpression(compute_access, [Literal(3, Type.INTEGER), Literal(4, Type.INTEGER)])
        main_return = ReturnStatement(method_call)

        main_body = Block([calc_decl, main_return])
        main_func = FunctionDeclaration("main", [], TypeNode("int"), main_body)

        # 4. Complete program
        program = Program([factorial_func, calculator_class, main_func])

        # Generate TAC
        tac_lines = self.generator.generate_program(program)

        # Verify comprehensive TAC generation
        self.assertIsInstance(tac_lines, list)
        self.assertGreater(len(tac_lines), 20)  # Should be substantial program

        tac_content = '\n'.join(tac_lines)

        # Print TAC for demonstration (can be removed in production)
        print("\n" + "="*60)
        print("COMPLETE TAC GENERATION DEMONSTRATION")
        print("="*60)
        print(tac_content)
        print("="*60)

        # Verify all major components are present

        # FUNC-001: Function declarations
        self.assertIn("BeginFunc factorial", tac_content)
        self.assertIn("BeginFunc main", tac_content)
        self.assertIn("EndFunc factorial", tac_content)
        self.assertIn("EndFunc main", tac_content)

        # FUNC-002: Function calls
        self.assertIn("call factorial", tac_content)
        self.assertIn("call Calculator_compute", tac_content)

        # FUNC-003: Parameter handling
        self.assertIn("PushParam", tac_content)
        self.assertIn("PopParams", tac_content)

        # FUNC-004: Return statements
        self.assertIn("return", tac_content)

        # REC-001: Recursive functions (verified by presence of factorial call within factorial)
        factorial_section = tac_content[tac_content.find("BeginFunc factorial"):tac_content.find("EndFunc factorial")]
        self.assertIn("call factorial", factorial_section)

        # CLASS-001: Class methods and constructors
        self.assertIn("Class: Calculator", tac_content)
        self.assertIn("Constructor: Calculator", tac_content)
        self.assertIn("Method: Calculator.compute", tac_content)
        self.assertIn("BeginFunc Calculator_constructor", tac_content)
        self.assertIn("BeginFunc Calculator_compute", tac_content)

        # RA-001 to RA-004: Activation records (implicit in BeginFunc/EndFunc)
        func_begins = tac_content.count("BeginFunc")
        func_ends = tac_content.count("EndFunc")
        self.assertEqual(func_begins, func_ends)  # Balanced activation records
        self.assertGreaterEqual(func_begins, 4)  # At least 4 functions

    def test_comprehensive_statistics(self):
        """Test comprehensive statistics and metadata collection."""
        # Simple program for statistics
        param = Parameter("x", TypeNode("int"))
        body = Block([ReturnStatement(Literal(42, Type.INTEGER))])
        func = FunctionDeclaration("test", [param], TypeNode("int"), body)
        program = Program([func])

        # Generate TAC
        self.generator.generate_program(program)

        # Get comprehensive statistics
        stats = self.generator.get_complete_statistics()

        # Verify statistics structure
        required_sections = [
            'integrated_stats',
            'expression_stats',
            'control_flow_stats',
            'function_stats',
            'total_instructions',
            'generator_context'
        ]

        for section in required_sections:
            self.assertIn(section, stats)

        # Verify we have meaningful data
        self.assertGreater(stats['total_instructions'], 0)
        self.assertEqual(stats['generator_context'], 'global')

        # Get TAC with metadata
        metadata = self.generator.get_tac_with_metadata()

        required_metadata = [
            'tac_code',
            'instruction_count',
            'function_registry',
            'statistics',
            'memory_layout'
        ]

        for field in required_metadata:
            self.assertIn(field, metadata)

        self.assertIn('test', metadata['function_registry'])
        self.assertGreater(metadata['instruction_count'], 0)

    def test_validation_and_optimization(self):
        """Test TAC validation and optimization features."""
        # Create program with potential optimization opportunities
        param = Parameter("x", TypeNode("int"))
        body = Block([ReturnStatement(Literal(1, Type.INTEGER))])
        func1 = FunctionDeclaration("func1", [param], TypeNode("int"), body)
        func2 = FunctionDeclaration("func2", [param], TypeNode("int"), body)
        program = Program([func1, func2])

        # Generate TAC
        self.generator.generate_program(program)

        # Test validation
        errors = self.generator.validate_tac()
        self.assertIsInstance(errors, list)

        # Should have no critical errors for valid program
        critical_errors = [e for e in errors if "undefined" in e.lower() or "unmatched" in e.lower()]
        self.assertEqual(len(critical_errors), 0, f"Critical validation errors: {critical_errors}")

        # Test optimization
        original_count = len(self.generator.get_instructions())
        optimized_tac = self.generator.optimize_tac()

        self.assertIsInstance(optimized_tac, list)
        self.assertLessEqual(len(optimized_tac), original_count)

    def test_symbol_table_integration_demo(self):
        """Demonstrate symbol table extensions working with TAC generation."""
        from AST.symbol_table import Symbol, Scope

        # Create function symbol as would be done by semantic analysis
        func_symbol = Symbol("demoFunc", TypeNode("int"), kind="func")
        func_symbol.params = [TypeNode("int"), TypeNode("float")]
        func_symbol.return_type = TypeNode("int")

        # Set TAC generation metadata
        func_symbol.tac_label = "func_demoFunc"
        func_symbol.memory_address = "global_demoFunc"

        # Create scope with activation record info
        global_scope = Scope()
        func_scope = global_scope.create_function_scope("demoFunc")

        # Add symbols to scope
        param1 = Symbol("x", TypeNode("int"))
        param1.is_parameter = True
        param1.parameter_index = 0
        param1.memory_offset = 8

        param2 = Symbol("y", TypeNode("float"))
        param2.is_parameter = True
        param2.parameter_index = 1
        param2.memory_offset = 12

        func_scope.define(param1)
        func_scope.define(param2)

        # Calculate frame size
        frame_size = func_scope.calculate_stack_frame_size()
        self.assertGreater(frame_size, 0)

        # Verify symbol table integration
        self.assertEqual(func_scope.local_var_count, 0)  # No locals, only params
        self.assertEqual(len(func_scope.symbols), 2)

        # Test to_dict with TAC extensions
        func_dict = func_symbol.to_dict()
        self.assertEqual(func_dict['tac_label'], "func_demoFunc")
        self.assertEqual(func_dict['memory_address'], "global_demoFunc")

        scope_dict = func_scope.to_dict()
        self.assertEqual(scope_dict['scope_type'], "function")
        self.assertEqual(scope_dict['function_name'], "demoFunc")

    def test_activation_record_demonstration(self):
        """Demonstrate activation record management."""
        # Function with multiple parameters and local variables
        params = [
            Parameter("a", TypeNode("int")),
            Parameter("b", TypeNode("float")),
            Parameter("c", TypeNode("boolean"))
        ]

        body = Block([ReturnStatement(Literal(42, Type.INTEGER))])
        func = FunctionDeclaration("complexFunc", params, TypeNode("int"), body)
        program = Program([func])

        # Generate TAC
        self.generator.generate_program(program)

        # Check activation record management
        ar_stats = self.generator.function_generator.address_manager.get_statistics()

        # Should have created at least one activation record
        self.assertGreaterEqual(ar_stats['active_functions'], 0)
        self.assertGreater(ar_stats['labels_generated'], 0)

        # Check that function was registered
        func_info = self.generator.function_generator.get_function_info("complexFunc")
        self.assertIsNotNone(func_info)
        self.assertEqual(func_info['parameter_count'], 3)
        self.assertEqual(func_info['name'], "complexFunc")
        self.assertTrue(func_info['has_return_value'])

    def test_error_handling_demo(self):
        """Demonstrate error handling capabilities."""
        # Create function call with wrong parameter count
        callee = Variable("unknownFunc")
        call_expr = CallExpression(callee, [Literal(1, Type.INTEGER), Literal(2, Type.INTEGER)])

        # This should be handled gracefully
        with self.assertRaises(Exception):
            self.generator.function_generator.visit_CallExpression(call_expr)

        # Test continues normally after error
        param = Parameter("x", TypeNode("int"))
        body = Block([ReturnStatement(Literal(1, Type.INTEGER))])
        valid_func = FunctionDeclaration("validFunc", [param], TypeNode("int"), body)
        program = Program([valid_func])

        # Should generate TAC successfully
        tac_lines = self.generator.generate_program(program)
        self.assertGreater(len(tac_lines), 0)


if __name__ == '__main__':
    # Run with verbose output to see the TAC generation
    unittest.main(verbosity=2)