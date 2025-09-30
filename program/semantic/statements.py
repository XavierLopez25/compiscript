from CompiscriptParser import CompiscriptParser
from AST.ast_nodes import *
from AST.symbol_table import *

class Statements:
    # ---- Enter/Exit Blocks ({...}) ----
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        stmts = [ self.visit(s) for s in ctx.statement() ]
        return Program(statements=stmts)
    
    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        old = self.state.current_scope
        self.state.current_scope = Scope(parent=old)
        stmts = []
        terminated = False
        try:
            for sctx in ctx.statement():
                if terminated:
                    self._raise_ctx(sctx, "dead code: statement unreachable after return/break/continue")
                s = self.visit(sctx)
                stmts.append(s)

                # Does this statement guarantee to terminate the flow of the block?
                if isinstance(s, ReturnStatement):
                    terminated = True
                elif isinstance(s, BreakStatement) and (self.switch_depth > 0 or self.loop_depth > 0):
                    terminated = True
                elif isinstance(s, ContinueStatement) and self.loop_depth > 0:
                    terminated = True
                elif getattr(s, "terminates", False):
                    terminated = True
        finally:
            self.state.current_scope = old

        block = Block(statements=stmts)
        block.terminates = terminated
        return block


    # ---- Variable/Constant Declarations ----
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()

        # Obtain the TypeNode robustly
        tctx = None
        if hasattr(ctx, "typeAnnotation") and ctx.typeAnnotation():
            tctx = ctx.typeAnnotation().type_()
        elif hasattr(ctx, "type_") and ctx.type_():
            # inline annotation: Identifier ':' type
            tctx = ctx.type_()

        type_node = self.visit(tctx) if tctx else None
        if (hasattr(ctx, "typeAnnotation") and ctx.typeAnnotation()) or (hasattr(ctx, "type_") and ctx.type_()):
            if type_node is None:
                raise SemanticError("BUG: type annotated but TypeNode not resolved")

        init_node = self.visit(ctx.initializer().expression()) if ctx.initializer() else None

        # Inference only if NO annotation and init is primitive
        if type_node is None and init_node is not None and init_node.type is not None:
            type_node = self._type_node_from_enum(init_node.type)

        sym = Symbol(name, type_node, is_const=False, kind="var")
        self.state.current_scope.define(sym)

        if init_node is not None:
            if not self._types_compatible_assign(type_node, init_node):
                raise SemanticError(f"Assignment incompatible with '{name}'")

        return VariableDeclaration(name, type_node, init_node, is_const=False)


    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()

        tctx = None
        if hasattr(ctx, "typeAnnotation") and ctx.typeAnnotation():
            tctx = ctx.typeAnnotation().type_()
        elif hasattr(ctx, "type_") and ctx.type_():
            tctx = ctx.type_()

        type_node = self.visit(tctx) if tctx else None
        if (hasattr(ctx, "typeAnnotation") and ctx.typeAnnotation()) or (hasattr(ctx, "type_") and ctx.type_()):
            if type_node is None:
                raise SemanticError("BUG: type annotated but TypeNode not resolved")

        init_node = self.visit(ctx.expression())
        if init_node is None:
            raise SemanticError(f"Constant '{name}' must be initialized")

        if type_node is None and init_node.type is not None:
            type_node = self._type_node_from_enum(init_node.type)

        sym = Symbol(name, type_node, is_const=True, kind="var")
        self.state.current_scope.define(sym)

        if not self._types_compatible_assign(type_node, init_node):
            raise SemanticError(f"Assignment incompatible with constant '{name}'")

        return VariableDeclaration(name, type_node, init_node, is_const=True)

    # ---- Sentences ----
    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        _ = self.visit(ctx.expression())
        return _

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr = self.visit(ctx.expression())
        return PrintStatement(expr)

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        # 1) x = expr ;
        if ctx.Identifier() and ctx.getChildCount() >= 4 and ctx.getChild(1).getText() == '=':
            name = ctx.Identifier().getText()
            sym  = self.state.current_scope.lookup(name)
            if sym.is_const:
                raise SemanticError(f"Cannot assign to constant '{name}'")
            value = self.visit(ctx.expression(0))
            if not self._types_compatible_assign(sym.type_node, value):
                raise SemanticError(f"Assignment incompatible with '{name}'")
            node = AssignmentStatement(target=Variable(name), value=value)
            node.type = value.type
            return node

        # 2) <expr> . prop = expr ;
        # We use the tree: expression(0) '.' Identifier '=' expression(1)
        if ctx.getChildCount() >= 6 and ctx.getChild(1).getText() != '=':
            obj   = self.visit(ctx.expression(0))
            prop  = ctx.Identifier().getText()
            value = self.visit(ctx.expression(1))
            target = PropertyAccess(obj, prop)

            obj_tn = self._expr_typenode(obj)
            if self._is_class_typenode(obj_tn):
                mem = self._lookup_member(obj_tn.base, prop)
                if mem["kind"] != "field":
                    raise SemanticError(f"Cannot assign to member '{prop}' (not a field)")
                field_tn = mem["type"]
                if not self._types_compatible_assign(field_tn, value):
                    raise SemanticError(f"Assignment incompatible with field '{prop}'")
            else: 
                self._raise_ctx(ctx, "property assignment on non-class value")

            # if it's not a class, we let it pass (no type info)
            node = AssignmentStatement(target=target, value=value)
            node.type = getattr(value, "type", None)
            return node

        raise SemanticError("Invalid assignment")

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_ctx = ctx.expression()
        cond = self.visit(cond_ctx)
        if cond.type != Type.BOOLEAN:
            self._raise_ctx(cond_ctx, "if condition must be boolean!")
        then_block = self.visit(ctx.block(0))
        else_block = self.visit(ctx.block(1)) if ctx.block(1) else None

        node = IfStatement(cond, then_block, else_block)
        # The if "ends" if both branches end
        node.terminates = bool(else_block) and getattr(then_block, "terminates", False) and getattr(else_block, "terminates", False)
        return node


    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_ctx = ctx.expression()
        cond = self.visit(cond_ctx)
        if cond.type != Type.BOOLEAN:
            self._raise_ctx(cond_ctx, "while condition must be boolean!")
        self.loop_depth += 1
        body = self.visit(ctx.block())
        self.loop_depth -= 1
        return WhileStatement(cond, body)

    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        self.loop_depth += 1
        body = self.visit(ctx.block())
        self.loop_depth -= 1
        cond_ctx = ctx.expression()
        cond = self.visit(cond_ctx)
        if cond.type != Type.BOOLEAN:
            self._raise_ctx(cond_ctx, "do-while condition must be boolean!")
        return DoWhileStatement(body, cond) 

    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        old_scope = self.state.current_scope
        self.state.current_scope = Scope(parent=old_scope)
        try:
            init = None
            if ctx.variableDeclaration():
                init = self.visit(ctx.variableDeclaration())
            elif ctx.assignment():
                init = self.visit(ctx.assignment())

            cond = None
            cond_ctx = ctx.expression(0) if len(ctx.expression()) >= 1 else None
            if cond_ctx:
                cond = self.visit(cond_ctx)
                if cond.type != Type.BOOLEAN:
                    self._raise_ctx(cond_ctx, "for condition must be boolean!")
            upd = self.visit(ctx.expression(1)) if len(ctx.expression()) >= 2 else None

            self.loop_depth += 1
            body = self.visit(ctx.block())
            self.loop_depth -= 1

            return ForStatement(init, cond, upd, body)
        finally:
            self.state.current_scope = old_scope


    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        var_name = ctx.Identifier().getText()
        iterable = self.visit(ctx.expression())

        old_scope = self.state.current_scope
        self.state.current_scope = Scope(parent=old_scope)

        elem_tn = None
        it_tn = self._expr_typenode(iterable)
        if it_tn and it_tn.dimensions > 0:
            elem_tn = self._array_element_typenode(it_tn)

        self.state.current_scope.define(Symbol(var_name, elem_tn, is_const=False, kind="var"))

        self.loop_depth += 1
        body = self.visit(ctx.block())
        self.loop_depth -= 1

        self.state.current_scope = old_scope

        return ForEachStatement(var_name, iterable, body)

    def visitBreakStatement(self, ctx):
        if self.loop_depth <= 0 and self.switch_depth <= 0:
            self._raise_ctx(ctx, "break out of loop or switch")
        return BreakStatement()

    def visitContinueStatement(self, ctx):
        if self.loop_depth <= 0:
            self._raise_ctx(ctx, "continue out of loop")
        return ContinueStatement()

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        value = self.visit(ctx.expression()) if ctx.expression() else None
        # out of function:
        if not self.func_return_stack:
            self._raise_ctx(ctx, "return outside of function")
        expected = self.func_return_stack[-1]  # TypeNode
        if expected.base != "void":
            if value is None:
                self._raise_ctx(ctx, "return without value in non-void function")

            if not self._types_compatible_assign(expected, value):  
                err_ctx = ctx.expression() if ctx.expression() else ctx
                self._raise_ctx(err_ctx, "incompatible return type")
        else:
            if value is not None:
                self._raise_ctx(ctx.expression(), "return with value in void function")

        return ReturnStatement(value)

    # -------------- Try/Catch & Switch ------------------
    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        try_block = self.visit(ctx.block(0))
        exc_name  = ctx.Identifier().getText()
        old = self.state.current_scope
        self.state.current_scope = Scope(parent=old)
        # Exception variable is treated as string for message concatenation
        self.state.current_scope.define(Symbol(exc_name, TypeNode(base="string"), is_const=True))
        catch_block = self.visit(ctx.block(1))
        self.state.current_scope = old

        node = TryCatchStatement(try_block, exc_name, catch_block)
        node.terminates = getattr(try_block, "terminates", False) and getattr(catch_block, "terminates", False)
        return node


    def visitSwitchStatement(self, ctx: CompiscriptParser.SwitchStatementContext):
        old_scope = self.state.current_scope
        self.state.current_scope = Scope(parent=old_scope)
        self.switch_depth += 1
        try:
            expr_ctx = ctx.expression()
            switch_expr = self.visit(expr_ctx)
            if switch_expr.type not in (Type.INTEGER, Type.STRING, Type.BOOLEAN):
                self._raise_ctx(expr_ctx, f"switch condition must be integer, boolean or string, got {switch_expr.type}")

            cases = []
            for c in ctx.switchCase():
                case_parent = self.state.current_scope
                self.state.current_scope = Scope(parent=case_parent)
                try:
                    val = self.visit(c.expression())
                    stmts = [self.visit(s) for s in c.statement()]
                    cases.append(SwitchCase(val, stmts))
                finally:
                    self.state.current_scope = case_parent

            default_stmts = None
            if ctx.defaultCase():
                def_parent = self.state.current_scope
                self.state.current_scope = Scope(parent=def_parent)
                try:
                    default_stmts = [self.visit(s) for s in ctx.defaultCase().statement()]
                finally:
                    self.state.current_scope = def_parent

            return SwitchStatement(switch_expr, cases, default_stmts)
        finally:
            self.switch_depth -= 1
            self.state.current_scope = old_scope

    # ---- Functions & classes ----

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        # Register signature first (for recursion)
        ret_t = self.visit(ctx.type_()) if ctx.type_() else TypeNode(base="void", dimensions=0)
        params_nodes: List[Parameter] = []
        params_types: List[TypeNode]  = []
        if ctx.parameters():
            for p in ctx.parameters().parameter():
                p_name = p.Identifier().getText()
                p_type = self.visit(p.type_()) if p.type_() else None
                if p_type is None:
                    raise SemanticError(f"Parameter '{p_name}' must have a type")
                params_nodes.append(Parameter(p_name, p_type))
                params_types.append(p_type)

        sym = Symbol(name, type_node=None, is_const=True, kind="func")
        sym.params      = params_types
        sym.return_type = ret_t
        self.state.current_scope.define(sym)

        # Create function scope and define parameters
        old = self.state.current_scope
        self.state.current_scope = Scope(parent=old)
        for pn in params_nodes:
            self.state.current_scope.define(Symbol(pn.name, pn.type_node, is_const=False, kind="var"))

        # Check body against return stack
        self.func_return_stack.append(ret_t)
        body = self.visit(ctx.block())
        self.func_return_stack.pop()
        self.state.current_scope = old

        return FunctionDeclaration(name, params_nodes, ret_t, body)
