# program/symbol_table.py
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from AST.ast_nodes import TypeNode

class SemanticError(Exception):
    """Exception for semantic errors."""
    def __init__(self, message, line=None, column=None):
        if line is not None and column is not None:
            message = f"line {line}:{column} {message}"
        super().__init__(message)
        self.line = line
        self.column = column
    pass

@dataclass
class Symbol:
    def __init__(self, name: str, type_node, is_const: bool=False, kind: str="var"):
        self.name       = name
        self.type_node  = type_node   # TypeNode or None (if inferred)
        self.is_const   = is_const
        self.kind       = kind        # "var" | "func" | "class"
        # Para funciones:
        self.params     = []          # [TypeNode, ...]
        self.return_type= None        # TypeNode

        # SYM-001: TAC Generation Extensions
        self.memory_offset = None     # Memory offset in activation record
        self.memory_address = None    # Global memory address or register
        self.tac_label = None        # TAC label for functions
        self.is_parameter = False    # True if this symbol is a function parameter
        self.parameter_index = None  # Parameter position (0, 1, 2, ...)
        self.activation_record_id = None  # Reference to activation record
        self.size_bytes = 4          # Size in bytes (default 4 for int/pointer)
    def to_dict(self):
        def tn_str(tn):
            if tn is None: return None
            return f"{tn.base}[{tn.dimensions}]"
        return {
            "name": self.name,
            "kind": getattr(self, "kind", "var"),
            "const": getattr(self, "is_const", False),
            "type": tn_str(self.type_node),
            "params": [tn_str(p) for p in getattr(self, "params", [])] if hasattr(self, "params") else None,
            "return": tn_str(getattr(self, "return_type", None)) if hasattr(self, "return_type") else None,
            # TAC Generation metadata
            "memory_offset": getattr(self, "memory_offset", None),
            "memory_address": getattr(self, "memory_address", None),
            "tac_label": getattr(self, "tac_label", None),
            "is_parameter": getattr(self, "is_parameter", False),
            "parameter_index": getattr(self, "parameter_index", None),
            "size_bytes": getattr(self, "size_bytes", 4),
        }

class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}   # name -> Symbol
        self.children = []  # <- NEW
        if parent:
            parent.children.append(self)  # <- NEW

        # SYM-002: Activation Record Extensions
        self.activation_record = None    # Reference to ActivationRecord
        self.function_name = None        # Function name if this is function scope
        self.scope_type = "global"       # "global", "function", "block", "class"
        self.stack_frame_size = 0        # Total stack frame size
        self.local_var_count = 0         # Number of local variables
        self.temp_var_count = 0          # Number of temporary variables
        self.max_call_depth = 1          # Maximum call depth from this scope

    def define(self, sym):
        if sym.name in self.symbols:
            raise SemanticError(f"Redeclaración de '{sym.name}' en el mismo ámbito")
        self.symbols[sym.name] = sym

    def lookup(self, name):
        cur = self
        while cur:
            if name in cur.symbols:
                return cur.symbols[name]
            cur = cur.parent
        raise SemanticError(f"Identificador no declarado: '{name}'")

    # SYM-003: Runtime Environment Support
    def create_function_scope(self, function_name: str):
        """Create a new function scope with activation record support."""
        child_scope = Scope(parent=self)
        child_scope.scope_type = "function"
        child_scope.function_name = function_name
        return child_scope

    def get_activation_record_info(self):
        """Get activation record information for this scope."""
        return {
            "function_name": self.function_name,
            "scope_type": self.scope_type,
            "stack_frame_size": self.stack_frame_size,
            "local_var_count": self.local_var_count,
            "temp_var_count": self.temp_var_count,
            "max_call_depth": self.max_call_depth
        }

    def calculate_stack_frame_size(self):
        """Calculate total stack frame size for this scope."""
        total_size = 0
        for symbol in self.symbols.values():
            if hasattr(symbol, 'size_bytes') and symbol.size_bytes:
                total_size += symbol.size_bytes
        self.stack_frame_size = total_size
        return total_size

    def assign_memory_offsets(self, start_offset: int = 0):
        """Assign memory offsets to symbols in this scope."""
        current_offset = start_offset
        for symbol in self.symbols.values():
            if symbol.kind == "var" and not symbol.is_parameter:
                symbol.memory_offset = current_offset
                current_offset += symbol.size_bytes
                self.local_var_count += 1
        return current_offset

    # Helpers para mostrar
    def to_dict(self):
        return {
            "symbols": [s.to_dict() for s in self.symbols.values()],
            "children": [c.to_dict() for c in self.children],
            # Activation record info
            "scope_type": getattr(self, "scope_type", "global"),
            "function_name": getattr(self, "function_name", None),
            "stack_frame_size": getattr(self, "stack_frame_size", 0),
            "local_var_count": getattr(self, "local_var_count", 0),
            "temp_var_count": getattr(self, "temp_var_count", 0),
        }