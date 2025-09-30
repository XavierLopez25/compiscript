from typing import Optional, Dict, Any
from AST.ast_nodes import *
from .base_generator import BaseTACVisitor, TACGenerationError
from .instruction import *

class ExpressionTACGenerator(BaseTACVisitor):
    """
    TAC Generator for expressions (Part 2/4).

    Handles:
    - Arithmetic operators (+, -, *, /)
    - Boolean operators (&&, ||, !) with short-circuit evaluation
    - Relational operators (==, !=, <, >, <=, >=)
    - Unary operators (-, !)
    - Assignment operations
    - Type conversions and operator precedence
    """

    def __init__(self):
        super().__init__()
        self._function_generator = None  # Will be set by parent generator
        self._operator_mapping = {
            # Arithmetic operators
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '%': '%',
            # Relational operators
            '==': '==',
            '!=': '!=',
            '<': '<',
            '>': '>',
            '<=': '<=',
            '>=': '>=',
            # Unary operators
            'u-': '-',  # Unary minus
            'u!': '!'   # Unary not
        }

    # ============ LITERALS ============

    def visit_Literal(self, node: Literal) -> str:
        """Generate TAC for literal values (integers, floats, strings, booleans)."""
        return str(node.value)

    def visit_NullLiteral(self, node: NullLiteral) -> str:
        """Generate TAC for null literal."""
        return "null"

    # ============ VARIABLES ============

    def visit_Variable(self, node: Variable) -> str:
        """Generate TAC for variable access."""
        # Look up the scoped name for this variable
        return self.get_scoped_name(node.name, is_declaration=False)

    def visit_ThisExpression(self, node) -> str:
        """Generate TAC for 'this' reference in methods."""
        return "this"

    # ============ BINARY OPERATIONS ============

    def visit_BinaryOperation(self, node: BinaryOperation) -> str:
        """Generate TAC for binary operations with appropriate handling."""
        # Validate operation types first
        self._validate_operation_types(node)

        if node.operator in ['&&', '||']:
            return self._generate_boolean_shortcircuit(node)
        else:
            return self._generate_simple_binary(node)

    def _generate_simple_binary(self, node: BinaryOperation) -> str:
        """Generate TAC for simple binary operations (arithmetic, relational, string concatenation)."""
        left_result = self.visit(node.left)
        right_result = self.visit(node.right)

        # Handle special case: string concatenation
        if node.operator == '+' and self._is_string_operation(node):
            return self._generate_string_concatenation(left_result, right_result)

        # Handle type conversions for numeric operations
        if self._is_arithmetic_operator(node.operator):
            left_result, right_result = self._handle_numeric_conversions(node, left_result, right_result)

        # Map operator to TAC format
        tac_operator = self._operator_mapping.get(node.operator, node.operator)

        # Generate temporary for result
        result_temp = self.new_temp()

        # Emit assignment instruction
        instruction = AssignInstruction(result_temp, left_result, tac_operator, right_result)
        self.emit(instruction)

        return result_temp

    def _generate_boolean_shortcircuit(self, node: BinaryOperation) -> str:
        """Generate TAC for boolean operations with short-circuit evaluation."""
        result_temp = self.new_temp()
        end_label = self.new_label("bool_end")

        if node.operator == '&&':
            # Short-circuit AND: if left is false, result is false
            left_result = self.visit(node.left)

            # If left is false, jump to end with false result
            false_label = self.new_label("and_false")
            self.emit(ConditionalGotoInstruction(left_result, false_label, "0", "=="))

            # Left is true, evaluate right
            right_result = self.visit(node.right)
            self.emit(AssignInstruction(result_temp, right_result))
            self.emit(GotoInstruction(end_label))

            # Left was false
            self.emit(LabelInstruction(false_label))
            self.emit(AssignInstruction(result_temp, "0"))  # false

        elif node.operator == '||':
            # Short-circuit OR: if left is true, result is true
            left_result = self.visit(node.left)

            # If left is true, jump to end with true result
            true_label = self.new_label("or_true")
            self.emit(ConditionalGotoInstruction(left_result, true_label, "0", "!="))

            # Left is false, evaluate right
            right_result = self.visit(node.right)
            self.emit(AssignInstruction(result_temp, right_result))
            self.emit(GotoInstruction(end_label))

            # Left was true
            self.emit(LabelInstruction(true_label))
            self.emit(AssignInstruction(result_temp, "1"))  # true

        self.emit(LabelInstruction(end_label))
        return result_temp

    # ============ UNARY OPERATIONS ============

    def visit_UnaryOperation(self, node: UnaryOperation) -> str:
        """Generate TAC for unary operations."""
        operand_result = self.visit(node.operand)
        result_temp = self.new_temp()

        # Map unary operator
        if node.operator == '-':
            tac_operator = self._operator_mapping.get('u-', '-')
        elif node.operator == '!':
            tac_operator = self._operator_mapping.get('u!', '!')
        else:
            tac_operator = node.operator

        # Emit unary operation
        instruction = AssignInstruction(result_temp, operand_result, tac_operator)
        self.emit(instruction)

        return result_temp

    # ============ ASSIGNMENT OPERATIONS ============

    def visit_AssignmentStatement(self, node: AssignmentStatement) -> str:
        """Generate TAC for assignment statements."""
        value_result = self.visit(node.value)

        if isinstance(node.target, Variable):
            # Simple variable assignment: x = value
            self.emit(AssignInstruction(node.target.name, value_result))
            return node.target.name

        elif isinstance(node.target, IndexExpression):
            # Array assignment: array[index] = value
            array_result = self.visit(node.target.array)
            index_result = self.visit(node.target.index)

            instruction = ArrayAccessInstruction(
                target=value_result,
                array=array_result,
                index=index_result,
                is_assignment=True
            )
            self.emit(instruction)
            return value_result

        elif isinstance(node.target, PropertyAccess):
            # Property assignment: obj.prop = value
            object_result = self.visit(node.target.object)

            instruction = PropertyAccessInstruction(
                target=value_result,
                object_ref=object_result,
                property_name=node.target.property,
                is_assignment=True
            )
            self.emit(instruction)
            return value_result

        else:
            raise TACGenerationError(f"Unsupported assignment target: {type(node.target)}", node)

    # ============ COMPLEX EXPRESSIONS ============

    def visit_TernaryOp(self, node: TernaryOp) -> str:
        """Generate TAC for ternary conditional operator (condition ? true_expr : false_expr)."""
        condition_result = self.visit(node.condition)
        result_temp = self.new_temp()

        false_label = self.new_label("ternary_false")
        end_label = self.new_label("ternary_end")

        # If condition is false, jump to false branch
        self.emit(ConditionalGotoInstruction(condition_result, false_label, "0", "=="))

        # True branch
        true_result = self.visit(node.if_true)
        self.emit(AssignInstruction(result_temp, true_result))
        self.emit(GotoInstruction(end_label))

        # False branch
        self.emit(LabelInstruction(false_label))
        false_result = self.visit(node.if_false)
        self.emit(AssignInstruction(result_temp, false_result))

        self.emit(LabelInstruction(end_label))
        return result_temp

    def visit_IndexExpression(self, node: IndexExpression) -> str:
        """Generate TAC for array access expressions."""
        array_result = self.visit(node.array)
        index_result = self.visit(node.index)
        result_temp = self.new_temp()

        instruction = ArrayAccessInstruction(
            target=result_temp,
            array=array_result,
            index=index_result,
            is_assignment=False
        )
        self.emit(instruction)

        return result_temp

    def visit_PropertyAccess(self, node: PropertyAccess) -> str:
        """Generate TAC for property access expressions."""
        object_result = self.visit(node.object)
        result_temp = self.new_temp()

        instruction = PropertyAccessInstruction(
            target=result_temp,
            object_ref=object_result,
            property_name=node.property,
            is_assignment=False
        )
        self.emit(instruction)

        return result_temp

    def visit_ArrayLiteral(self, node: ArrayLiteral) -> str:
        """Generate TAC for array literal creation."""
        result_temp = self.new_temp()

        # Emit comment for array creation
        self.emit(CommentInstruction(f"Array literal with {len(node.elements)} elements"))

        # For now, we'll create a simple array allocation
        # This might need to be extended when we have proper array support
        self.emit(AssignInstruction(result_temp, f"array[{len(node.elements)}]"))

        # Generate TAC for each element and assign to array
        for i, element in enumerate(node.elements):
            element_result = self.visit(element)
            instruction = ArrayAccessInstruction(
                target=element_result,
                array=result_temp,
                index=str(i),
                is_assignment=True
            )
            self.emit(instruction)

        return result_temp

    def visit_NewExpression(self, node) -> str:
        """Generate TAC for object creation (new ClassName()) with constructor call."""
        # Create the object instance
        instance_temp = self.new_temp()

        # Emit comment for object creation
        self.emit(CommentInstruction(f"Create new instance of {node.class_name}"))

        # Generate new instruction
        from .instruction import NewInstruction, PushParamInstruction, CallInstruction, PopParamsInstruction
        self.emit(NewInstruction(instance_temp, node.class_name))

        # Determine which constructor to call
        # If the class has no explicit constructor but has a parent, use parent's constructor
        constructor_name = f"{node.class_name}_constructor"
        actual_constructor = constructor_name

        # Check if we should use parent constructor
        if hasattr(self, '_function_generator') and self._function_generator:
            # Check if this class has an explicit constructor or just a default one
            class_registry = self._function_generator._class_registry
            if node.class_name in class_registry:
                class_node = class_registry[node.class_name]

                # Check if class has explicit constructor
                has_explicit_constructor = False
                for member in class_node.members:
                    if hasattr(member, 'name') and member.name == 'constructor':
                        has_explicit_constructor = True
                        break

                # If no explicit constructor and has arguments, try parent class
                if not has_explicit_constructor and len(node.arguments) > 0:
                    if hasattr(class_node, 'superclass') and class_node.superclass:
                        # Use parent's constructor
                        actual_constructor = f"{class_node.superclass}_constructor"

        # Push constructor arguments (if any)
        for arg in node.arguments:
            arg_temp = self.visit(arg)
            self.emit(PushParamInstruction(arg_temp))

        # Push 'this' parameter (the instance we just created)
        self.emit(PushParamInstruction(instance_temp))

        # Call constructor
        constructor_result = self.new_temp()
        total_params = len(node.arguments) + 1  # arguments + this
        self.emit(CallInstruction(actual_constructor, total_params, constructor_result))

        # Clean up parameters
        self.emit(PopParamsInstruction(total_params))

        # Return the constructed object (could be instance_temp or constructor_result)
        # Most constructors return 'this', so we use the constructor result
        return constructor_result

    def visit_CallExpression(self, node) -> str:
        """Handle function calls within expressions by delegating to function generator."""
        if self._function_generator:
            # Sync instructions before delegating
            self._function_generator.instructions = self.get_instructions()
            result = self._function_generator.visit_CallExpression(node)
            # Sync back instructions
            self.instructions = self._function_generator.get_instructions()
            return result
        else:
            # If no function generator is available, generate a basic call
            # This shouldn't normally happen, but provides a working fallback
            result_temp = self.new_temp()
            from .instruction import CommentInstruction, PushParamInstruction, CallInstruction, PopParamsInstruction

            # Get function name
            if hasattr(node.callee, 'name'):
                function_name = node.callee.name
            else:
                function_name = str(node.callee)

            # Generate basic call
            self.emit(CommentInstruction(f"Fallback call to {function_name}"))

            # Push parameters
            for arg in node.arguments:
                arg_temp = self.visit(arg)
                self.emit(PushParamInstruction(arg_temp))

            # Call function
            self.emit(CallInstruction(function_name, len(node.arguments), result_temp))

            # Pop parameters
            if len(node.arguments) > 0:
                self.emit(PopParamsInstruction(len(node.arguments)))

            return result_temp

    # ============ TYPE CONVERSION HELPERS ============

    def _generate_type_conversion(self, value: str, from_type: Type, to_type: Type) -> str:
        """Generate TAC for type conversions when needed."""
        if from_type == to_type:
            return value

        result_temp = self.new_temp()

        if from_type == Type.INTEGER and to_type == Type.FLOAT:
            self.emit(AssignInstruction(result_temp, value, "int_to_float"))
        elif from_type == Type.FLOAT and to_type == Type.INTEGER:
            self.emit(AssignInstruction(result_temp, value, "float_to_int"))
        elif to_type == Type.STRING:
            self.emit(AssignInstruction(result_temp, value, "to_string"))
        else:
            # Default: just copy the value (no conversion needed)
            self.emit(AssignInstruction(result_temp, value))

        return result_temp

    def _handle_numeric_conversions(self, node: BinaryOperation, left_result: str, right_result: str) -> tuple:
        """Handle automatic type conversions for numeric operations."""
        # Get types from AST nodes if available
        left_type = getattr(node.left, 'type', None)
        right_type = getattr(node.right, 'type', None)

        # If we don't have type information, return as-is
        if not left_type or not right_type:
            return left_result, right_result

        # Both same type, no conversion needed
        if left_type == right_type:
            return left_result, right_result

        # Promote integer to float if one operand is float
        if left_type == Type.INTEGER and right_type == Type.FLOAT:
            left_result = self._generate_type_conversion(left_result, Type.INTEGER, Type.FLOAT)
        elif left_type == Type.FLOAT and right_type == Type.INTEGER:
            right_result = self._generate_type_conversion(right_result, Type.INTEGER, Type.FLOAT)

        return left_result, right_result

    def _is_string_operation(self, node: BinaryOperation) -> bool:
        """Check if this is a string concatenation operation."""
        # Check if either operand has string type
        left_type = getattr(node.left, 'type', None)
        right_type = getattr(node.right, 'type', None)

        return (left_type == Type.STRING or right_type == Type.STRING or
                self._is_string_literal(node.left) or self._is_string_literal(node.right))

    def _is_string_literal(self, node: ASTNode) -> bool:
        """Check if node is a string literal."""
        return isinstance(node, Literal) and isinstance(node.value, str)

    def _generate_string_concatenation(self, left_result: str, right_result: str) -> str:
        """Generate TAC for string concatenation."""
        result_temp = self.new_temp()

        # Emit comment for clarity
        self.emit(CommentInstruction("String concatenation"))

        # Use special string concatenation operation
        instruction = AssignInstruction(result_temp, left_result, "str_concat", right_result)
        self.emit(instruction)

        return result_temp

    def _validate_operation_types(self, node: BinaryOperation) -> None:
        """Validate that operation types are compatible and raise errors if not."""
        left_type = getattr(node.left, 'type', None)
        right_type = getattr(node.right, 'type', None)

        # Skip validation if type information is not available
        if not left_type or not right_type:
            return

        operator = node.operator

        # String operations: only concatenation (+) is allowed
        if left_type == Type.STRING or right_type == Type.STRING:
            if operator != '+':
                raise TACGenerationError(
                    f"String operands only support concatenation (+), not '{operator}'", node)
            return

        # Boolean operations: only logical operators allowed
        if left_type == Type.BOOLEAN or right_type == Type.BOOLEAN:
            if operator not in ['&&', '||', '==', '!=']:
                raise TACGenerationError(
                    f"Boolean operands don't support operator '{operator}'", node)
            return

        # Arithmetic operations: only numeric types
        if self._is_arithmetic_operator(operator):
            if not self._is_numeric_type(left_type) or not self._is_numeric_type(right_type):
                raise TACGenerationError(
                    f"Arithmetic operator '{operator}' requires numeric operands", node)
            return

        # Relational operations: compatible types only
        if operator in ['<', '>', '<=', '>=']:
            if not (self._is_numeric_type(left_type) and self._is_numeric_type(right_type)):
                raise TACGenerationError(
                    f"Relational operator '{operator}' requires numeric operands", node)

    def _is_numeric_type(self, type_val: Type) -> bool:
        """Check if type is numeric (integer or float)."""
        return type_val in [Type.INTEGER, Type.FLOAT]

    # ============ UTILITY METHODS ============

    def _is_boolean_operator(self, operator: str) -> bool:
        """Check if operator produces boolean result."""
        return operator in ['&&', '||', '==', '!=', '<', '>', '<=', '>=', '!']

    def _is_arithmetic_operator(self, operator: str) -> bool:
        """Check if operator is arithmetic."""
        return operator in ['+', '-', '*', '/', '%']

    def _get_operator_precedence(self, operator: str) -> int:
        """Get operator precedence for expression ordering."""
        precedence_map = {
            '||': 1,
            '&&': 2,
            '==': 3, '!=': 3,
            '<': 4, '>': 4, '<=': 4, '>=': 4,
            '+': 5, '-': 5,
            '*': 6, '/': 6, '%': 6,
            '!': 7, 'u-': 7  # Unary operators
        }
        return precedence_map.get(operator, 0)