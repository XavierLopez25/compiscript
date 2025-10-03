from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener as ErrorListenerA
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from SemanticVisitor import SemanticVisitor
from AST.symbol_table import SemanticError
from AST.ast_to_dot import write_dot
from tac.integrated_generator import IntegratedTACGenerator
from tac.base_generator import TACGenerationError

import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    code: str
    return_ast_dot: bool = False  # opcional: devolver DOT
    generate_tac: bool = False    # opcional: generar TAC

class Diagnostic(BaseModel):
    kind: str               # "lexer" | "parser" | "semantic" | "tac"
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    length: Optional[int] = None  # si disponible

class TACInfo(BaseModel):
    code: List[str]           # Lista de instrucciones TAC
    instruction_count: int    # Número total de instrucciones
    temporaries_used: int     # Número de temporales utilizados
    functions_registered: int # Número de funciones registradas
    validation_errors: List[str] = []  # Errores de validación TAC

class AnalyzeResponse(BaseModel):
    ok: bool
    diagnostics: List[Diagnostic]
    ast_dot: Optional[str] = None
    tac: Optional[TACInfo] = None

class CollectingErrorListener(ErrorListenerA):
    def __init__(self):
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        length = None
        try:
            if offendingSymbol is not None and getattr(offendingSymbol, "start", None) is not None:
                start = offendingSymbol.start
                stop = getattr(offendingSymbol, "stop", start)
                if stop is not None and start is not None and stop >= start:
                    length = (stop - start + 1)
        except Exception:
            pass
        self.errors.append(Diagnostic(kind="parser", message=msg, line=line, column=column, length=length))

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    code = req.code

    input_stream = InputStream(code)

    lex_err = CollectingErrorListener()
    parser_err = CollectingErrorListener()

    lexer = CompiscriptLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(lex_err)

    token_stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(parser_err)

    # Parse
    tree = parser.program()

    diagnostics: List[Diagnostic] = []
    diagnostics.extend([Diagnostic(kind="lexer", message=e.message, line=e.line, column=e.column, length=e.length)
                        for e in lex_err.errors])
    diagnostics.extend(parser_err.errors)

    ast_dot_str: Optional[str] = None
    tac_info: Optional[TACInfo] = None
    ok = False

    if not diagnostics:
        sem = SemanticVisitor()
        try:
            ast = sem.visit(tree)
            ok = True

            if req.return_ast_dot:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".dot") as tmp:
                    write_dot(ast, tmp.name)
                    tmp.flush()
                    with open(tmp.name, "r", encoding="utf-8") as f:
                        ast_dot_str = f.read()

            if req.generate_tac:
                try:
                    tac_generator = IntegratedTACGenerator()
                    tac_lines = tac_generator.generate_program(ast)

                    # Get statistics
                    stats = tac_generator.get_complete_statistics()

                    # Validate TAC
                    validation_errors = tac_generator.validate_tac()

                    # Extract temporaries count
                    temporaries_used = 0
                    if 'integrated_stats' in stats and 'temporaries_used' in stats['integrated_stats']:
                        temporaries_used = stats['integrated_stats']['temporaries_used']
                    else:
                        # Fallback: count temporaries from instructions
                        temporaries_used = sum(1 for line in tac_lines if 't' in line and '=' in line)

                    # Get function count
                    functions_registered = len(tac_generator.function_generator._function_registry)

                    tac_info = TACInfo(
                        code=tac_lines,
                        instruction_count=len(tac_lines),
                        temporaries_used=temporaries_used,
                        functions_registered=functions_registered,
                        validation_errors=validation_errors
                    )

                except TACGenerationError as e:
                    diagnostics.append(Diagnostic(kind="tac", message=f"TAC generation error: {str(e)}"))
                except Exception as e:
                    diagnostics.append(Diagnostic(kind="tac", message=f"Unexpected TAC error: {str(e)}"))

        except SemanticError as e:
            diagnostics.append(Diagnostic(kind="semantic", message=str(e), line=e.line, column=e.column))

    return AnalyzeResponse(ok=ok, diagnostics=diagnostics, ast_dot=ast_dot_str, tac=tac_info)