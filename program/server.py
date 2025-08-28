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

class Diagnostic(BaseModel):
    kind: str               # "lexer" | "parser" | "semantic"
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    length: Optional[int] = None  # si disponible

class AnalyzeResponse(BaseModel):
    ok: bool
    diagnostics: List[Diagnostic]
    ast_dot: Optional[str] = None

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

        except SemanticError as e:
            diagnostics.append(Diagnostic(kind="semantic", message=str(e)))

    return AnalyzeResponse(ok=ok, diagnostics=diagnostics, ast_dot=ast_dot_str)