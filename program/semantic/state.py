from dataclasses import dataclass, field
from typing import Optional, List, Dict
from AST.symbol_table import Scope
from AST.ast_nodes import TypeNode

@dataclass
class SemanticState:
    global_scope: Scope = field(default_factory=Scope)
    current_scope: Optional[Scope] = None
    func_return_stack: List[Optional[TypeNode]] = field(default_factory=list)
    loop_depth: int = 0
    switch_depth: int = 0
    classes: Dict[str, dict] = field(default_factory=dict)
    current_class: Optional[str] = None

    def __post_init__(self):
        if self.current_scope is None:
            self.current_scope = self.global_scope