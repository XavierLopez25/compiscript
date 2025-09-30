from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

from AST.ast_nodes import ASTNode
from AST.symbol_table import Symbol, Scope
from .instruction import (
    TACInstruction,
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction
)
from .temp_manager import TemporaryManager
from .address_manager import AddressManager
from .label_manager import LabelManager

class TACGenerator(ABC):
    """
    Base class for Three Address Code generation.
    Provides infrastructure for TAC generation using the visitor pattern.
    """

    def __init__(self):
        self.instructions: List[TACInstruction] = []
        self.temp_manager = TemporaryManager()
        self.address_manager = AddressManager()
        self.label_manager = LabelManager(self.address_manager.generate_label)
        self._symbol_table: Optional[Dict[str, Symbol]] = None
        self._current_scope: Optional[Scope] = None

        # Scope tracking for variable and function renaming (shared state)
        self._scope_state = {
            'level': 0,
            'stack': [{}],  # Stack of {original_name: scoped_name}
            'function_names': {}  # {original_name: scoped_name} for functions
        }

    def set_symbol_table(self, symbol_table: Dict[str, Symbol]) -> None:
        """Set the symbol table from semantic analysis."""
        self._symbol_table = symbol_table

    def set_current_scope(self, scope: Scope) -> None:
        """Set the current scope for symbol resolution."""
        self._current_scope = scope

    def emit(self, instruction: TACInstruction) -> None:
        """
        Emit a TAC instruction to the instruction list.

        Args:
            instruction: TAC instruction to emit
        """
        if isinstance(instruction, LabelInstruction):
            self.label_manager.define_label(instruction.label)
        elif isinstance(instruction, (GotoInstruction, ConditionalGotoInstruction)):
            self.label_manager.reference_label(instruction.label)

        self.instructions.append(instruction)

    def emit_list(self, instructions: List[TACInstruction]) -> None:
        """
        Emit multiple TAC instructions.

        Args:
            instructions: List of TAC instructions to emit
        """
        for instruction in instructions:
            self.emit(instruction)

    def new_temp(self) -> str:
        """
        Generate a new temporary variable.

        Returns:
            str: New temporary variable name
        """
        return self.temp_manager.new_temp()

    def release_temp(self, temp: str) -> None:
        """
        Release a temporary variable for reuse.

        Args:
            temp: Temporary variable to release
        """
        self.temp_manager.release_temp(temp)

    def new_label(self, prefix: str = "L", hint: Optional[str] = None) -> str:
        """
        Generate a new label for control flow.

        Args:
            prefix: Label prefix
            hint: Optional semantic hint for label name

        Returns:
            str: New label name
        """
        return self.label_manager.new_label(prefix, hint)

    def enter_scope(self) -> None:
        """Enter a new scope (for temporaries and variables)."""
        self.temp_manager.enter_scope()
        # Track scope for variable/function renaming
        self._scope_state['level'] += 1
        self._scope_state['stack'].append({})

    def exit_scope(self) -> None:
        """Exit current scope and clean up temporaries."""
        self.temp_manager.exit_scope()
        # Clean up scope tracking
        if self._scope_state['level'] > 0:
            self._scope_state['stack'].pop()
            self._scope_state['level'] -= 1

    def get_scoped_name(self, original_name: str, is_declaration: bool = False) -> str:
        """
        Get the scoped name for a variable or function.

        Args:
            original_name: Original variable/function name
            is_declaration: True if this is a declaration, False if it's a use

        Returns:
            str: Scoped name (e.g., 'x' becomes 'x_scope1' in nested scope)
        """
        # For declarations, create a new scoped name if we're in a nested scope
        if is_declaration:
            if self._scope_state['level'] > 0:
                scoped_name = f"{original_name}_scope{self._scope_state['level']}"
                # Register in current scope
                self._scope_state['stack'][-1][original_name] = scoped_name
                return scoped_name
            else:
                # Global scope, use original name
                self._scope_state['stack'][-1][original_name] = original_name
                return original_name

        # For uses, look up the name starting from innermost scope
        for scope_dict in reversed(self._scope_state['stack']):
            if original_name in scope_dict:
                return scope_dict[original_name]

        # Not found in any scope, return original name (might be a global or parameter)
        return original_name

    def register_function_scope(self, original_name: str, scoped_name: str) -> None:
        """Register a function with its scoped name."""
        self._scope_state['function_names'][original_name] = scoped_name

    def get_function_scoped_name(self, original_name: str) -> str:
        """Get the scoped name for a function (for calls)."""
        # Look in current scope stack first
        for scope_dict in reversed(self._scope_state['stack']):
            if original_name in scope_dict:
                return scope_dict[original_name]

        # Fall back to function registry
        return self._scope_state['function_names'].get(original_name, original_name)

    def get_instructions(self) -> List[TACInstruction]:
        """
        Get all generated TAC instructions.

        Returns:
            List[TACInstruction]: Generated instructions
        """
        return self.instructions.copy()

    def clear_instructions(self) -> None:
        """Clear all generated instructions."""
        self.instructions.clear()

    def get_tac_code(self) -> str:
        """
        Get string representation of all TAC instructions.

        Returns:
            str: TAC code as string
        """
        return '\n'.join(str(instruction) for instruction in self.instructions)

    @abstractmethod
    def generate(self, ast_node: ASTNode) -> Optional[str]:
        """
        Generate TAC for an AST node.
        Must be implemented by concrete generators.

        Args:
            ast_node: AST node to generate TAC for

        Returns:
            Optional[str]: Result temporary/variable name or None
        """
        pass

    def reset(self) -> None:
        """Reset the generator to initial state."""
        self.instructions.clear()
        self.temp_manager.reset()
        self.address_manager.reset()
        self.label_manager.reset()
        # Reset scope tracking
        self._scope_state = {
            'level': 0,
            'stack': [{}],
            'function_names': {}
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get generation statistics for optimization analysis.

        Returns:
            Dict[str, Any]: Statistics about generation process
        """
        temp_stats = self.temp_manager.optimize_usage()
        addr_stats = self.address_manager.get_statistics()
        label_stats = self.label_manager.get_statistics()

        return {
            'instructions_generated': len(self.instructions),
            'temporary_stats': temp_stats,
            'address_stats': addr_stats,
            'label_stats': label_stats
        }

class BaseTACVisitor(TACGenerator):
    """
    Base visitor class for TAC generation.
    Implements common visiting patterns and provides extension points.
    """

    def visit(self, node: ASTNode) -> Optional[str]:
        """
        Visit an AST node and generate TAC.

        Args:
            node: AST node to visit

        Returns:
            Optional[str]: Result variable/temporary name
        """
        if node is None:
            return None

        method_name = f'visit_{node.__class__.__name__}'
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(node)
        else:
            return self.generic_visit(node)

    def generic_visit(self, node: ASTNode) -> Optional[str]:
        """
        Generic visit method for nodes without specific handlers.

        Args:
            node: AST node to visit

        Returns:
            Optional[str]: None (default implementation)
        """
        return None

    def generate(self, ast_node: ASTNode) -> Optional[str]:
        """
        Generate TAC for an AST node using visitor pattern.

        Args:
            ast_node: AST node to generate TAC for

        Returns:
            Optional[str]: Result temporary/variable name
        """
        return self.visit(ast_node)

class TACGenerationError(Exception):
    """Exception raised during TAC generation."""

    def __init__(self, message: str, node: Optional[ASTNode] = None):
        if (node and hasattr(node, 'line') and hasattr(node, 'column')
            and node.line is not None and node.column is not None):
            message = f"Line {node.line}:{node.column}: {message}"
        super().__init__(message)
        self.node = node
