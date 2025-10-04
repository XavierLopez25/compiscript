# Repository Guidelines

## Project Structure & Module Organization
- `program/` hosts the compiler source; keep AST nodes in `program/AST`, semantic passes in `program/semantic`, TAC generators in `program/tac`, and runnable samples under `program/*.cps`.
- `program/tests/` stores regression suites; place new fixtures in `test_cases` and helpers beside `run_tests.py`.
- `IDE-compiscript/` contains the Vite/React IDE; UI code lives in `IDE-compiscript/src` with assets next to their components.
- `commands/` holds ANTLR helper scripts; leave `antlr-4.13.1-complete.jar` at the repository root for grammar generation.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` prepares an isolated Python environment.
- `pip install -r requirements.txt` installs compiler runtime dependencies.
- `java -jar antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -no-listener program/Compiscript.g4` regenerates lexer and parser files (inside Docker you may run `./commands/antlr ...`).
- `python3 program/Driver.py program/program.cps` executes the compiler against a sample program; swap in other `.cps` files as needed.
- `python3 program/tests/run_tests.py` runs semantic smoke tests plus unit tests.
- `cd IDE-compiscript && npm install && npm run dev` launches the IDE frontend locally; use `npm run build` for production bundles.

## Coding Style & Naming Conventions
- Follow PEP 8 for Python: four-space indentation, snake_case functions and variables, PascalCase classes, and descriptive module names.
- Never hand-edit generated ANTLR artifacts in `program/`; update the grammar and regenerate instead.
- React components in `IDE-compiscript/src` stay in PascalCase files with co-located styles; prefer functional components and hooks.
- Run `npm run lint` before committing IDE changes to keep ESLint clean.

## Testing Guidelines
- Extend semantic fixtures via `program/tests/test_cases/success_cases.cps` or `failure_cases/*.cps`; name new files after the covered language feature.
- Add focused unit tests to `program/tests/test_semantic_analysis.py` using `unittest.TestCase` patterns already in place.
- After regenerating parser artefacts or altering semantics, re-run `python3 program/tests/run_tests.py` and ensure no regressions.
- Capture manual compiler runs (input program → observed output) in PR notes whenever test coverage cannot assert the change.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes seen in history (`feat`, `fix`, `test`, etc.) and add scope hints, e.g., `feat(tac): ...`.
- Reference related issues in the PR description, list setup steps, and attach compiler output or IDE screenshots when UI behaviour changes.
- Keep PRs focused: separate grammar updates, semantic adjustments, and IDE tweaks into dedicated commits where practical.
- Call out breaking grammar changes or new runtime flags in the PR summary so maintainers can refresh sample programs promptly.


## Additional Notes

# 🧪 TAC Generator Project - CompilScript Compiler

## 📋 Project Overview

This project implements the **Intermediate Code Generation (TAC)** phase for a CompilScript compiler. Building upon existing lexical, syntactic, and semantic analysis phases, we generate Three Address Code (TAC) as an intermediate representation.

## 🎯 Main Requirements

### **REQ-1: Semantic Actions for TAC Generation**
- Transform AST nodes into TAC instructions
- Use visitor pattern to traverse AST and generate intermediate code
- TAC syntax follows standard format: `x = y op z`, `goto L`, `if x goto L`
- Support all language constructs: expressions, control flow, functions, classes

### **REQ-2: Symbol Table Extensions**
- Extend existing symbol table with code generation metadata
- Add memory addresses, offsets, and temporary labels
- Support activation records with variable offsets
- Maintain compatibility with previous compiler phases

### **REQ-3: Temporary Variable Management**  
- Implement algorithm for temporary variable allocation (t1, t2, t3...)
- Include recycling mechanism to reuse temporaries when safe
- Optimize temporary usage in complex expressions
- Track temporary lifetimes and scope

### **REQ-4: Comprehensive Testing**
- Test suite covering successful TAC generation cases
- Error cases and boundary conditions testing
- Integration tests with previous compiler phases
- Performance tests for temporary recycling

### **REQ-5: Activation Records & Runtime Environments**
- Implement activation record structure for function calls
- Calculate variable offsets within activation records
- Support nested scopes and function parameter passing
- Handle return values and stack management

## 🏗️ Project Structure (4-Person Team)

### **Part 1/4: Infrastructure & Memory Management**
**Scope:** Base TAC framework, temporary variables, memory layout
- TAC instruction classes and visitor base
- Temporary variable generator with recycling algorithm
- Memory address/offset management system
- Base testing infrastructure

**Key Deliverables:**
```python
tac/
├── instruction.py      # TAC instruction classes
├── temp_manager.py     # Temporary variable management
├── address_manager.py  # Memory address allocation
└── base_generator.py   # Base visitor for TAC generation
```

### **Part 2/4: Expression TAC Generation** 
**Scope:** Arithmetic, boolean, and assignment expressions
- Binary operators (+, -, *, /, &&, ||, etc.)
- Unary operators (-, !)  
- Short-circuit boolean evaluation
- Type conversions and operator precedence

**Dependencies:** Part 1 (temporaries + base infrastructure)

### **Part 3/4: Control Flow TAC Generation**
**Scope:** Conditional statements, loops, jumps
- Label generation and management
- if/else, while, for, switch statements
- Conditional and unconditional jumps
- Break/continue statement handling

**Dependencies:** Parts 1-2 (infrastructure + expressions)

### **Part 4/4: Functions & Activation Records**
**Scope:** Function calls, parameter passing, stack management
- Function declaration and call TAC
- Activation record structure and offsets
- Parameter pushing/popping
- Return statement handling
- Symbol table extensions integration

**Dependencies:** Parts 1-3 (complete TAC foundation)

## 🔧 Technical Constraints

### **TAC Instruction Format**
```
# Assignment
x = y op z
x = op y  
x = y

# Jumps  
goto L
if x goto L
if x relop y goto L

# Functions
BeginFunc n
EndFunc
PushParam x
call f, n
PopParams n
return x
```

### **Integration Points**
- Must work with existing `SemanticVisitor` and AST nodes
- Extend current `Symbol` and `Scope` classes
- Maintain compatibility with existing test framework
- Output TAC suitable for future MIPS assembly generation

### **Quality Standards**
- Comprehensive unit tests for each component
- Integration tests with sample CompilScript programs  
- Error handling for invalid code generation scenarios
- Performance benchmarks for temporary recycling efficiency

## 📝 Important Notes

- **Sequential Development**: Each part builds upon previous parts
- **Testing Focus**: Each part must include both success and failure test cases
- **Code Quality**: Follow existing project patterns and documentation standards
- **Team Coordination**: Regular code reviews and integration testing

## 🎓 Learning Objectives

- Understand intermediate code generation principles
- Implement efficient temporary variable management
- Design activation record structures for runtime execution
- Create comprehensive compiler testing strategies
