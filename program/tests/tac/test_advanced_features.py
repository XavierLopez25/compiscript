import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tac.function_generator import FunctionTACGenerator
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
    Type
)
from AST.symbol_table import Symbol, Scope


class TestAdvancedTACFeatures(unittest.TestCase):
    """Test suite for advanced TAC features: classes, recursion, symbol table extensions."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = FunctionTACGenerator()
        self.integrated_generator = IntegratedTACGenerator()

    def test_class_with_constructor(self):
        """Test CLASS-001: Class with constructor TAC generation."""
        # class Point {
        #     Point(x: int, y: int) {
        #         this.x = x;
        #         this.y = y;
        #     }
        # }

        # Constructor parameters
        param_x = Parameter("x", TypeNode("int"))
        param_y = Parameter("y", TypeNode("int"))

        # Constructor body (simplified)
        constructor_body = Block([ReturnStatement(None)])

        # Constructor function
        constructor = FunctionDeclaration("Point", [param_x, param_y], TypeNode("void"), constructor_body)

        # Class declaration
        class_decl = ClassDeclaration("Point", None, [constructor])

        result = self.generator.visit_ClassDeclaration(class_decl)
        instructions = self.generator.get_instructions()

        self.assertIsNone(result)

        # Check for constructor-specific instructions
        tac_content = '\n'.join(str(instr) for instr in instructions)
        self.assertIn("Constructor: Point", tac_content)
        self.assertIn("BeginFunc Point_constructor", tac_content)
        self.assertIn("EndFunc Point_constructor", tac_content)

        # Should handle implicit 'this' parameter (3 total: this + x + y)
        self.assertIn("Point_constructor, 3", tac_content)

    def test_class_with_methods(self):
        """Test CLASS-001: Class with methods TAC generation."""
        # class Calculator {
        #     add(a: int, b: int): int {
        #         return a + b;
        #     }
        # }

        param_a = Parameter("a", TypeNode("int"))
        param_b = Parameter("b", TypeNode("int"))
        method_body = Block([ReturnStatement(Literal(42, Type.INTEGER))])

        add_method = FunctionDeclaration("add", [param_a, param_b], TypeNode("int"), method_body)
        class_decl = ClassDeclaration("Calculator", None, [add_method])

        self.generator.visit_ClassDeclaration(class_decl)
        instructions = self.generator.get_instructions()

        tac_content = '\n'.join(str(instr) for instr in instructions)
        self.assertIn("Method: Calculator.add", tac_content)
        self.assertIn("BeginFunc Calculator_add", tac_content)
        self.assertIn("Default Constructor: Calculator", tac_content)  # Should generate default constructor

    def test_recursive_function(self):
        """Test REC-001: Recursive function TAC generation."""
        # func factorial(n: int): int {
        #     if (n <= 1) return 1;
        #     return n * factorial(n - 1);
        # }

        param_n = Parameter("n", TypeNode("int"))

        # Recursive call (simplified)
        recursive_call = CallExpression(Variable("factorial"), [Literal(1, Type.INTEGER)])
        return_stmt = ReturnStatement(recursive_call)

        func_body = Block([return_stmt])

        func_decl = FunctionDeclaration("factorial", [param_n], TypeNode("int"), func_body)

        result = self.generator.visit_FunctionDeclaration(func_decl)
        instructions = self.generator.get_instructions()

        tac_content = '\n'.join(str(instr) for instr in instructions)

        # Should handle recursive call
        self.assertIn("BeginFunc factorial", tac_content)
        self.assertIn("call factorial", tac_content)
        self.assertIn("Recursive call to factorial", tac_content)
        self.assertIn("EndFunc factorial", tac_content)

    def test_symbol_table_extensions(self):
        """Test SYM-001 to SYM-004: Symbol table extensions."""
        # Test Symbol class extensions
        symbol = Symbol("testVar", TypeNode("int"))

        # Check default values
        self.assertIsNone(symbol.memory_offset)
        self.assertIsNone(symbol.memory_address)
        self.assertIsNone(symbol.tac_label)
        self.assertFalse(symbol.is_parameter)
        self.assertIsNone(symbol.parameter_index)
        self.assertEqual(symbol.size_bytes, 4)

        # Set TAC generation metadata
        symbol.memory_offset = -8
        symbol.memory_address = "fp-8"
        symbol.is_parameter = True
        symbol.parameter_index = 0

        # Test to_dict includes new fields
        symbol_dict = symbol.to_dict()
        self.assertEqual(symbol_dict['memory_offset'], -8)
        self.assertEqual(symbol_dict['memory_address'], "fp-8")
        self.assertTrue(symbol_dict['is_parameter'])
        self.assertEqual(symbol_dict['parameter_index'], 0)

    def test_scope_extensions(self):
        """Test SYM-002: Scope extensions for activation records."""
        # Test Scope class extensions
        scope = Scope()

        # Check default values
        self.assertIsNone(scope.activation_record)
        self.assertIsNone(scope.function_name)
        self.assertEqual(scope.scope_type, "global")
        self.assertEqual(scope.stack_frame_size, 0)

        # Test function scope creation
        func_scope = scope.create_function_scope("testFunc")
        self.assertEqual(func_scope.scope_type, "function")
        self.assertEqual(func_scope.function_name, "testFunc")
        self.assertEqual(func_scope.parent, scope)

        # Test activation record info
        ar_info = func_scope.get_activation_record_info()
        self.assertEqual(ar_info['function_name'], "testFunc")
        self.assertEqual(ar_info['scope_type'], "function")

    def test_nested_scopes(self):
        """Test SYM-003: Nested execution environments."""
        global_scope = Scope()
        global_scope.scope_type = "global"

        func_scope = global_scope.create_function_scope("outerFunc")
        block_scope = Scope(parent=func_scope)
        block_scope.scope_type = "block"

        # Test scope hierarchy
        self.assertEqual(block_scope.parent, func_scope)
        self.assertEqual(func_scope.parent, global_scope)
        self.assertIsNone(global_scope.parent)

        # Test memory offset calculation
        symbol1 = Symbol("var1", TypeNode("int"))
        symbol2 = Symbol("var2", TypeNode("float"))

        func_scope.define(symbol1)
        func_scope.define(symbol2)

        # Calculate offsets
        end_offset = func_scope.assign_memory_offsets(0)
        self.assertGreater(end_offset, 0)
        self.assertEqual(func_scope.local_var_count, 2)

    def test_error_cases(self):
        """Test TEST-007: Error cases for functions."""
        # Test function with wrong return type
        param = Parameter("x", TypeNode("int"))
        return_stmt = ReturnStatement(Literal("string", Type.STRING))  # Wrong type for int function
        body = Block([return_stmt])

        func_decl = FunctionDeclaration("badFunc", [param], TypeNode("int"), body)

        # Should still generate TAC but with potential type mismatch
        result = self.generator.visit_FunctionDeclaration(func_decl)
        instructions = self.generator.get_instructions()

        self.assertIsNone(result)
        self.assertGreater(len(instructions), 0)

    def test_complex_program_integration(self):
        """Test INT-001: Integration with all modules."""
        # Complex program with classes, functions, and recursion

        # func fibonacci(n: int): int {
        #     if (n <= 1) return n;
        #     return fibonacci(n-1) + fibonacci(n-2);
        # }
        #
        # class Math {
        #     power(base: int, exp: int): int {
        #         if (exp == 0) return 1;
        #         return base * this.power(base, exp-1);
        #     }
        # }

        # Fibonacci function
        fib_param = Parameter("n", TypeNode("int"))
        fib_call1 = CallExpression(Variable("fibonacci"), [Literal(1, Type.INTEGER)])
        fib_call2 = CallExpression(Variable("fibonacci"), [Literal(2, Type.INTEGER)])
        fib_return = ReturnStatement(fib_call1)  # Simplified
        fib_body = Block([fib_return])
        fib_func = FunctionDeclaration("fibonacci", [fib_param], TypeNode("int"), fib_body)

        # Math class with power method
        power_params = [Parameter("base", TypeNode("int")), Parameter("exp", TypeNode("int"))]
        recursive_power_call = CallExpression(Variable("power"), [Literal(2, Type.INTEGER), Literal(3, Type.INTEGER)])
        power_return = ReturnStatement(recursive_power_call)
        power_body = Block([power_return])
        power_method = FunctionDeclaration("power", power_params, TypeNode("int"), power_body)
        math_class = ClassDeclaration("Math", None, [power_method])

        # Complete program
        program = Program([fib_func, math_class])

        # Use integrated generator
        tac_lines = self.integrated_generator.generate_program(program)

        self.assertIsInstance(tac_lines, list)
        self.assertGreater(len(tac_lines), 10)

        tac_content = '\n'.join(tac_lines)

        # Should contain fibonacci function
        self.assertIn("BeginFunc fibonacci", tac_content)
        self.assertIn("call fibonacci", tac_content)

        # Should contain Math class and power method
        self.assertIn("Class: Math", tac_content)
        self.assertIn("Method: Math.power", tac_content)
        self.assertIn("Default Constructor: Math", tac_content)

    def test_end_to_end_tac_generation(self):
        """Test TEST-008: End-to-end program TAC generation."""
        # Complete program with multiple features

        # func main(): int {
        #     return 0;
        # }
        main_return = ReturnStatement(Literal(0, Type.INTEGER))
        main_body = Block([main_return])
        main_func = FunctionDeclaration("main", [], TypeNode("int"), main_body)

        program = Program([main_func])

        # Generate TAC with metadata
        metadata = self.integrated_generator.get_tac_with_metadata()
        self.integrated_generator.generate_program(program)
        metadata = self.integrated_generator.get_tac_with_metadata()

        # Verify metadata structure
        self.assertIn('tac_code', metadata)
        self.assertIn('instruction_count', metadata)
        self.assertIn('function_registry', metadata)
        self.assertIn('statistics', metadata)
        self.assertIn('memory_layout', metadata)

        # Verify content
        self.assertGreater(metadata['instruction_count'], 0)
        self.assertIn('main', metadata['function_registry'])

        # Test optimization
        optimized_tac = self.integrated_generator.optimize_tac()
        self.assertIsInstance(optimized_tac, list)

        # Test validation
        errors = self.integrated_generator.validate_tac()
        self.assertIsInstance(errors, list)
        # Print any validation errors for debugging
        for error in errors:
            print(f"Validation warning: {error}")


class TestSymbolTableIntegration(unittest.TestCase):
    """Test integration between TAC generation and extended symbol table."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = FunctionTACGenerator()

    def test_symbol_table_compatibility(self):
        """Test SYM-004: Compatibility with previous compiler phases."""
        # Create symbols as would be done by semantic analysis
        func_symbol = Symbol("testFunc", TypeNode("int"), kind="func")
        func_symbol.params = [TypeNode("int")]
        func_symbol.return_type = TypeNode("int")

        var_symbol = Symbol("x", TypeNode("int"))

        # Test that TAC generation can work with these symbols
        self.assertEqual(func_symbol.kind, "func")
        self.assertEqual(len(func_symbol.params), 1)
        self.assertIsNotNone(func_symbol.return_type)

        # Test TAC extensions don't break existing functionality
        func_dict = func_symbol.to_dict()
        self.assertEqual(func_dict['kind'], "func")
        self.assertIn('memory_offset', func_dict)
        self.assertIn('is_parameter', func_dict)

    def test_activation_record_integration(self):
        """Test integration between activation records and symbol table."""
        # Create function with parameters
        param = Parameter("x", TypeNode("int"))
        body = Block([ReturnStatement(Literal(1, Type.INTEGER))])
        func_decl = FunctionDeclaration("test", [param], TypeNode("int"), body)

        # Generate TAC and check activation record
        self.generator.visit_FunctionDeclaration(func_decl)

        # Verify activation record was created
        ar_stats = self.generator.address_manager.get_statistics()
        self.assertGreater(ar_stats['labels_generated'], 0)

    def test_memory_layout_calculation(self):
        """Test memory layout calculation for complex function."""
        # Function with multiple parameters and local variables
        params = [
            Parameter("a", TypeNode("int")),
            Parameter("b", TypeNode("float")),
            Parameter("c", TypeNode("boolean"))
        ]

        # Simplified body
        body = Block([ReturnStatement(Literal(1, Type.INTEGER))])
        func_decl = FunctionDeclaration("complex", params, TypeNode("int"), body)

        self.generator.visit_FunctionDeclaration(func_decl)

        # Check activation record size calculation
        ar_size = self.generator.address_manager.get_activation_record_size("complex")
        self.assertGreater(ar_size, 0)


if __name__ == '__main__':
    unittest.main()