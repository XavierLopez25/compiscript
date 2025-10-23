from CompiscriptParser import CompiscriptParser
from AST.ast_nodes import *
from AST.symbol_table import *

class Classes:
    def _visitMethodDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext, class_name: str):
        # Check if Identifier exists (can be None if parser failed on keyword)
        if ctx.Identifier() is None:
            self._raise_ctx(
                ctx,
                f"Invalid method declaration in class '{class_name}': method name is missing or uses a reserved keyword"
            )

        name = ctx.Identifier().getText()

        # Validate against built-in functions (inherited from Statements)
        if hasattr(self, 'BUILTIN_FUNCTIONS') and name in self.BUILTIN_FUNCTIONS:
            self._raise_ctx(
                ctx,
                f"Cannot use built-in function name '{name}' as a method in class '{class_name}'. "
                f"'{name}' is a reserved function provided by the runtime."
            )

        ret_t = self.visit(ctx.type_()) if ctx.type_() else TypeNode(base="void", dimensions=0)

        params_nodes, params_types = [], []
        if ctx.parameters():
            for p in ctx.parameters().parameter():
                p_name = p.Identifier().getText()
                p_type = self.visit(p.type_()) if p.type_() else None
                if p_type is None:
                    self._raise_ctx(p, f"Parameter '{p_name}' must have a type (method '{name}' in class '{class_name}')")
                params_nodes.append(Parameter(p_name, p_type))
                params_types.append(p_type)

        # The method is not defined as a global symbol; its signature remains in self.classes
        # Method scope
        old = self.current_scope
        self.current_scope = Scope(parent=old)

        # Inject 'this' with the current class type
        self.current_scope.define(Symbol("this", TypeNode(base=class_name), is_const=True))

        # Parameters in scope
        for pn in params_nodes:
            self.current_scope.define(Symbol(pn.name, pn.type_node, is_const=False))

        # Check body (return stack)
        self.func_return_stack.append(ret_t)
        body = self.visit(ctx.block())
        self.func_return_stack.pop()

        self.current_scope = old

        return FunctionDeclaration(name, params_nodes, ret_t, body)


    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        name = ctx.Identifier(0).getText()
        superclass = ctx.Identifier(1).getText() if ctx.Identifier().__len__() == 2 else None

        # Register class symbol (for identifier resolution)
        sym = Symbol(name, type_node=TypeNode(base=name), is_const=True, kind="class")
        self.current_scope.define(sym)

        # Create initial entry: copy members from super if it exists
        if superclass:
            if superclass not in self.classes:
                self._raise_ctx(ctx, f"Superclass '{superclass}' is not declared")
            base_fields  = dict(self.classes[superclass]["fields"])
            base_methods = dict(self.classes[superclass]["methods"])
        else:
            base_fields, base_methods = {}, {}

        self.classes[name] = {
            "fields":  base_fields,
            "methods": base_methods,
            "super":   superclass
        }

        # Class scope + current class marker
        old_scope = self.current_scope
        old_class = self.current_class
        self.current_scope = Scope(parent=old_scope)
        self.current_class = name

        members = []
        for m in ctx.classMember():
            # Detect member type by concrete rule:
            if m.variableDeclaration():
                node = self.visit(m.variableDeclaration())
                # Register field
                if node.declared_type is None:
                    self._raise_ctx(m, f"Field '{node.name}' in class '{name}' must have a type")
                if node.name in self.classes[name]["fields"]:
                    self._raise_ctx(m, f"Field '{node.name}' in class '{name}' is duplicated")
                self.classes[name]["fields"][node.name] = node.declared_type
                members.append(node)

            elif m.constantDeclaration():
                node = self.visit(m.constantDeclaration())
                if node.declared_type is None:
                    self._raise_ctx(m, f"Field '{node.name}' in class '{name}' must have a type")
                if node.name in self.classes[name]["fields"]:
                    self._raise_ctx(m, f"Field '{node.name}' in class '{name}' is duplicated")
                self.classes[name]["fields"][node.name] = node.declared_type
                members.append(node)

            elif m.functionDeclaration():
                fn = self._visitMethodDeclaration(m.functionDeclaration(), class_name=name)
                # Register method (override check)
                self._check_method_override(name, fn.name, [p.type_node for p in fn.parameters], fn.return_type)
                self.classes[name]["methods"][fn.name] = {
                    "params": [p.type_node for p in fn.parameters],
                    "ret":    fn.return_type
                }
                members.append(fn)
            else:
                self._raise_ctx(m, "Unknown class member")

        self.current_scope = old_scope
        self.current_class = old_class

        return ClassDeclaration(name, superclass, members)
