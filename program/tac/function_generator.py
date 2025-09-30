from typing import Optional, List, Dict, Any
from AST.ast_nodes import (
    FunctionDeclaration,
    CallExpression,
    ReturnStatement,
    Parameter,
    Block,
    ASTNode,
    ClassDeclaration,
    VariableDeclaration
)
from AST.symbol_table import Symbol, Scope
from .base_generator import BaseTACVisitor, TACGenerationError
from .instruction import (
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
    AssignInstruction,
    LabelInstruction,
    CommentInstruction
)
from .expression_generator import ExpressionTACGenerator
from .control_flow_generator import ControlFlowTACGenerator


class FunctionTACGenerator(BaseTACVisitor):
    """
    TAC Generator for functions and activation records (Part 4/4).

    Handles:
    - Function declarations with parameter setup
    - Function calls with parameter passing
    - Return statements
    - Activation record management
    - Stack frame setup and cleanup
    """

    def __init__(self):
        super().__init__()
        self.expression_generator = ExpressionTACGenerator()
        self.control_flow_generator = ControlFlowTACGenerator()
        self._function_registry: Dict[str, FunctionDeclaration] = {}
        self._class_registry: Dict[str, ClassDeclaration] = {}
        self._current_function: Optional[str] = None
        self._current_class: Optional[str] = None

        # Share infrastructure between generators
        self._sync_infrastructure()

    def _sync_infrastructure(self):
        """Share infrastructure components between generators."""
        # Share temp manager
        self.expression_generator.temp_manager = self.temp_manager
        self.control_flow_generator.temp_manager = self.temp_manager

        # Share address manager
        self.expression_generator.address_manager = self.address_manager
        self.control_flow_generator.address_manager = self.address_manager

        # Share label manager
        self.expression_generator.label_manager = self.label_manager
        self.control_flow_generator.label_manager = self.label_manager

        # Set function generator reference for call expressions
        self.expression_generator._function_generator = self

    def visit_FunctionDeclaration(self, node: FunctionDeclaration) -> Optional[str]:
        """
        Generate TAC for function declaration.

        Args:
            node: FunctionDeclaration AST node

        Returns:
            None (function declarations don't return values)
        """
        function_name = node.name
        # Only register if not already registered (from pre-pass)
        if function_name not in self._function_registry:
            self._function_registry[function_name] = node
        self._current_function = function_name

        # Extract parameter names
        param_names = [param.name for param in node.parameters]

        # Create activation record
        activation_record = self.address_manager.enter_function(function_name, param_names)

        # Enter new scope for temporaries
        self.enter_scope()

        # Emit function prologue
        self.emit(CommentInstruction(f"Function: {function_name}"))
        self.emit(BeginFuncInstruction(function_name, len(param_names)))

        # Generate label for function start using label manager to track it
        func_label = self.new_label("func", function_name)
        self.emit(LabelInstruction(func_label))

        # Allocate space for parameters and local variables
        for param in node.parameters:
            self.address_manager.allocate_local_var(param.name)

        # Generate TAC for function body
        self._generate_block_tac(node.body)

        # Emit implicit return if function can reach the end without returning
        if not self._function_always_returns(node.body):
            if node.return_type and node.return_type.base != "void":
                # Return default value for non-void functions
                default_val = self._get_default_value(node.return_type.base)
                self.emit(ReturnInstruction(default_val))
            else:
                self.emit(ReturnInstruction())

        # Emit function epilogue
        self.emit(EndFuncInstruction(function_name))

        # Exit scope and function
        self.exit_scope()
        self.address_manager.exit_function()
        self._current_function = None

        return None

    def visit_ClassDeclaration(self, node: ClassDeclaration) -> Optional[str]:
        """
        Generate TAC for class declaration.

        Args:
            node: ClassDeclaration AST node

        Returns:
            None (class declarations don't return values)
        """
        class_name = node.name
        self._class_registry[class_name] = node
        self._current_class = class_name

        # Emit class start comment
        self.emit(CommentInstruction(f"Class: {class_name}"))
        if node.superclass:
            self.emit(CommentInstruction(f"Extends: {node.superclass}"))

        # Process class members
        constructor_found = False
        for member in node.members:
            if isinstance(member, FunctionDeclaration):
                # Check if it's a constructor
                is_constructor = member.name == class_name
                if is_constructor:
                    constructor_found = True
                    self._generate_constructor_tac(member, class_name)
                else:
                    self._generate_method_tac(member, class_name)
            elif isinstance(member, VariableDeclaration):
                # Handle class fields (for future implementation)
                self.emit(CommentInstruction(f"Field: {member.name}"))

        # Generate default constructor if none found
        if not constructor_found:
            self._generate_default_constructor(class_name)

        self._current_class = None
        return None

    def _generate_constructor_tac(self, constructor: FunctionDeclaration, class_name: str):
        """Generate TAC for class constructor."""
        # Constructor gets special naming and 'this' parameter
        constructor_name = f"{class_name}_constructor"

        # Add implicit 'this' parameter
        param_names = ['this'] + [param.name for param in constructor.parameters]

        # Create activation record
        activation_record = self.address_manager.enter_function(constructor_name, param_names)
        self.enter_scope()

        # Emit constructor prologue
        self.emit(CommentInstruction(f"Constructor: {class_name}"))
        self.emit(BeginFuncInstruction(constructor_name, len(param_names)))

        func_label = f"constructor_{class_name}"
        self.emit(LabelInstruction(func_label))

        # Allocate space for parameters and local variables
        for param_name in param_names:
            self.address_manager.allocate_local_var(param_name)

        # Generate TAC for constructor body
        self._generate_block_tac(constructor.body)

        # Implicit return 'this' if no explicit return
        if (not constructor.body.statements or
            not isinstance(constructor.body.statements[-1], ReturnStatement)):
            self.emit(ReturnInstruction('this'))

        # Emit constructor epilogue
        self.emit(EndFuncInstruction(constructor_name))

        self.exit_scope()
        self.address_manager.exit_function()

    def _generate_method_tac(self, method: FunctionDeclaration, class_name: str):
        """Generate TAC for class method."""
        # Method gets class-qualified name and implicit 'this' parameter
        method_name = f"{class_name}_{method.name}"

        # Register method in function registry if not already registered (from pre-pass)
        if method_name not in self._function_registry:
            self._function_registry[method_name] = method
        if method.name not in self._function_registry:
            self._function_registry[method.name] = method  # Allow simple name calls

        # Add implicit 'this' parameter for instance methods
        param_names = ['this'] + [param.name for param in method.parameters]

        # Create activation record
        activation_record = self.address_manager.enter_function(method_name, param_names)
        self.enter_scope()

        # Emit method prologue
        self.emit(CommentInstruction(f"Method: {class_name}.{method.name}"))
        self.emit(BeginFuncInstruction(method_name, len(param_names)))

        func_label = f"method_{class_name}_{method.name}"
        self.emit(LabelInstruction(func_label))

        # Allocate space for parameters and local variables
        for param_name in param_names:
            self.address_manager.allocate_local_var(param_name)

        # Generate TAC for method body
        self._generate_block_tac(method.body)

        # Emit implicit return if no explicit return
        if (not method.body.statements or
            not isinstance(method.body.statements[-1], ReturnStatement)):
            if method.return_type and method.return_type.base != "void":
                default_val = self._get_default_value(method.return_type.base)
                self.emit(ReturnInstruction(default_val))
            else:
                self.emit(ReturnInstruction())

        # Emit method epilogue
        self.emit(EndFuncInstruction(method_name))

        self.exit_scope()
        self.address_manager.exit_function()

    def _generate_default_constructor(self, class_name: str):
        """Generate default constructor if none provided."""
        constructor_name = f"{class_name}_constructor"
        param_names = ['this']

        activation_record = self.address_manager.enter_function(constructor_name, param_names)
        self.enter_scope()

        self.emit(CommentInstruction(f"Default Constructor: {class_name}"))
        self.emit(BeginFuncInstruction(constructor_name, 1))
        self.emit(LabelInstruction(f"default_constructor_{class_name}"))

        # Allocate 'this' parameter
        self.address_manager.allocate_local_var('this')

        # Return 'this'
        self.emit(ReturnInstruction('this'))
        self.emit(EndFuncInstruction(constructor_name))

        self.exit_scope()
        self.address_manager.exit_function()

    def visit_CallExpression(self, node: CallExpression) -> Optional[str]:
        """
        Generate TAC for function call.

        Args:
            node: CallExpression AST node

        Returns:
            str: Temporary variable holding return value (if any)
        """
        # Handle function name and method calls
        is_method_call = False
        this_object = None

        if hasattr(node.callee, 'name'):
            # Simple function call
            function_name = node.callee.name
        elif hasattr(node.callee, 'property'):
            # Method call: object.method()
            from AST.ast_nodes import PropertyAccess
            if isinstance(node.callee, PropertyAccess):
                is_method_call = True
                this_object = self.expression_generator.visit(node.callee.object)
                method_name = node.callee.property

                # Try to determine the class name from the object
                # For now, assume the object is the class instance
                # We'll look for ClassName_methodName in registry
                function_name = None
                for registered_name in self._function_registry.keys():
                    if registered_name.endswith(f"_{method_name}"):
                        function_name = registered_name
                        break

                if not function_name:
                    function_name = method_name  # Fallback to simple name
            else:
                # For other complex expressions as callees, evaluate first
                function_name = self.expression_generator.visit(node.callee)
                if not function_name:
                    raise TACGenerationError("Invalid function expression", node)
        else:
            # For complex expressions as callees, evaluate first
            function_name = self.expression_generator.visit(node.callee)
            if not function_name:
                raise TACGenerationError("Invalid function expression", node)

        # Get function info
        # Define built-in functions that are allowed without declaration
        builtin_functions = {'print', 'println', 'input', 'str', 'int', 'float', 'bool', 'len'}

        if function_name in self._function_registry:
            func_decl = self._function_registry[function_name]
            expected_params = len(func_decl.parameters)

            # For method calls, add 1 for the implicit 'this' parameter
            if is_method_call or '_' in function_name:  # Class methods have underscore in name
                expected_params += 1

            has_return_value = (func_decl.return_type and
                              func_decl.return_type.base != "void")
        elif function_name in builtin_functions:
            # Built-in function - allow variable argument count
            expected_params = len(node.arguments)
            has_return_value = True
        else:
            # Function not declared and not a built-in
            raise TACGenerationError(
                f"Function '{function_name}' is not declared", node
            )

        # For method calls, we need to account for the implicit 'this' parameter
        actual_args = len(node.arguments)
        if is_method_call:
            # Method calls have an implicit 'this' parameter
            actual_args += 1

        if actual_args != expected_params:
            raise TACGenerationError(
                f"Function {function_name} expects {expected_params} arguments, "
                f"got {actual_args} (including 'this' for method calls)", node
            )

        # Evaluate arguments and push parameters (right to left)
        arg_temps = []
        for arg in node.arguments:
            arg_temp = self.expression_generator.visit(arg)
            if not arg_temp:
                raise TACGenerationError("Failed to evaluate argument", arg)
            arg_temps.append(arg_temp)

        # Push parameters in reverse order (right to left for stack)
        for arg_temp in reversed(arg_temps):
            self.emit(PushParamInstruction(arg_temp))

        # For method calls, push 'this' object as first (last pushed) parameter
        if is_method_call and this_object:
            self.emit(PushParamInstruction(this_object))

        # Check if this is a recursive call
        if self._current_function and function_name == self._current_function:
            self.emit(CommentInstruction(f"Recursive call to {function_name}"))

        # Generate function call
        total_params = actual_args  # Use actual_args which includes 'this' for method calls
        result_temp = None
        if has_return_value:
            result_temp = self.new_temp()
            self.emit(CallInstruction(function_name, total_params, result_temp))
        else:
            self.emit(CallInstruction(function_name, total_params))

        # Clean up parameters from stack
        if total_params > 0:
            self.emit(PopParamsInstruction(total_params))

        # Release argument temporaries
        for arg_temp in arg_temps:
            if arg_temp.startswith('t'):  # Only release temps, not variables
                self.release_temp(arg_temp)

        return result_temp

    def visit_ReturnStatement(self, node: ReturnStatement) -> Optional[str]:
        """
        Generate TAC for return statement.

        Args:
            node: ReturnStatement AST node

        Returns:
            None (return statements don't produce values)
        """
        if node.value:
            # Evaluate return expression
            try:
                # Check if it's a call expression (needs to be handled by this generator)
                if isinstance(node.value, CallExpression):
                    return_temp = self.visit_CallExpression(node.value)
                else:
                    # Sync instructions with expression generator
                    self.expression_generator.instructions = self.get_instructions()
                    return_temp = self.expression_generator.visit(node.value)
                    # Sync back instructions
                    self.instructions = self.expression_generator.get_instructions()

                if not return_temp:
                    raise TACGenerationError("Failed to evaluate return expression", node.value)
                self.emit(ReturnInstruction(return_temp))
            except Exception as e:
                # If expression evaluation fails, re-raise with context
                if isinstance(e, TACGenerationError):
                    raise
                raise TACGenerationError(f"Failed to evaluate return expression: {str(e)}", node.value)

            # Release temporary if it was created for this expression
            if return_temp.startswith('t'):
                self.release_temp(return_temp)
        else:
            # Void return
            self.emit(ReturnInstruction())

        return None

    def _generate_block_tac(self, block: Block) -> None:
        """
        Generate TAC for a block of statements.
        Handles recursive calls and nested structures.

        Args:
            block: Block AST node
        """
        for stmt in block.statements:
            if isinstance(stmt, FunctionDeclaration):
                self.visit_FunctionDeclaration(stmt)
            elif isinstance(stmt, ClassDeclaration):
                self.visit_ClassDeclaration(stmt)
            elif isinstance(stmt, ReturnStatement):
                self.visit_ReturnStatement(stmt)
            elif isinstance(stmt, CallExpression):
                # REC-001: Support recursive function calls
                result = self.visit_CallExpression(stmt)
                # For recursive calls, ensure proper stack management
                if result and hasattr(stmt.callee, 'name'):
                    callee_name = stmt.callee.name
                    if callee_name == self._current_function:
                        self.emit(CommentInstruction(f"Recursive call to {callee_name}"))
            elif isinstance(stmt, VariableDeclaration):
                # Handle variable declarations with proper delegation
                self.control_flow_generator.instructions = self.get_instructions()
                result = self.control_flow_generator.visit_VariableDeclaration(stmt)
                self.instructions = self.control_flow_generator.get_instructions()
            else:
                # Delegate to appropriate generators with state synchronization
                stmt_type = stmt.__class__.__name__

                # Control flow nodes
                if stmt_type in ['IfStatement', 'WhileStatement', 'ForStatement',
                               'DoWhileStatement', 'SwitchStatement', 'BreakStatement',
                               'ContinueStatement', 'Block']:
                    # Sync current instructions to control flow generator
                    self.control_flow_generator.instructions = self.get_instructions()
                    self.control_flow_generator.generate(stmt)
                    # Sync back instructions
                    self.instructions = self.control_flow_generator.get_instructions()

                # Expression nodes
                elif stmt_type in ['BinaryOperation', 'UnaryOperation', 'AssignmentStatement',
                                 'Identifier', 'Literal', 'PropertyAccess', 'IndexExpression',
                                 'NewExpression', 'VariableDeclaration']:
                    # Sync current instructions to expression generator
                    self.expression_generator.instructions = self.get_instructions()
                    self.expression_generator.generate(stmt)
                    # Sync back instructions
                    self.instructions = self.expression_generator.get_instructions()

                else:
                    # Try generic visit
                    self.visit(stmt)

    def _function_always_returns(self, body: Block) -> bool:
        """Check if a function body always returns (all execution paths have returns)."""
        if not body.statements:
            return False

        last_stmt = body.statements[-1]

        # If last statement is return, check if it's reachable
        if isinstance(last_stmt, ReturnStatement):
            return True

        # If last statement is if-else, both branches must return
        from AST.ast_nodes import IfStatement
        if isinstance(last_stmt, IfStatement):
            if last_stmt.else_branch:
                # Both branches must end with return
                then_returns = self._statement_always_returns(last_stmt.then_branch)
                else_returns = self._statement_always_returns(last_stmt.else_branch)
                return then_returns and else_returns

        return False

    def _statement_always_returns(self, stmt) -> bool:
        """Check if a statement always returns."""
        from AST.ast_nodes import Block, ReturnStatement, IfStatement

        if isinstance(stmt, ReturnStatement):
            return True
        elif isinstance(stmt, Block) and stmt.statements:
            # Block returns if its last statement returns
            return self._statement_always_returns(stmt.statements[-1])
        elif isinstance(stmt, IfStatement) and stmt.else_branch:
            # If-else returns if both branches return
            then_returns = self._statement_always_returns(stmt.then_branch)
            else_returns = self._statement_always_returns(stmt.else_branch)
            return then_returns and else_returns
        else:
            return False

    def _get_default_value(self, type_name: str) -> str:
        """
        Get default value for a type.

        Args:
            type_name: Type name

        Returns:
            str: Default value
        """
        defaults = {
            'int': '0',
            'float': '0.0',
            'boolean': 'false',
            'string': '""',
        }
        return defaults.get(type_name, '0')

    def generate_program_tac(self, program_node: ASTNode) -> List[str]:
        """
        Generate TAC for entire program.

        Args:
            program_node: Program AST node

        Returns:
            List[str]: Generated TAC instructions as strings
        """
        # Reset generator state
        self.reset()

        # Generate main program TAC
        if hasattr(program_node, 'statements'):
            # Handle program as block
            for stmt in program_node.statements:
                if isinstance(stmt, FunctionDeclaration):
                    self.visit_FunctionDeclaration(stmt)
                else:
                    # Generate TAC for global statements
                    self.visit(stmt)
        else:
            # Single statement/expression
            self.visit(program_node)

        # Return generated instructions as strings
        return [str(instr) for instr in self.get_instructions()]

    def get_function_info(self, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a declared function.

        Args:
            function_name: Name of the function

        Returns:
            Optional[Dict]: Function information or None if not found
        """
        if function_name not in self._function_registry:
            return None

        func_decl = self._function_registry[function_name]
        return {
            'name': function_name,
            'parameter_count': len(func_decl.parameters),
            'parameters': [p.name for p in func_decl.parameters],
            'return_type': func_decl.return_type.base if func_decl.return_type else 'void',
            'has_return_value': (func_decl.return_type and
                               func_decl.return_type.base != 'void')
        }

    def set_expression_generator(self, expr_gen: ExpressionTACGenerator) -> None:
        """Set the expression generator to use for expression evaluation."""
        self.expression_generator = expr_gen

    def set_control_flow_generator(self, cf_gen: ControlFlowTACGenerator) -> None:
        """Set the control flow generator to use for control flow statements."""
        self.control_flow_generator = cf_gen

    def reset(self) -> None:
        """Reset the generator to initial state, including function registry."""
        super().reset()
        self._function_registry.clear()
        self._class_registry.clear()
        self._current_function = None
        self._current_class = None
        # Also reset sub-generators
        self.expression_generator.reset()
        self.control_flow_generator.reset()
        # Re-sync infrastructure after reset
        self._sync_infrastructure()