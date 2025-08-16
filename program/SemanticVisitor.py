from CompiscriptVisitor import CompiscriptVisitor
from semantic.state import SemanticState
from semantic.helpers import Helpers
from semantic.statements import Statements
from semantic.expressions import Expressions
from semantic.classes import Classes
from semantic.types import Types


class SemanticVisitor(Types, Statements, Expressions, Classes, Helpers, CompiscriptVisitor):
    def __init__(self):
        self.state = SemanticState()

    # ---- proxys to state ----
    @property
    def global_scope(self): return self.state.global_scope

    @property
    def current_scope(self): return self.state.current_scope
    @current_scope.setter
    def current_scope(self, v): self.state.current_scope = v

    @property
    def func_return_stack(self): return self.state.func_return_stack

    @property
    def loop_depth(self): return self.state.loop_depth
    @loop_depth.setter
    def loop_depth(self, v): self.state.loop_depth = v

    @property
    def switch_depth(self): return self.state.switch_depth
    @switch_depth.setter
    def switch_depth(self, v): self.state.switch_depth = v

    @property
    def classes(self): return self.state.classes

    @property
    def current_class(self): return self.state.current_class
    @current_class.setter
    def current_class(self, v): self.state.current_class = v
