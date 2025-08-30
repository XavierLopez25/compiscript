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
        }

class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}   # name -> Symbol
        self.children = []  # <- NEW
        if parent:
            parent.children.append(self)  # <- NEW

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

    # Helpers para mostrar
    def to_dict(self):
        return {
            "symbols": [s.to_dict() for s in self.symbols.values()],
            "children": [c.to_dict() for c in self.children],
        }