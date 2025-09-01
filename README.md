# CompilScript Compiler

CompilScript is a statically-typed programming language with object-oriented features, implemented as a compiler with comprehensive lexical, syntactic, and semantic analysis phases. This project provides a complete implementation using Python and ANTLR for educational and research purposes in compiler construction.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Language Features](#language-features)
3. [Architecture](#architecture)
4. [Installation and Setup](#installation-and-setup)
5. [Usage](#usage)
6. [Modules](#modules)
7. [Testing](#testing)

## Project Overview

### Objectives

The CompilScript compiler project aims to:

- **Implement a complete compiler front-end** with lexical, syntactic, and semantic analysis phases
- **Demonstrate modern compiler construction techniques** using visitor patterns and symbol table management
- **Provide comprehensive error reporting** with precise location information and context-aware messages
- **Support advanced language features** including classes, inheritance, closures, and type inference
- **Generate intermediate representations** such as Abstract Syntax Trees (AST) and symbol table dumps

### Key Features

- **Static Type System**: Strong typing with type inference and automatic promotion
- **Object-Oriented Programming**: Classes, inheritance, constructors, and method overriding
- **Lexical Scoping**: Proper variable resolution with nested scope support
- **Control Flow Analysis**: Comprehensive validation of loops, conditionals, and function returns
- **Error Recovery**: Robust error handling with detailed diagnostic messages

## Language Features

CompilScript supports the following programming constructs:

- **Data Types**: `integer`, `float`, `string`, `boolean`, `void`, arrays, and user-defined classes
- **Variable Declarations**: Mutable (`var`) and immutable (`const`) bindings with optional type annotations
- **Control Structures**: `if/else`, `while`, `do-while`, `for`, `switch/case` statements
- **Functions**: First-class functions with recursion, closures, and nested definitions
- **Classes**: Object-oriented features with inheritance, constructors, and method dispatch
- **Arrays**: Multi-dimensional arrays with type-safe element access
- **Operators**: Arithmetic, logical, relational, and assignment operators with proper precedence

## Architecture

The compiler follows a modular architecture with clear separation of concerns:

```
compiscript/
├── AST/                    # Abstract Syntax Tree definitions
│   ├── nodes.py           # AST node classes and type definitions
│   ├── symbol_table.py    # Symbol table and scope management
│   └── ast_to_dot.py      # AST visualization (Graphviz DOT export)
├── semantic/              # Semantic analysis modules
│   ├── types.py          # Type system implementation
│   ├── expressions.py    # Expression semantic analysis
│   ├── statements.py     # Statement semantic analysis
│   ├── classes.py        # Class and inheritance analysis
│   ├── helpers.py        # Utility functions
│   └── state.py          # Semantic analysis state
├── SemanticVisitor.py    # Main semantic analysis visitor
├── Driver.py             # Compiler driver and entry point
├── Compiscript.g4        # ANTLR grammar specification
└── program/              # Test programs and examples
```

### Architectural Patterns

**Visitor Pattern Implementation:**
- Base `ASTNode` class with `accept(visitor)` method
- Modular semantic visitors organized by responsibility
- Composite `SemanticVisitor` inheriting from all specialized modules

**Symbol Table Hierarchy:**
- Hierarchical scopes with parent-child relationships
- Separate symbol namespaces for variables, functions, and classes
- Support for nested environments (functions, classes, blocks)

**State Management:**
- Centralized `SemanticState` with scope tracking
- Function return type stack for nested functions
- Loop/switch depth counters for control flow validation

## Installation and Setup

### Prerequisites

- Docker (recommended) or Python 3.8+ with ANTLR
- Graphviz (for AST visualization)

### Docker Setup (Recommended)

1. **Build and run the Docker container:**
   ```bash
   docker build --rm . -t csp-image && \
    docker run --rm -it -p 8000:8000 -v "$(pwd)/program":/program -w /program csp-image \
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Generate lexer and parser from grammar:**
   ```bash
   antlr -Dlanguage=Python3 -visitor -no-listener Compiscript.g4
   ```

### Manual Setup

1. **Install ANTLR4 Python runtime:**
   ```bash
   pip install antlr4-python3-runtime
   ```

2. **Generate parser components:**
   ```bash
   antlr4 -Dlanguage=Python3 -visitor -no-listener Compiscript.g4
   ```

## Usage

### Basic Compilation

Execute the compiler on a CompilScript source file:

```bash
python3 Driver.py <source_file.cps>
```

### Expected Output

**Successful compilation:**
```
Semantic analysis completed successfully.
AST -> ast.dot (use: dot -Tpng ast.dot -o ast.png)
Scopes -> scopes.json
```

**Compilation errors:**
```
SemanticError at line X, column Y: <detailed error message>
```

### AST Visualization

Generate a visual representation of the Abstract Syntax Tree:

```bash
dot -Tpng ast.dot -o ast.png
```

### Scope Analysis

The compiler generates `scopes.json` containing the complete symbol table hierarchy for debugging and analysis.

## Implementation Details

### Core Components

#### `Driver.py` - Compilation Pipeline
The main entry point orchestrates the complete compilation process:

```python
# Parsing phase
input_stream = FileStream(argv[1], encoding='utf-8')
lexer = CompiscriptLexer(input_stream)
parser = CompiscriptParser(CommonTokenStream(lexer))
tree = parser.program()

# Semantic analysis
sem = SemanticVisitor()
ast = sem.visit(tree)

# Output generation
write_dot(ast, "ast.dot")           # AST visualization
dump_scopes(sem.global_scope)       # Symbol table export
```

**Outputs:**
- `ast.dot`: Graphviz visualization of the Abstract Syntax Tree
- `scopes.json`: Complete symbol table hierarchy with all declared symbols

#### `SemanticVisitor.py` - Composite Visitor
Combines all semantic analysis modules using multiple inheritance:

```python
class SemanticVisitor(Types, Statements, Expressions, Classes, Helpers, CompiscriptVisitor):
    def __init__(self):
        self.state = SemanticState()
```

**Design Features:**
- **Method Resolution Order (MRO)**: Left-to-right precedence for visitor methods
- **State Proxies**: Unified access to semantic state across all modules
- **Modular Responsibilities**: Each mixin handles specific language constructs

### AST Infrastructure

#### `AST/nodes.py` - AST Node Definitions
Defines the complete Abstract Syntax Tree structure:

**Base Classes:**
- `ASTNode`: Base class with `type`, `line`, `column` attributes and `accept(visitor)` method
- `Type(Enum)`: Semantic types (`INTEGER`, `FLOAT`, `STRING`, `BOOLEAN`, `VOID`)
- `TypeNode`: Declared types with base name and array dimensions

**Expression Nodes:**
- `Literal(value, type)`: Primitive literals with inferred types
- `Variable(name)`: Identifier references with symbol resolution
- `BinaryOperation(left, right, operator)`: Binary expressions with type checking
- `CallExpression(callee, arguments)`: Function/method calls with signature validation
- `PropertyAccess(object, property)`: Member access with class validation
- `ArrayLiteral(elements)`: Array initialization with element type unification

**Statement Nodes:**
- `Program(statements)`: Root AST node
- `Block(statements)`: Scoped statement groups
- `VariableDeclaration(name, declared_type, initializer, is_const)`: Variable bindings
- Control flow: `IfStatement`, `WhileStatement`, `ForStatement`, `SwitchStatement`
- `FunctionDeclaration(name, parameters, return_type, body)`: Function definitions
- `ClassDeclaration(name, superclass, members)`: Class definitions with inheritance

#### `AST/symbol_table.py` - Symbol Management
Implements hierarchical symbol resolution:

```python
class Symbol:
    def __init__(self, name, type_node, is_const=False, kind="var"):
        # Supports variables, functions, classes with metadata

class Scope:
    def __init__(self, parent=None):
        self.symbols = {}      # Local symbol table
        self.children = []     # Nested scopes
    
    def define(symbol):        # Prevents redeclaration
    def lookup(name):          # Searches upward through hierarchy
```

**Features:**
- **Redeclaration Detection**: Prevents duplicate symbols in same scope
- **Hierarchical Lookup**: Searches parent scopes for symbol resolution
- **Scope Tree Export**: Generates complete scope hierarchy for debugging

#### `AST/ast_to_dot.py` - AST Visualization
Exports AST to Graphviz DOT format:
- **Node Labeling**: Shows class name, attributes (`name=`, `op=`, `type=`)
- **Edge Generation**: Represents parent-child relationships in AST
- **Type Annotations**: Displays inferred types and declared type nodes

### Semantic Analysis Modules

#### `semantic/state.py` - Centralized State Management
Manages all semantic analysis state in a single dataclass:

```python
@dataclass
class SemanticState:
    global_scope: Scope                          # Root scope
    current_scope: Optional[Scope]               # Active scope
    func_return_stack: List[Optional[TypeNode]]  # Return type validation
    loop_depth: int                              # Break/continue validation
    switch_depth: int                            # Switch break validation
    classes: Dict[str, dict]                     # Class metadata
    current_class: Optional[str]                 # Active class context
```

#### `semantic/types.py` - Type System
Handles type annotations and TypeNode construction:
- **Type Parsing**: Converts grammar rules to `TypeNode(base, dimensions)`
- **Primitive Normalization**: Lowercases built-in types (`integer`, `float`, etc.)
- **Array Dimension Counting**: Parses `[]` notation for multi-dimensional arrays
- **Class Type Preservation**: Maintains original casing for user-defined types

#### `semantic/expressions.py` - Expression Analysis
Comprehensive expression type checking and validation:

**Arithmetic Operations:**
- Binary operators (`+`, `-`, `*`, `/`, `%`) with numeric type promotion
- String concatenation via `+` operator
- Type compatibility validation with detailed error messages

**Logical Operations:**
- Boolean operators (`&&`, `||`, `!`) with strict boolean operand requirements
- Comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`) with type compatibility rules

**Object-Oriented Features:**
- **Property Access**: `obj.property` with class member validation
- **Method Calls**: `obj.method(args)` with signature verification
- **Object Construction**: `new ClassName(args)` with constructor validation
- **`this` Expression**: Context-aware self-reference validation

**Array Operations:**
- **Array Literals**: `[1, 2, 3]` with element type unification
- **Array Access**: `array[index]` with bounds and type checking
- **Multi-dimensional**: Support for `array[i][j]` access patterns

#### `semantic/statements.py` - Statement Analysis
Handles all statement forms and control flow:

**Variable Management:**
- **Declarations**: `var`/`let` with optional type inference
- **Constants**: `const` with mandatory initialization
- **Assignments**: Type compatibility validation with immutability checks

**Control Flow:**
- **Conditionals**: `if/else` with boolean condition requirements
- **Loops**: `while`, `do-while`, `for`, `foreach` with proper scope management
- **Switch Statements**: `switch/case` with expression type validation and default handling

**Function Declarations:**
- **Parameter Validation**: Required type annotations for all parameters
- **Return Type Checking**: Validates all return statements against declared type
- **Recursive Functions**: Self-reference support through forward declaration
- **Nested Functions**: Proper scope nesting with closure support

#### `semantic/classes.py` - Object-Oriented Analysis
Complete class system implementation:

**Class Declaration Processing:**
- **Inheritance Validation**: Single inheritance with member inheritance
- **Symbol Registration**: Class names as callable symbols for `new` expressions
- **Member Processing**: Fields and methods with access control

**Method Analysis:**
- **Method Signatures**: Parameter and return type validation
- **Override Checking**: Ensures compatible method signatures in inheritance
- **`this` Context**: Automatic `this` parameter injection in method scopes

**Class Metadata Management:**
```python
classes["Dog"] = {
    "fields": {"name": TypeNode("string", 0), ...},
    "methods": {"speak": {"params": [...], "ret": TypeNode("void", 0)}, ...},
    "super": "Animal" or None
}
```

#### `semantic/helpers.py` - Utility Functions
Provides shared functionality across all semantic modules:

**Type Compatibility:**
- `_types_compatible_assign(declared, actual)`: Assignment validation
- `_promote_numeric(type_a, type_b)`: Automatic numeric promotion (int→float)
- `_class_is_or_inherits_from(class, expected)`: Inheritance checking

**Symbol Resolution:**
- `_lookup_class(name)`: Class metadata retrieval with error handling
- `_lookup_member(class_name, property)`: Field/method resolution in class hierarchy

**Array Type Management:**
- `_array_element_typenode(array_type)`: Element type extraction
- `_unify_array_element_types(elements)`: Type unification for array literals

**Error Reporting:**
- `_raise_ctx(ctx, message)`: Precise error location reporting
- Context-aware error messages with suggestions for common mistakes

### Compilation Pipeline

The CompilScript compiler follows a three-phase compilation process:

#### Phase 1: Lexical and Syntactic Analysis
```
Source Code (.cps) → ANTLR Lexer → Token Stream → ANTLR Parser → Parse Tree
```

**Process:**
1. **Lexical Analysis**: ANTLR-generated lexer tokenizes source code according to `Compiscript.g4`
2. **Syntactic Analysis**: ANTLR-generated parser builds concrete syntax tree (CST)
3. **Error Recovery**: ANTLR provides automatic error recovery and reporting

#### Phase 2: Semantic Analysis
```
Parse Tree → SemanticVisitor → Abstract Syntax Tree (AST) + Symbol Tables
```

**Analysis Steps:**
1. **AST Construction**: Convert parse tree to typed AST nodes with semantic attributes
2. **Symbol Table Building**: Create hierarchical scopes with symbol definitions
3. **Type Checking**: Validate type compatibility in all expressions and statements
4. **Scope Resolution**: Resolve all identifier references to their declarations
5. **Control Flow Validation**: Verify proper use of `break`, `continue`, `return` statements
6. **Class Analysis**: Process inheritance, method overrides, and member access

**Semantic Validation Rules:**
- **Type Safety**: All operations checked for type compatibility with promotion rules
- **Symbol Resolution**: All identifiers must be declared before use
- **Immutability**: Constants cannot be reassigned after declaration
- **Control Flow**: `break`/`continue` only in loops, `return` only in functions
- **Class Members**: Field/method access validated against class definitions
- **Function Signatures**: Parameter count and types validated in all calls

#### Phase 3: Output Generation
```
AST + Symbol Tables → ast.dot (Visualization) + scopes.json (Debug Info)
```

**Generated Artifacts:**
- **`ast.dot`**: Graphviz DOT file for AST visualization
  - Node labels show AST node types and attributes
  - Edges represent parent-child relationships
  - Type annotations display inferred and declared types

- **`scopes.json`**: Complete symbol table dump
  - Hierarchical scope structure with parent-child relationships
  - All symbols with their types, kinds, and metadata
  - Useful for debugging symbol resolution issues

### Error Handling and Diagnostics

**Error Categories:**
- **Semantic Errors**: Type mismatches, undeclared variables, invalid operations
- **Scope Errors**: Redeclaration, out-of-scope access, constant reassignment
- **Control Flow Errors**: Invalid break/continue, return type mismatches
- **Class Errors**: Inheritance cycles, invalid member access, constructor issues

**Error Reporting Features:**
- **Precise Location**: Line and column information for all errors
- **Context-Aware Messages**: Detailed explanations with suggested fixes
- **Multiple Error Reporting**: Continues analysis after non-fatal errors
- **Type Information**: Shows expected vs. actual types in mismatches

**Example Error Output:**
```
SemanticError at line 15, column 8: Cannot assign 'string' to variable 'count' of type 'integer'
Expected: integer
Actual: string
```

### Language Grammar

The CompilScript language is defined by a comprehensive ANTLR4 grammar (`Compiscript.g4`) with the following specifications:

#### Lexical Elements

**Literals:**
- `IntegerLiteral`: Sequences of digits (`[0-9]+`)
- `FloatLiteral`: Decimal numbers (`[0-9]+ '.' [0-9]+`)
- `StringLiteral`: Double-quoted strings (`"..."`)
- `BooleanLiteral`: `true`, `false`
- `NullLiteral`: `null`

**Identifiers:**
- Pattern: `[a-zA-Z_][a-zA-Z0-9_]*`
- Used for variables, functions, classes, and parameters

**Comments:**
- Single-line: `// comment text`
- Multi-line: `/* comment block */`

#### Data Types

**Primitive Types:**
- `boolean`: Boolean values (`true`/`false`)
- `integer`: Whole numbers
- `string`: Text literals
- `float`: Floating-point numbers (inferred from literals)
- `void`: No return value (functions/methods)

**Composite Types:**
- **Arrays**: `type[]`, `type[][]` (multi-dimensional)
- **Classes**: User-defined object types with inheritance

**Type Annotations:**
- Optional type declarations: `var name: type`
- Required for function parameters and return types
- Automatic type inference for initialized variables

#### Variable Declarations

**Mutable Variables:**
```antlr
('let' | 'var') Identifier typeAnnotation? initializer? ';'
```

**Constants:**
```antlr
'const' Identifier typeAnnotation? '=' expression ';'
```

#### Control Flow Statements

**Conditional Statements:**
- `if (expression) block ('else' block)?`

**Loop Statements:**
- `while (expression) block`
- `do block while (expression);`
- `for (init; condition; update) block`
- `foreach (Identifier in expression) block`

**Switch Statements:**
```antlr
'switch' '(' expression ')' '{' 
  ('case' expression ':' statement*)*
  ('default' ':' statement*)?
'}'
```

**Control Transfer:**
- `break;` - Exit loops/switch
- `continue;` - Continue to next loop iteration  
- `return expression?;` - Return from functions

#### Function Declarations

```antlr
'function' Identifier '(' parameters? ')' (':' type)? block

parameters: parameter (',' parameter)*
parameter: Identifier (':' type)?
```

**Features:**
- Optional parameter types (with inference)
- Optional return type annotation
- Support for recursion and closures
- Nested function definitions

#### Class Declarations

```antlr
'class' Identifier (':' Identifier)? '{' classMember* '}'

classMember: functionDeclaration | variableDeclaration | constantDeclaration
```

**Object-Oriented Features:**
- Single inheritance (`: ParentClass`)
- Constructor methods
- Instance methods and fields
- `this` keyword for self-reference
- `new` operator for instantiation

#### Expression Grammar (Operator Precedence)

**Precedence Hierarchy (Highest to Lowest):**

1. **Primary Expressions:**
   - Literals, identifiers, parenthesized expressions
   - Array literals: `[expr1, expr2, ...]`

2. **Postfix Operations:**
   - Function calls: `function(args)`
   - Array indexing: `array[index]`
   - Property access: `object.property`

3. **Unary Operations:**
   - Arithmetic negation: `-expr`
   - Logical negation: `!expr`

4. **Multiplicative Operations:**
   - `*` (multiplication), `/` (division), `%` (modulo)

5. **Additive Operations:**
   - `+` (addition), `-` (subtraction)

6. **Relational Operations:**
   - `<`, `<=`, `>`, `>=` (comparisons)

7. **Equality Operations:**
   - `==` (equality), `!=` (inequality)

8. **Logical AND:** `&&`

9. **Logical OR:** `||`

10. **Ternary Conditional:** `condition ? expr1 : expr2`

11. **Assignment Operations:**
    - Simple assignment: `variable = expression`
    - Property assignment: `object.property = expression`

#### Advanced Features

**Exception Handling:**
```antlr
'try' block 'catch' '(' Identifier ')' block
```

**Object Construction:**
- `new ClassName(arguments)` - Create class instances
- Constructor parameter passing

**Array Operations:**
- Multi-dimensional array support: `type[][]`
- Array literal initialization: `[1, 2, 3]`
- Index-based access: `array[0]`

**Type System Integration:**
- Strong static typing with inference
- Automatic numeric promotion (integer → float)
- Type compatibility checking for all operations

## Testing

The project includes comprehensive test programs:

- **`program.cps`**: General language features and basic constructs
- **`program_loop.cps`**: Loop constructs and control flow
- **`program_break_continue_return.cps`**: Control flow statements validation
- **`program_dot_constructors.cps`**: Object-oriented features and constructor testing

### Running Tests

Execute individual test programs:

```bash
python3 Driver.py program/<test_file.cps>
```
