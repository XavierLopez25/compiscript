from AST.ast_nodes import *
from AST.symbol_table import SemanticError
from typing import Optional, List, Dict


class Helpers:
    def _lhs_to_target(self, lhs_node: ASTNode) -> ASTNode:
        """
        Accept the result of visitLeftHandSide (Variable, PropertyAccess, IndexExpression, CallExpr…)
        and validates that it is assignable (not call).
        """
        if isinstance(lhs_node, (Variable, PropertyAccess, IndexExpression)):
            return lhs_node
        raise SemanticError("The LHS of an assignment is not assignable")

    def _ensure_boolean(self, node: ASTNode, op_desc="operation"):
        if node.type != Type.BOOLEAN:
            raise SemanticError(f"The {op_desc} requires boolean, got {node.type}")

    def _type_name_is_primitive(self, base: str) -> bool:
        return base in ("integer", "float", "string", "boolean", "void")

    def _enum_to_typenode(self, t: Type) -> TypeNode:
        return TypeNode(base=self._type_enum_to_name(t), dimensions=0)

    def _expr_typenode(self, node: ASTNode) -> Optional[TypeNode]:
        """Convert an expression node to TypeNode (if primitive, wrap it; if array/class use node.type_node)."""
        # Case non-primitive/arrays/classes
        tn = getattr(node, "type_node", None)
        if tn is not None:
            return tn
        # Case known primitive
        if getattr(node, "type", None) in (Type.INTEGER, Type.FLOAT, Type.STRING, Type.BOOLEAN, Type.VOID):
            return self._enum_to_typenode(node.type)
        return None

    def _types_compatible_assign(self, declared: Optional[TypeNode], value_node: ASTNode) -> bool:
        # null: only allow for arrays or classes (not for primitives)
        if isinstance(value_node, NullLiteral) or getattr(value_node, "type", None) == Type.VOID:
            return (declared is None) or (declared.dimensions > 0) or (not self._type_name_is_primitive(declared.base))

        actual = self._expr_typenode(value_node)

        # If there is a declared type but we could NOT infer the value's type -> explicit error
        if declared is not None and actual is None:
            raise SemanticError("Could not infer the type of the expression in the assignment")

        # No type declared -> allow inference
        if declared is None:
            return True
        if actual is None:
            # (should not reach here due to previous guard)
            return True

        if declared.dimensions != actual.dimensions:
            return False
        if declared.dimensions > 0:
            return declared.base == actual.base

        if self._type_name_is_primitive(declared.base) and self._type_name_is_primitive(actual.base):
            return declared.base == actual.base

        if not self._type_name_is_primitive(declared.base) and not self._type_name_is_primitive(actual.base):
            return self._class_is_or_inherits_from(actual.base, declared.base)

        return False


    def _class_is_or_inherits_from(self, cls: str, expected: str) -> bool:
        """Returns True if cls == expected or if cls inherits (transitively) from expected."""
        if cls == expected:
            return True
        cur = self.state.classes.get(cls)
        while cur and cur.get("super"):
            if cur["super"] == expected:
                return True
            cur = self.state.classes.get(cur["super"])
        return False

    def _array_element_typenode(self, arr_tn: TypeNode) -> TypeNode:
        if arr_tn.dimensions <= 0:
            raise SemanticError("Index access on non-array type")
        return TypeNode(base=arr_tn.base, dimensions=arr_tn.dimensions - 1)

    def _get_primitive_enum_from_base(self, base: str) -> Optional[Type]:
        mapping = {"integer": Type.INTEGER, "float": Type.FLOAT, "string": Type.STRING, "boolean": Type.BOOLEAN, "void": Type.VOID}
        return mapping.get(base)

    def _is_class_typenode(self, tn: Optional[TypeNode]) -> bool:
        return tn is not None and not self._type_name_is_primitive(tn.base) and tn.dimensions == 0

    def _lookup_class(self, name: str):
        if name not in self.state.classes:
            raise SemanticError(f"Class not declared: '{name}'")
        return self.state.classes[name]

    def _lookup_member(self, class_name: str, prop: str):
        """Search for a member (field or method) in the class and its hierarchy."""
        cur = self._lookup_class(class_name)
        while cur:
            if prop in cur["fields"]:
                return {"kind": "field", "type": cur["fields"][prop]}
            if prop in cur["methods"]:
                return {"kind": "method", "sig": cur["methods"][prop]}
            s = cur.get("super")
            cur = self.state.classes.get(s) if s else None
        raise SemanticError(f"Member '{prop}' does not exist in class '{class_name}'")

    def _check_method_override(self, cls: str, name: str, params: List[TypeNode], ret: TypeNode):
        """If the method exists in the superclass, validate signature compatibility."""
        cur = self._lookup_class(cls)
        s = cur.get("super")
        if not s:
            return
        super_info = self.state.classes.get(s)
        while super_info:
            if name in super_info["methods"]:
                sup = super_info["methods"][name]
                if len(params) != len(sup["params"]):
                    raise SemanticError(f"Override incompatible in '{cls}.{name}': different arity")
                for p, sp in zip(params, sup["params"]):
                    if p.base != sp.base or p.dimensions != sp.dimensions:
                        raise SemanticError(f"Override incompatible in '{cls}.{name}': parameter types do not match")
                if ret.base != sup["ret"].base or ret.dimensions != sup["ret"].dimensions:
                    raise SemanticError(f"Override incompatible in '{cls}.{name}': return type is different")
                return
            s = super_info.get("super")
            super_info = self.state.classes.get(s) if s else None

    def _type_enum_to_name(self, t: Type) -> str:
        return t.name.lower()

    def _expr_type_is_numeric(self, t: Optional[Type]) -> bool:
        return t in (Type.INTEGER, Type.FLOAT)

    def _promote_numeric(self, a: Type, b: Type) -> Type:
        return Type.FLOAT if (a == Type.FLOAT or b == Type.FLOAT) else Type.INTEGER

    def _type_node_from_enum(self, t: Type) -> TypeNode:
        # alias for the name used in other places
        return TypeNode(base=self._type_enum_to_name(t), dimensions=0)

    def _is_primitive_name(self, base: str) -> bool:
        # alias for the name used in visitIdentifierExpr
        return self._type_name_is_primitive(base)
    
    def _ensure_numeric(self, node: ASTNode, op: str):
        if getattr(node, "type", None) not in (Type.INTEGER, Type.FLOAT):
            raise SemanticError(f"Operands of '{op}' must be integer|float, got {getattr(node, 'type', None)}")

    def _unify_array_element_types(self, ctx, elem_tns: List[TypeNode]) -> TypeNode:
        """
        Unifies the types of the elements of an array literal (can be primitive or arrays),
        allowing numeric promotion (integer→float) and checking that the dimensions match.
        Returns the TypeNode of the ELEMENT (not the outer array).
        """
        if not elem_tns:
            return TypeNode(base="any", dimensions=0)

        dims = elem_tns[0].dimensions
        bases = []

        for tn in elem_tns:
            if tn.dimensions != dims:
                raise SemanticError("Array con elementos de diferentes dimensiones")
            bases.append(tn.base)

        # If there is 'any', the result is 'any' in that base
        if "any" in bases:
            return TypeNode(base="any", dimensions=dims)

        # Try numeric promotion if all bases are numeric
        prims = [self._get_primitive_enum_from_base(b) for b in bases]
        # prims contains Type.INTEGER/Type.FLOAT/Type.STRING/Type.BOOLEAN/None (for classes)
        if all(p in (Type.INTEGER, Type.FLOAT) for p in prims if p is not None):
            result_enum = Type.INTEGER
            for p in prims:
                if p == Type.FLOAT:
                    result_enum = Type.FLOAT
            return TypeNode(base=self._type_enum_to_name(result_enum), dimensions=dims)

        # If not all are numeric, require identical bases (e.g. all 'string' or all 'Dog')
        first = bases[0]
        for b in bases[1:]:
            if b != first:
                msg = f"Array with incompatible element bases: '{first}' and '{b}'"
                raise SemanticError(msg, line=ctx.start.line, column=ctx.start.column)
        return TypeNode(base=first, dimensions=dims)

    def _raise_ctx(self, ctx, msg: str):
        raise SemanticError(msg, line=ctx.start.line, column=ctx.start.column)

    def _callee_pretty_name(self, node):
        if isinstance(node, Variable):
            return node.name
        if isinstance(node, PropertyAccess):
            return node.property
        return node.__class__.__name_