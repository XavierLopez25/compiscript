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
        # Get scoped name for the variable (handles shadowing)
        scoped_name = self.get_scoped_name(node.name, is_declaration=True)

        if node.initializer is not None:
            # Generate code for the initializer expression
            value = self.visit(node.initializer)
            # Assign the result to the scoped variable name
            self.emit(AssignInstruction(scoped_name, value))
            return scoped_name
        else:
            # Variable declaration without initializer
            self.emit(CommentInstruction(f"Variable declaration: {scoped_name}"))
            return scoped_name

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

    def visit_TryCatchStatement(self, node) -> None:
        """
        Generate TAC for try-catch statement with explicit safety checks.
        Detects risky operations (array access) and adds bounds checking.
        """
        catch_label = self.new_label("catch")
        end_label = self.new_label("try_end")

        self.emit(CommentInstruction("Try block with safety checks"))

        # Process try block statements with safety checks
        self._generate_try_block_with_checks(node.try_block, catch_label)

        # Jump over catch block if no error
        self.emit(GotoInstruction(end_label))

        # Catch block
        self.emit(LabelInstruction(catch_label))
        self.emit(CommentInstruction(f"Catch block (exception var: {node.exc_name})"))

        # Assign error message to exception variable
        error_temp = self.new_temp()
        self.emit(AssignInstruction(error_temp, '"Runtime error occurred"'))

        # Get scoped name for exception variable
        scoped_exc_name = self.get_scoped_name(node.exc_name, is_declaration=True)
        self.emit(AssignInstruction(scoped_exc_name, error_temp))

        # Generate TAC for catch block
        self.visit(node.catch_block)

        self.emit(LabelInstruction(end_label))
        self.emit(CommentInstruction("Try-catch end"))

    def _generate_try_block_with_checks(self, block, catch_label: str) -> None:
        """Generate try block with safety checks for risky operations."""
        from AST.ast_nodes import VariableDeclaration, IndexExpression

        for stmt in block.statements:
            # Check if statement contains array access
            if isinstance(stmt, VariableDeclaration) and stmt.initializer:
                if self._contains_array_access(stmt.initializer):
                    # Generate bounds checking before the access
                    self._generate_array_bounds_check(stmt.initializer, catch_label)

            # Generate normal code for the statement
            self.visit(stmt)

    def _contains_array_access(self, node) -> bool:
        """Check if an expression tree contains array access."""
        from AST.ast_nodes import IndexExpression, BinaryOperation, CallExpression

        if isinstance(node, IndexExpression):
            return True
        elif isinstance(node, BinaryOperation):
            return (self._contains_array_access(node.left) or
                   self._contains_array_access(node.right))
        elif isinstance(node, CallExpression):
            return any(self._contains_array_access(arg) for arg in node.arguments)

        return False

    def _generate_array_bounds_check(self, node, catch_label: str) -> None:
        """Generate bounds checking code for array access."""
        from AST.ast_nodes import IndexExpression

        if isinstance(node, IndexExpression):
            # Evaluate array and index
            array_temp = self.visit(node.array)
            index_temp = self.visit(node.index)

            # Get array length
            length_temp = self.new_temp()
            self.emit(AssignInstruction(length_temp, array_temp, "len"))

            # Check if index < length
            check_temp = self.new_temp()
            self.emit(AssignInstruction(check_temp, index_temp, "<", length_temp))

            # If check fails (index >= length), jump to catch
            self.emit(ConditionalGotoInstruction(check_temp, catch_label, "0", "=="))

            # Also check if index >= 0
            zero_check_temp = self.new_temp()
            self.emit(AssignInstruction(zero_check_temp, index_temp, ">=", "0"))
            self.emit(ConditionalGotoInstruction(zero_check_temp, catch_label, "0", "=="))

    # ------------------------------------------------------------------
    # Generic handler fallbacks
    # ------------------------------------------------------------------
    def generic_visit(self, node: ASTNode) -> Optional[str]:
        """
        Handle nodes that don't have specific visitors in control flow generator.
        Delegates to function generator for PrintStatement and other function-related nodes.
        """
        node_type = node.__class__.__name__

        # Delegate FunctionDeclaration to function generator (for nested functions)
        if node_type == 'FunctionDeclaration' and hasattr(self, '_function_generator') and self._function_generator:
            # Sync instructions
            self._function_generator.instructions = self.get_instructions()
            result = self._function_generator.visit_FunctionDeclaration(node)
            # Sync back
            self.instructions = self._function_generator.get_instructions()
            return result

        # Delegate PrintStatement to function generator
        elif node_type == 'PrintStatement' and hasattr(self, '_function_generator') and self._function_generator:
            # Sync instructions
            self._function_generator.instructions = self.get_instructions()
            result = self._function_generator.visit_PrintStatement(node)
            # Sync back
            self.instructions = self._function_generator.get_instructions()
            return result

        # Delegate CallExpression to function generator (for standalone calls)
        elif node_type == 'CallExpression' and hasattr(self, '_function_generator') and self._function_generator:
            # Sync instructions
            self._function_generator.instructions = self.get_instructions()
            result = self._function_generator.visit_CallExpression(node)
            # Sync back
            self.instructions = self._function_generator.get_instructions()
            return result

        return super().generic_visit(node)
