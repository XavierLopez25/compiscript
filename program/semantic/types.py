from CompiscriptParser import CompiscriptParser
from AST.ast_nodes import TypeNode

class Types:
    def visitTypeAnnotation(self, ctx: CompiscriptParser.TypeAnnotationContext) -> TypeNode:
        return self.visit(ctx.type_())

    def visitType(self, ctx: CompiscriptParser.TypeContext) -> TypeNode:
        text = ctx.getText()
        base = ctx.baseType().getText()
        # Only normalize if primitive
        if base in ("integer", "float", "string", "boolean", "void"):
            base = base.lower()
        dims = text.count('[')
        return TypeNode(base=base, dimensions=dims)