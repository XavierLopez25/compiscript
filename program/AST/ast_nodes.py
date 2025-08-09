from enum import Enum, auto
from typing import *

class Type(Enum):
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    BOOLEAN = auto()
    VOID = auto()
    # pending more types

class ASTNode:
    """Base node of AST."""
    def __init__(self):
        self.type = None # Infered/Checked type
        self.line = None # Line number in source code
        self.column = None # Column number in source code

    def accept(self, visitor):
        """Method to accept a visitor."""
        method = 'visit_' + self.__class__.__name__
        return getattr(visitor, method)(self)

# ------------------------- Expressions -------------------------

class Literal(ASTNode):
    """Base class for literals."""
    def __init__(self, value, type: Type):
        super().__init__()
        self.value = value
        self.type = type

class NullLiteral(Literal):
    def __init__(self):
        super().__init__(None, Type.VOID)

class Variable(ASTNode):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

class BinaryOperation(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode, operator: str):
        super().__init__()
        self.left = left
        self.right = right
        self.operator = operator

class UnaryOperation(ASTNode):
    def __init__(self, operand: ASTNode, operator: str):
        super().__init__()
        self.operand = operand
        self.operator = operator

class CallExpression(ASTNode):
    def __init__(self, callee: ASTNode, arguments: list):
        super().__init__()
        self.callee = callee
        self.arguments = arguments

class IndexExpression(ASTNode):
    def __init__(self, array: ASTNode, index: ASTNode):
        super().__init__()
        self.array = array
        self.index = index

class PropertyAccess(ASTNode):
    def __init__(self, object: ASTNode, property: str):
        super().__init__()
        self.object = object
        self.property = property

class ArrayLiteral(ASTNode):
    def __init__(self, elements: list):
        super().__init__()
        self.elements = elements  # List of ASTNode

class ThisExpression(ASTNode):
    def __init__(self):
        super().__init__()

class NewExpression(ASTNode):
    def __init__(self, class_name: str, arguments: list):
        super().__init__()
        self.class_name = class_name
        self.arguments = arguments # List of ASTNode

class TernaryOp(ASTNode):
    def __init__(self, condition, if_true, if_false):
        super().__init__()
        self.condition = condition
        self.if_true   = if_true
        self.if_false  = if_false


class Program(ASTNode):
    def __init__(self, statements: list):
        super().__init__()
        self.statements = statements

# ------------------------- Declarations & sentences -------------------------
class TypeNode(ASTNode):
    def __init__(self, base: str, dimensions: int=0):
        super().__init__()
        self.base       = base        # e.g. 'integer' or class identifier
        self.dimensions = dimensions  # 0 = no array, 1 = [], 2 = [][]…

class VariableDeclaration(ASTNode):
    def __init__(self, name: str, declared_type: TypeNode, initializer: ASTNode, is_const: bool=False):
        super().__init__()
        self.name = name
        self.declared_type = declared_type
        self.initializer = initializer
        self.is_const = is_const

class AssignmentStatement(ASTNode):
    def __init__(self, target: ASTNode, value: ASTNode):
        super().__init__()
        self.target = target # Variable, PropertyAccess, IndexExpresssion
        self.value = value

class PrintStatement(ASTNode):
    def __init__(self, expression: ASTNode):
        super().__init__()
        self.expression = expression

class Block(ASTNode):
    def __init__(self, statements: list):
        super().__init__()
        self.statements = statements # List of ASTNode

class IfStatement(ASTNode):
    def __init__(self, condition: ASTNode, then_branch: Block, else_branch: Block=None):
        super().__init__()
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileStatement(ASTNode):
    def __init__(self, condition: ASTNode, body: Block):
        super().__init__()
        self.condition = condition
        self.body = body

class DoWhileStatement(ASTNode):
    def __init__(self, body: Block, condition: ASTNode):
        super().__init__()
        self.body = body
        self.condition = condition

class ForStatement(ASTNode):
    def __init__(self, init: ASTNode, condition: ASTNode, update: ASTNode, body: Block):
        super().__init__()
        self.init = init # VariableDeclaration, AssignmentStatement or None
        self.condition = condition
        self.update = update
        self.body = body

class ForEachStatement(ASTNode):
    def __init__(self, var_name: str, iterable: ASTNode, body: Block):
        super().__init__()
        self.var_name = var_name
        self.iterable = iterable
        self.body = body

class BreakStatement(ASTNode):
    pass

class ContinueStatement(ASTNode):
    pass

class ReturnStatement(ASTNode):
    def __init__(self, value: ASTNode=None):
        super().__init__()
        self.value = value

class TryCatchStatement(ASTNode):
    def __init__(self, try_block: Block, exc_name: str, catch_block: Block):
        super().__init__()
        self.try_block = try_block
        self.exc_name = exc_name
        self.catch_block = catch_block

class SwitchCase(ASTNode):
    def __init__(self, expression: ASTNode, statements: list):
        super().__init__()
        self.expression = expression
        self.statements = statements

class SwitchStatement(ASTNode):
    def __init__(self, expression: ASTNode, cases: list, default: list=None):
        super().__init__()
        self.expression = expression
        self.cases = cases # List of SwitchCase
        self.default = default # List of ASTNode

class Parameter(ASTNode):
    def __init__(self, name: str, type_node):
        super().__init__()
        self.name = name
        self.type_node = type_node

class FunctionDeclaration(ASTNode):
    def __init__(self, name: str, parameters: List[Parameter], return_type: TypeNode, body: Block):
        super().__init__()
        self.name = name
        self.parameters = parameters # List of Parameter
        self.return_type = return_type
        self.body = body

class ClassDeclaration(ASTNode):
    def __init__(self, name: str, superclass: str, members: list):
        super().__init__()
        self.name = name
        self.superclass = superclass # or None
        self.members = members # VariableDeclaration, FunctionDeclaration, etc.

