"""
Symbol Table Annotator for TAC Generation.
Annotates symbol table with memory addresses, offsets, TAC labels, and other
code generation metadata.
"""

from typing import Dict, Any, Optional
from AST.symbol_table import Symbol, Scope
from .address_manager import AddressManager


class SymbolAnnotator:
    """Annotates symbol table with code generation metadata."""

    def __init__(self, address_manager: AddressManager):
        self.address_manager = address_manager

    def annotate_global_scope(self, scope: Scope) -> None:
        """
        Annotate global scope with memory information.

        Args:
            scope: Global scope to annotate
        """
        # scope.symbols is a dict {name -> Symbol}, so iterate over .values()
        for symbol in scope.symbols.values():
            if symbol.kind == 'var':
                self._annotate_global_variable(symbol)
            elif symbol.kind == 'func':
                self._annotate_function(symbol)
            elif symbol.kind == 'class':
                self._annotate_class(symbol)

    def _annotate_global_variable(self, symbol: Symbol) -> None:
        """Annotate a global variable with memory location."""
        # Calculate size based on type_node
        size = self._calculate_size_from_type_node(symbol.type_node)

        # Allocate global variable
        location = self.address_manager.allocate_global_var(symbol.name, size)

        # Update symbol
        symbol.memory_address = location.address
        symbol.memory_offset = location.offset
        symbol.size_bytes = size

    def _annotate_function(self, symbol: Symbol) -> None:
        """Annotate a function with code address and label."""
        # Get function label and address from address manager
        tac_label = self.address_manager.get_function_label(symbol.name)
        code_address = self.address_manager.get_function_address(symbol.name)

        if tac_label:
            symbol.tac_label = tac_label
        if code_address is not None:
            symbol.memory_address = hex(code_address)

    def _annotate_class(self, symbol: Symbol) -> None:
        """Annotate a class symbol."""
        # Classes don't have direct memory addresses
        # Could add vtable_address here for OOP support
        pass

    def annotate_function_scope(self, scope: Scope, function_name: str) -> None:
        """
        Annotate function scope with activation record information.

        Args:
            scope: Function scope to annotate
            function_name: Name of the function
        """
        # Get activation record from address manager
        activation_record = self.address_manager._completed_records.get(function_name)

        if not activation_record:
            # Try current activation record
            if (self.address_manager._activation_records and
                self.address_manager._activation_records[-1].function_name == function_name):
                activation_record = self.address_manager._activation_records[-1]

        if activation_record:
            # Update scope metadata
            scope.scope_type = 'function'
            scope.function_name = function_name
            scope.stack_frame_size = activation_record.total_size
            scope.local_var_count = len(activation_record.local_vars)
            scope.temp_var_count = len(activation_record.temp_vars)

            # Annotate parameters
            param_index = 0
            for symbol in scope.symbols.values():
                if symbol.name in activation_record.parameters:
                    self._annotate_parameter(symbol, activation_record, param_index)
                    param_index += 1
                elif symbol.name in activation_record.local_vars:
                    self._annotate_local_variable(symbol, activation_record)

    def _annotate_parameter(self, symbol: Symbol, activation_record, param_index: int) -> None:
        """Annotate a function parameter."""
        offset = activation_record.local_vars.get(symbol.name, 0)

        symbol.is_parameter = True
        symbol.parameter_index = param_index
        symbol.memory_offset = offset
        symbol.memory_address = f"fp+{offset}" if offset >= 0 else f"fp{offset}"
        symbol.size_bytes = self._calculate_size_from_type_node(symbol.type_node)

    def _annotate_local_variable(self, symbol: Symbol, activation_record) -> None:
        """Annotate a local variable."""
        offset = activation_record.local_vars.get(symbol.name, 0)

        symbol.memory_offset = offset
        symbol.memory_address = f"fp+{offset}" if offset >= 0 else f"fp{offset}"
        symbol.size_bytes = self._calculate_size_from_type_node(symbol.type_node)

    def annotate_nested_scope(self, scope: Scope, parent_function: str = None) -> None:
        """
        Annotate nested block scope.

        Args:
            scope: Nested scope to annotate
            parent_function: Parent function name if applicable
        """
        # Nested scopes inherit function context from parent
        if parent_function:
            scope.function_name = parent_function

        # Annotate symbols in this scope
        for symbol in scope.symbols.values():
            if symbol.kind == 'var':
                # Local variable in nested scope
                size = self._calculate_size_from_type_node(symbol.type_node)
                symbol.size_bytes = size
                # Offset would be calculated during function generation

        # Recursively annotate children
        for child_scope in scope.children:
            self.annotate_nested_scope(child_scope, parent_function or scope.function_name)

    def _calculate_size_from_type_node(self, type_node) -> int:
        """
        Calculate size in bytes from a TypeNode object.

        Args:
            type_node: TypeNode object or None

        Returns:
            int: Size in bytes
        """
        if type_node is None:
            return 4  # Default size

        # TypeNode has .base (string) and .dimensions (int)
        base_type = type_node.base if hasattr(type_node, 'base') else str(type_node)
        dimensions = type_node.dimensions if hasattr(type_node, 'dimensions') else 0

        # For arrays, return pointer size (4 bytes)
        if dimensions > 0:
            return 4

        # Base types
        type_map = {
            'integer': 4,
            'float': 4,
            'boolean': 4,
            'string': 4,  # Pointer to string
        }

        return type_map.get(base_type, 4)

    def _calculate_size(self, type_str: str) -> int:
        """
        Calculate size in bytes for a type.

        Args:
            type_str: Type string (e.g., "integer[0]", "string[1]")

        Returns:
            int: Size in bytes
        """
        if not type_str:
            return 4  # Default size

        # Extract array dimensions
        if '[' in type_str:
            # For arrays, return pointer size (4 bytes)
            # Actual array size is managed in heap
            return 4

        # Base types
        type_map = {
            'integer': 4,
            'float': 4,
            'boolean': 4,
            'string': 4,  # Pointer to string
        }

        base_type = type_str.split('[')[0] if '[' in type_str else type_str
        return type_map.get(base_type, 4)

    def annotate_scope_tree(self, root_scope: Scope) -> None:
        """
        Recursively annotate entire scope tree.

        Args:
            root_scope: Root scope to start annotation
        """
        # Annotate global scope
        self.annotate_global_scope(root_scope)

        # Annotate child scopes
        for child_scope in root_scope.children:
            if child_scope.function_name:
                self.annotate_function_scope(child_scope, child_scope.function_name)
            else:
                self.annotate_nested_scope(child_scope)

            # Recursively process children
            self._annotate_children(child_scope)

    def _annotate_children(self, scope: Scope) -> None:
        """Recursively annotate child scopes."""
        for child in scope.children:
            parent_func = scope.function_name

            if child.function_name:
                self.annotate_function_scope(child, child.function_name)
            else:
                self.annotate_nested_scope(child, parent_func)

            self._annotate_children(child)
