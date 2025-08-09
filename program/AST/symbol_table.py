# program/symbol_table.py

class SemanticError(Exception):
    """Exception for semantic errors."""
    pass

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
        self.symbols = {}  # name -> Symbol

    def define(self, sym: Symbol):
        if sym.name in self.symbols:
            raise SemanticError(f"Redeclaration of '{sym.name}' in the same scope")
        self.symbols[sym.name] = sym

    def lookup(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        raise SemanticError(f"Use of undeclared identifier: '{name}'")
