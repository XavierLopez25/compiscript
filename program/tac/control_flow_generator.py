from typing import Optional

from AST.ast_nodes import (
    Program,
    Block,
    IfStatement,
    WhileStatement,
    ForStatement,
    DoWhileStatement,
    ForEachStatement,
    SwitchStatement,
    SwitchCase,
    BreakStatement,
    ContinueStatement,
    ReturnStatement,
    VariableDeclaration,
    AssignmentStatement,
    ASTNode
)

from .expression_generator import ExpressionTACGenerator
from .instruction import (
    AssignInstruction,
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
    ReturnInstruction,
    ArrayAccessInstruction,
    CommentInstruction
)
from .base_generator import TACGenerationError


class ControlFlowTACGenerator(ExpressionTACGenerator):
    """Generate TAC for control-flow constructs (Part 3/4)."""

    # ------------------------------------------------------------------
    # High-level entry points
    # ------------------------------------------------------------------
    def visit_Program(self, node: Program) -> None:
        for statement in node.statements:
            self.visit(statement)

    def visit_Block(self, node: Block) -> None:
        self.enter_scope()
        for statement in node.statements:
            self.visit(statement)
        self.exit_scope()

    # ------------------------------------------------------------------
    # Variable declarations
    # ------------------------------------------------------------------
    def visit_VariableDeclaration(self, node: VariableDeclaration) -> Optional[str]:
        if node.initializer is not None:
            # Generate code for the initializer expression
            value = self.visit(node.initializer)
            # Assign the result to the variable
            self.emit(AssignInstruction(node.name, value))
            return node.name
        else:
            # Variable declaration without initializer
            self.emit(CommentInstruction(f"Variable declaration: {node.name}"))
            return node.name

    # ------------------------------------------------------------------
    # Control flow statements
    # ------------------------------------------------------------------
    def visit_IfStatement(self, node: IfStatement) -> None:
        false_label = self.new_label("if_false")

        condition = self.visit(node.condition)
        self.emit(ConditionalGotoInstruction(condition, false_label, "0", "=="))

        self.visit(node.then_branch)

        if node.else_branch:
            # Check if then_branch ends with a return/goto (no need for goto end_label)
            then_has_exit = self._statement_has_exit(node.then_branch)

            if not then_has_exit:
                end_label = self.new_label("if_end")
                self.emit(GotoInstruction(end_label))

            self.emit(LabelInstruction(false_label))
            self.visit(node.else_branch)

            if not then_has_exit:
                self.emit(LabelInstruction(end_label))
        else:
            self.emit(LabelInstruction(false_label))

    def _statement_has_exit(self, stmt) -> bool:
        """Check if a statement/block ends with return, break, continue, or goto."""
        from AST.ast_nodes import Block, ReturnStatement, BreakStatement, ContinueStatement

        if isinstance(stmt, ReturnStatement):
            return True
        elif isinstance(stmt, (BreakStatement, ContinueStatement)):
            return True
        elif isinstance(stmt, Block) and stmt.statements:
            # Check the last statement in the block
            return self._statement_has_exit(stmt.statements[-1])
        else:
            return False

    def visit_WhileStatement(self, node: WhileStatement) -> None:
        start_label = self.new_label("while_start")
        end_label = self.new_label("while_end")

        self.emit(LabelInstruction(start_label))
        condition = self.visit(node.condition)
        self.emit(ConditionalGotoInstruction(condition, end_label, "0", "=="))

        self.label_manager.push_loop(end_label, start_label)
        self.visit(node.body)
        self.label_manager.pop_loop()

        self.emit(GotoInstruction(start_label))
        self.emit(LabelInstruction(end_label))

    def visit_DoWhileStatement(self, node: DoWhileStatement) -> None:
        start_label = self.new_label("do_start")
        cond_label = self.new_label("do_cond")
        end_label = self.new_label("do_end")

        self.emit(LabelInstruction(start_label))

        self.label_manager.push_loop(end_label, cond_label)
        self.visit(node.body)
        self.label_manager.pop_loop()

        self.emit(LabelInstruction(cond_label))
        condition = self.visit(node.condition)
        self.emit(ConditionalGotoInstruction(condition, start_label, "0", "!="))
        self.emit(LabelInstruction(end_label))

    def visit_ForStatement(self, node: ForStatement) -> None:
        if node.init:
            self.visit(node.init)

        condition_label = self.new_label("for_cond")
        update_label = self.new_label("for_update")
        end_label = self.new_label("for_end")

        self.emit(LabelInstruction(condition_label))
        if node.condition:
            condition = self.visit(node.condition)
            self.emit(ConditionalGotoInstruction(condition, end_label, "0", "=="))

        self.label_manager.push_loop(end_label, update_label)
        self.visit(node.body)
        self.label_manager.pop_loop()

        self.emit(LabelInstruction(update_label))
        if node.update:
            self.visit(node.update)
        self.emit(GotoInstruction(condition_label))
        self.emit(LabelInstruction(end_label))

    def visit_ForEachStatement(self, node: ForEachStatement) -> None:
        iterable = self.visit(node.iterable)
        index_temp = self.new_temp()
        length_temp = self.new_temp()

        self.emit(AssignInstruction(index_temp, "0"))
        self.emit(AssignInstruction(length_temp, iterable, "len"))

        loop_label = self.new_label("foreach_start")
        continue_label = self.new_label("foreach_continue")
        end_label = self.new_label("foreach_end")

        self.emit(LabelInstruction(loop_label))
        self.emit(ConditionalGotoInstruction(index_temp, end_label, length_temp, ">="))

        element_temp = self.new_temp()
        self.emit(ArrayAccessInstruction(element_temp, iterable, index_temp, is_assignment=False))
        self.emit(AssignInstruction(node.var_name, element_temp))

        self.label_manager.push_loop(end_label, continue_label)
        self.visit(node.body)
        self.label_manager.pop_loop()

        self.emit(LabelInstruction(continue_label))
        self.emit(AssignInstruction(index_temp, index_temp, "+", "1"))
        self.emit(GotoInstruction(loop_label))
        self.emit(LabelInstruction(end_label))

    def visit_SwitchStatement(self, node: SwitchStatement) -> None:
        switch_expr = self.visit(node.expression)
        end_label = self.new_label("switch_end")

        case_entries = []
        for switch_case in node.cases:
            label = self.new_label("case")
            case_entries.append((switch_case, label))

        default_label = self.new_label("switch_default") if node.default else end_label

        for switch_case, label in case_entries:
            case_value = self.visit(switch_case.expression)
            self.emit(ConditionalGotoInstruction(switch_expr, label, case_value, "=="))

        self.emit(GotoInstruction(default_label))

        self.label_manager.push_switch(end_label)

        for switch_case, label in case_entries:
            self.emit(LabelInstruction(label))
            for statement in switch_case.statements:
                self.visit(statement)

        if node.default:
            self.emit(LabelInstruction(default_label))
            for statement in node.default:
                self.visit(statement)

        self.label_manager.pop_switch()
        self.emit(LabelInstruction(end_label))

    def visit_BreakStatement(self, node: BreakStatement) -> None:  # type: ignore[override]
        try:
            label = self.label_manager.current_break_label()
        except RuntimeError as exc:
            raise TACGenerationError(str(exc), node)
        self.emit(GotoInstruction(label))

    def visit_ContinueStatement(self, node: ContinueStatement) -> None:  # type: ignore[override]
        try:
            label = self.label_manager.current_continue_label()
        except RuntimeError as exc:
            raise TACGenerationError(str(exc), node)
        self.emit(GotoInstruction(label))

    def visit_ReturnStatement(self, node: ReturnStatement) -> None:
        value = self.visit(node.value) if node.value is not None else None
        self.emit(ReturnInstruction(value))

    # ------------------------------------------------------------------
    # Generic handler fallbacks
    # ------------------------------------------------------------------
    def generic_visit(self, node: ASTNode) -> Optional[str]:
        return super().generic_visit(node)
