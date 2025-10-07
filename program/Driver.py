import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from SemanticVisitor import SemanticVisitor
from AST.symbol_table import SemanticError
import json

from AST.ast_to_dot import write_dot
from tac.integrated_generator import IntegratedTACGenerator
from tac.base_generator import TACGenerationError
from tac.symbol_annotator import SymbolAnnotator

def main(argv):
    input_stream = FileStream(argv[1], encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    sem = SemanticVisitor()
    
    try:
        ast = sem.visit(tree)
        print("✓ Semantic analysis completed successfully.")

        # Generate AST visualization
        write_dot(ast, "ast.dot")
        print("✓ AST -> ast.dot (usa: dot -Tpng ast.dot -o ast.png)")

        # Debug: Check AST structure
        print(f"\n--- AST Debug Info ---")
        print(f"  AST type: {type(ast).__name__}")
        if hasattr(ast, 'statements'):
            print(f"  Number of statements: {len(ast.statements)}")
            print(f"  Statement types: {[type(s).__name__ for s in ast.statements[:10]]}")  # First 10
        else:
            print(f"  AST has no 'statements' attribute")

        # Generate TAC
        print("\n--- TAC Generation ---")
        try:
            tac_generator = IntegratedTACGenerator()
            tac_lines = tac_generator.generate_program(ast)

            # Save TAC to file
            with open("output.tac", "w") as f:
                for line in tac_lines:
                    f.write(line + "\n")

            print("✓ TAC generation completed successfully.")
            print(f"✓ Generated {len(tac_lines)} TAC instructions")
            print("✓ TAC -> output.tac")

            # Validate TAC
            validation_errors = tac_generator.validate_tac()
            if validation_errors:
                print("\n⚠ TAC Validation Warnings:")
                for error in validation_errors:
                    print(f"  - {error}")
            else:
                print("✓ TAC validation passed")

            # Print statistics
            stats = tac_generator.get_complete_statistics()
            print("\n--- TAC Statistics ---")
            print(f"  Total instructions: {stats['total_instructions']}")

            # Count functions from the function registry
            func_count = len(tac_generator.function_generator._function_registry)
            print(f"  Functions registered: {func_count}")

            if 'integrated_stats' in stats and 'temporaries_used' in stats['integrated_stats']:
                print(f"  Temporaries used: {stats['integrated_stats']['temporaries_used']}")
            else:
                # Count temporaries from instructions
                temp_count = sum(1 for line in tac_lines if 't' in line and '=' in line)
                print(f"  Temporaries used (approx): {temp_count}")

            # Annotate symbol table with memory information
            print("\n--- Annotating Symbol Table ---")
            annotator = SymbolAnnotator(tac_generator.address_manager)
            annotator.annotate_scope_tree(sem.global_scope)
            print("✓ Symbol table annotated with memory info")

            # Save annotated symbol table
            with open("scopes.json", "w") as f:
                json.dump(sem.global_scope.to_dict(), f, indent=2)
            print("✓ Scopes -> scopes.json")

            # Optionally print TAC to console
            print("\n--- Generated TAC ---")
            for line in tac_lines:
                print(line)

        except TACGenerationError as e:
            print(f"✗ TAC generation error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error during TAC generation: {e}")
            import traceback
            traceback.print_exc()

    except SemanticError as e:
        print(f"✗ Semantic error: {e}")

if __name__ == '__main__':
    main(sys.argv)