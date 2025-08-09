from CompiscriptParser import CompiscriptParser
from AST.ast_nodes import *
from AST.symbol_table import *

class Expressions:
    
    def visitExpression(self, ctx: CompiscriptParser.ExpressionContext):
        return self.visit(ctx.assignmentExpr())

    # assignmentExpr:
    #   lhs=leftHandSide '=' assignmentExpr            # AssignExpr
    def visitAssignExpr(self, ctx: CompiscriptParser.AssignExprContext):
        target = self._lhs_to_target(self.visit(ctx.lhs))
        value  = self.visit(ctx.assignmentExpr())
        # If is Variable: validate symbol
        if isinstance(target, Variable):
            sym = self.state.current_scope.lookup(target.name)
            if sym.is_const:
                raise SemanticError(f"Cannot assign to constant '{target.name}'")
            if not self._types_compatible_assign(sym.type_node, value):
                raise SemanticError(f"Cannot assign to '{target.name}'")
            node = AssignmentStatement(target, value)
            node.type = value.type
            return node

        # Assignment to array element: a[i] = value
        if isinstance(target, IndexExpression):
            base_tn = self._expr_typenode(target.array)
            if base_tn is None or base_tn.dimensions == 0:
                raise SemanticError("Left-hand side index expression is not an array")
            elem_tn = self._array_element_typenode(base_tn)
            if not self._types_compatible_assign(elem_tn, value):
                raise SemanticError("Cannot assign to array element")
            node = AssignmentStatement(target, value)
            node.type = getattr(value, "type", None)
            return node

        # Assignment to property: obj.prop = value (only fields; methods are not assignable)
        if isinstance(target, PropertyAccess):
            obj_tn = self._expr_typenode(target.object)
            if not self._is_class_typenode(obj_tn):
                # If not a class, we cannot validate here
                node = AssignmentStatement(target, value)
                node.type = getattr(value, "type", None)
                return node
            mem = self._lookup_member(obj_tn.base, target.property)
            if mem["kind"] != "field":
                raise SemanticError(f"Cannot assign to member '{target.property}' (not a field)")
            field_tn = mem["type"]
            if not self._types_compatible_assign(field_tn, value):
                raise SemanticError(f"Cannot assign to field '{target.property}'")
            node = AssignmentStatement(target, value)
            node.type = getattr(value, "type", None)
            return node

    #   lhs=leftHandSide '.' Identifier '=' assignmentExpr # PropertyAssignExpr
    def visitPropertyAssignExpr(self, ctx: CompiscriptParser.PropertyAssignExprContext):
        base   = self.visit(ctx.lhs)
        prop   = ctx.Identifier().getText()
        value  = self.visit(ctx.assignmentExpr())
        target = PropertyAccess(base, prop)

        obj_tn = self._expr_typenode(base)
        if self._is_class_typenode(obj_tn):
            mem = self._lookup_member(obj_tn.base, prop)
            if mem["kind"] != "field":
                raise SemanticError(f"Cannot assign to member '{prop}' (not a field)")
            field_tn = mem["type"]
            if not self._types_compatible_assign(field_tn, value):
                raise SemanticError(f"Cannot assign to field '{prop}'")

        node = AssignmentStatement(target, value)
        node.type = getattr(value, "type", None)
        return node


    #   | conditionalExpr                                # ExprNoAssign
    def visitExprNoAssign(self, ctx: CompiscriptParser.ExprNoAssignContext):
        return self.visit(ctx.conditionalExpr())

    # conditionalExpr: logicalOrExpr ('?' expression ':' expression)?
    def visitTernaryExpr(self, ctx: CompiscriptParser.TernaryExprContext):
        base = self.visit(ctx.logicalOrExpr())
        if ctx.getChildCount() == 1:
            return base
        cond = base
        self._ensure_boolean(cond, "condición del operador ternario")
        t_val = self.visit(ctx.expression(0))
        f_val = self.visit(ctx.expression(1))
        # Both arms must be compatible (same base)
        if t_val.type != f_val.type:
            # Allow integer/float → float
            if self._expr_type_is_numeric(t_val.type) and self._expr_type_is_numeric(f_val.type):
                result_t = self._promote_numeric(t_val.type, f_val.type)
            else:
                raise SemanticError("Incompatible types in ternary branches")
        else:
            result_t = t_val.type
        node = TernaryOp(cond, t_val, f_val)
        node.type = result_t
        return node

    # logicalOrExpr: logicalAndExpr ( '||' logicalAndExpr )*
    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        node = self.visit(ctx.logicalAndExpr(0))
        # If there is NO '||', return as is (do not require boolean)
        if len(ctx.logicalAndExpr()) == 1:
            return node
        # From here on there is '||'
        self._ensure_boolean(node, "operación '||'")
        for i in range(1, len(ctx.logicalAndExpr())):
            right = self.visit(ctx.logicalAndExpr(i))
            self._ensure_boolean(right, "operación '||'")
            node = BinaryOperation(node, right, '||')
            node.type = Type.BOOLEAN
        return node

    # logicalAndExpr: equalityExpr ( '&&' equalityExpr )*
    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        node = self.visit(ctx.equalityExpr(0))
        # If there is NO '&&', return as is (do not require boolean)
        if len(ctx.equalityExpr()) == 1:
            return node
        # From here on there is '&&'
        self._ensure_boolean(node, "operación '&&'")
        for i in range(1, len(ctx.equalityExpr())):
            right = self.visit(ctx.equalityExpr(i))
            self._ensure_boolean(right, "operación '&&'")
            node = BinaryOperation(node, right, '&&')
            node.type = Type.BOOLEAN
        return node

    # equalityExpr: relationalExpr ( ('==' | '!=') relationalExpr )*
    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        node = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            op = ctx.getChild(2*i - 1).getText()  # '==' | '!='
            right = self.visit(ctx.relationalExpr(i))
            # Compatibility: same type or both numeric
            if node.type != right.type:
                if self._expr_type_is_numeric(node.type) and self._expr_type_is_numeric(right.type):
                    pass
                else:
                    raise SemanticError(f"Comparison '{op}' with different types: {node.type} vs {right.type}")
            node = BinaryOperation(node, right, op)
            node.type = Type.BOOLEAN
        return node

    # relationalExpr: additiveExpr ( ('<' | '<=' | '>' | '>=') additiveExpr )*
    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        node = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            op = ctx.getChild(2*i - 1).getText()
            right = self.visit(ctx.additiveExpr(i))
            # Compatibility: both must be numeric
            self._ensure_numeric(node, op)
            self._ensure_numeric(right, op)
            node = BinaryOperation(node, right, op)
            node.type = Type.BOOLEAN
        return node

    # additiveExpr: multiplicativeExpr ( ('+' | '-') multiplicativeExpr )*
    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        node = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            op = ctx.getChild(2*i - 1).getText()  # '+', '-'
            right = self.visit(ctx.multiplicativeExpr(i))

            if op == '+':
                # if either is string -> concatenation → string
                if getattr(node, "type", None) == Type.STRING or getattr(right, "type", None) == Type.STRING:
                    node = BinaryOperation(node, right, op)
                    node.type = Type.STRING
                    continue

            # normal arithmetic case
            self._ensure_numeric(node, op)
            self._ensure_numeric(right, op)
            result_type = self._promote_numeric(node.type, right.type)
            node = BinaryOperation(node, right, op)
            node.type = result_type
        return node


    # multiplicativeExpr: unaryExpr ( ('*' | '/' | '%') unaryExpr )*
    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        node = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            op = ctx.getChild(2*i - 1).getText()  # '*', '/', '%'
            right = self.visit(ctx.unaryExpr(i))
            # '%' is limited to integer | integer (typical behavior)
            if op == '%':
                if node.type != Type.INTEGER or right.type != Type.INTEGER:
                    raise SemanticError("Operator '%' requires integer operands")
                result_type = Type.INTEGER
            else:
                self._ensure_numeric(node, op)
                self._ensure_numeric(right, op)
                result_type = self._promote_numeric(node.type, right.type)
            node = BinaryOperation(node, right, op)
            node.type = result_type
        return node

    # unaryExpr: ('-' | '!') unaryExpr | primaryExpr
    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            operand = self.visit(ctx.unaryExpr())
            if op == '-':
                self._ensure_numeric(operand, op)
                t = operand.type
            elif op == '!':
                self._ensure_boolean(operand, "operator '!'")
                t = Type.BOOLEAN
            else:
                raise SemanticError(f"Unknown unary operator: {op}")
            node = UnaryOperation(operand, op)
            node.type = t
            return node
        else:
            return self.visit(ctx.primaryExpr())

    # primaryExpr: literalExpr | leftHandSide | '(' expression ')'
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        # paréntesis
        return self.visit(ctx.expression())

    # literalExpr: Literal | arrayLiteral | 'null' | 'true' | 'false'
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        text = ctx.getText()
        if text == 'null':
            return NullLiteral()
        if text == 'true':
            return Literal(True, Type.BOOLEAN)
        if text == 'false':
            return Literal(False, Type.BOOLEAN)
        if ctx.arrayLiteral():
            arr = self.visit(ctx.arrayLiteral())
            return arr
        # Literal → IntegerLiteral | StringLiteral
        if text.startswith('"'):
            return Literal(text[1:-1], Type.STRING)
        else:
            return Literal(int(text), Type.INTEGER)

    def visitArrayLiteral(self, ctx: CompiscriptParser.ArrayLiteralContext):
        elems = []
        elem_tns: List[TypeNode] = []

        if ctx.expression():
            for ectx in ctx.expression():
                e = self.visit(ectx)
                elems.append(e)

                # Ignore nulls for unification; they are considered compatible afterwards
                if isinstance(e, NullLiteral) or getattr(e, "type", None) == Type.VOID:
                    continue

                tn = self._expr_typenode(e)
                if tn is None:
                    # Cannot infer element type -> treat as 'any'
                    tn = TypeNode(base="any", dimensions=0)
                elem_tns.append(tn)

        # Unify ELEMENT type; then the outer array adds one dimension
        elem_tn = self._unify_array_element_types(elem_tns) if elem_tns else TypeNode(base="any", dimensions=0)
        arr_tn = TypeNode(base=elem_tn.base, dimensions=elem_tn.dimensions + 1)

        node = ArrayLiteral(elems)
        node.type_node = arr_tn
        return node


    # leftHandSide: primaryAtom (suffixOp)*
    def visitLeftHandSide(self, ctx: CompiscriptParser.LeftHandSideContext):
        node = self.visit(ctx.primaryAtom())
        for sop in ctx.suffixOp():
            first_tok = sop.getChild(0).getText()
            if first_tok == '(':
                args = []
                if sop.arguments():
                    for e in sop.arguments().expression():
                        args.append(self.visit(e))
                call = CallExpression(node, args)

                if isinstance(node, Variable):
                    sym = self.state.current_scope.lookup(node.name)
                    if getattr(sym, "kind", None) == "func":
                        if len(args) != len(sym.params):
                            raise SemanticError(f"Function '{node.name}' expects {len(sym.params)} arguments")
                        for a, p in zip(args, sym.params):
                            if not self._types_compatible_assign(p, a):
                                raise SemanticError(f"Incompatible argument type for '{node.name}'")
                        ret_tn = sym.return_type
                        call.type_node = ret_tn
                        if ret_tn.dimensions == 0 and self._type_name_is_primitive(ret_tn.base):
                            prim = self._get_primitive_enum_from_base(ret_tn.base)
                            if prim is not None:
                                call.type = prim

                if isinstance(node, PropertyAccess) and hasattr(node, "method_sig"):
                    sig = node.method_sig
                    if len(args) != len(sig["params"]):
                        raise SemanticError(f"Method '{node.property}' expects {len(sig['params'])} arguments")
                    for a, p in zip(args, sig["params"]):
                        if not self._types_compatible_assign(p, a):
                            raise SemanticError(f"Incompatible argument type for method '{node.property}'")
                    ret_tn = sig["ret"]
                    call.type_node = ret_tn
                    if ret_tn.dimensions == 0 and self._type_name_is_primitive(ret_tn.base):
                        prim = self._get_primitive_enum_from_base(ret_tn.base)
                        if prim is not None:
                            call.type = prim

                node = call

            elif first_tok == '[':
                idx = self.visit(sop.expression())
                if idx.type != Type.INTEGER:
                    raise SemanticError("Array index must be integer")

                # Verify that current node is array
                arr_tn = self._expr_typenode(node)
                if arr_tn is None or arr_tn.dimensions == 0:
                    raise SemanticError("Indexed access on non-array expression")

                elem_tn = self._array_element_typenode(arr_tn)
                idx_node = IndexExpression(node, idx)
                idx_node.type_node = elem_tn
                # if the element is primitive, also set node.type
                if elem_tn.dimensions == 0 and self._type_name_is_primitive(elem_tn.base):
                    prim = self._get_primitive_enum_from_base(elem_tn.base)
                    if prim is not None:
                        idx_node.type = prim
                node = idx_node
            elif first_tok == '.':
                prop = sop.Identifier().getText()
                pa = PropertyAccess(node, prop)

                # Type the access if the object is a class
                obj_tn = self._expr_typenode(node)
                if self._is_class_typenode(obj_tn):
                    mem = self._lookup_member(obj_tn.base, prop)
                    if mem["kind"] == "field":
                        pa.type_node = mem["type"]
                        if pa.type_node.dimensions == 0 and self._type_name_is_primitive(pa.type_node.base):
                            prim = self._get_primitive_enum_from_base(pa.type_node.base)
                            if prim is not None:
                                pa.type = prim
                    elif mem["kind"] == "method":
                        # attach the signature to validate when the Call '()' suffix is applied
                        pa.method_sig = mem["sig"]
                node = pa
            else:
                raise SemanticError("Unknown suffixOp")
        return node

    # primaryAtom alternatives listed:
    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        sym = self.state.current_scope.lookup(name)
        node = Variable(name)

        # ALWAYS propagate the symbol's type_node (arrays/classes/whatever)
        node.type_node = sym.type_node

        # If it's primitive (dims=0), also set node.type for operators
        if sym.type_node and sym.type_node.dimensions == 0 and self._is_primitive_name(sym.type_node.base):
            base = sym.type_node.base
            node.type = {
                "integer": Type.INTEGER,
                "float":   Type.FLOAT,
                "string":  Type.STRING,
                "boolean": Type.BOOLEAN,
                "void":    Type.VOID
            }[base]
        else:
            node.type = None

        return node


    def visitNewExpr(self, ctx: CompiscriptParser.NewExprContext):
        class_name = ctx.Identifier().getText()
        cls = self._lookup_class(class_name)

        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))

        # Constructor: method called 'constructor' (if it doesn't exist, arity 0)
        if "constructor" in cls["methods"]:
            sig = cls["methods"]["constructor"]
            if len(args) != len(sig["params"]):
                raise SemanticError(f"Constructor of '{class_name}' expects {len(sig['params'])} arguments")
            for a, p in zip(args, sig["params"]):
                if not self._types_compatible_assign(p, a):
                    raise SemanticError(f"Incompatible argument in constructor of '{class_name}'")
        else:
            if len(args) != 0:
                raise SemanticError(f"Class '{class_name}' does not define a constructor; 0 arguments expected")

        node = NewExpression(class_name, args)
        node.type_node = TypeNode(base=class_name, dimensions=0)
        return node


    def visitThisExpr(self, ctx: CompiscriptParser.ThisExprContext):
        if not self.current_class:
            raise SemanticError("'this' can only be used within class methods")
        node = ThisExpression()
        node.type_node = TypeNode(base=self.current_class, dimensions=0)
        return node
