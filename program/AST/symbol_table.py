# program/symbol_table.py
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from AST.ast_nodes import TypeNode

class SemanticError(Exception):
    """Exception for semantic errors."""
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

class Scope:
    def __init__(self, parent=None):
        self.parent  = parent
        self._table: Dict[str, Symbol] = {}

    def define(self, sym: Symbol):
        if sym.name in self._table:
            raise SemanticError(f"Identificador '{sym.name}' ya existe en este ámbito")
        self._table[sym.name] = sym

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self._table.get(name)

    def lookup(self, name: str) -> Symbol:
        scope = self
        while scope is not None:
            if name in scope._table:
                return scope._table[name]
            scope = scope.parent
        raise SemanticError(f"Identificador '{name}' no declarado")
