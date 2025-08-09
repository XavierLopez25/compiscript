import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from SemanticVisitor import SemanticVisitor
from AST.symbol_table import SemanticError


from AST.ast_to_dot import write_dot

def main(argv):
    input_stream = FileStream(argv[1])
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()

    sem = SemanticVisitor()
    try:
        ast = sem.visit(tree)
        print("Semantic analysis completed successfully.")
        write_dot(ast, "ast.dot")
        print("AST -> ast.dot (usa: dot -Tpng ast.dot -o ast.png)")

    except SemanticError as e:
        print(f"Semantic error: {e}")

if __name__ == '__main__':
    main(sys.argv)