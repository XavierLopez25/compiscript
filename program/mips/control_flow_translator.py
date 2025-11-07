"""
Control flow translation from TAC to MIPS assembly.

This module handles the translation of control flow instructions including:
- Unconditional jumps (goto)
- Conditional branches (if-goto)
- Labels
- Branch optimization
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from tac.instruction import (
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
)

from .instruction import MIPSInstruction
from .label_manager import LabelManager

if TYPE_CHECKING:
    from .translator_base import MIPSTranslatorBase


class ControlFlowTranslator:
    """
    Translates TAC control flow instructions to MIPS assembly.

    This class handles:
    - Unconditional jumps: goto L → j L
    - Conditional branches:
      * if x goto L → bnez $rx, L
      * if x == y goto L → beq $rx, $ry, L
      * if x != y goto L → bne $rx, $ry, L
      * if x < y goto L → slt + bnez
      * etc.
    - Label emission: L: → L:
    - Label tracking and validation
    """

    def __init__(self, translator_base: MIPSTranslatorBase):
        """
        Initialize the control flow translator.

        Args:
            translator_base: Base translator providing register allocation
                           and instruction emission facilities
        """
        self.base = translator_base
        self.label_manager = LabelManager()

    def translate_goto(self, instruction: GotoInstruction) -> None:
        """
        Translate unconditional goto to MIPS jump.

        TAC: goto L
        MIPS: j L

        Args:
            instruction: TAC goto instruction
        """
        label = instruction.label
        self.label_manager.reference_label(label)
        self.base.emit_text(
            MIPSInstruction("j", (label,), comment=f"goto {label}")
        )

    def translate_conditional_goto(
        self, instruction: ConditionalGotoInstruction
    ) -> None:
        """
        Translate conditional goto to MIPS branch.

        Handles two forms:
        1. Simple condition: if x goto L
           → Load x into register
           → bnez $rx, L

        2. Relational condition: if x relop y goto L
           → Load x and y into registers
           → Branch based on operator

        Supported operators:
        - == : beq (branch if equal)
        - != : bne (branch if not equal)
        - <  : slt + bnez (set less than + branch if not zero)
        - <= : slt + beqz (check if y < x, branch if zero)
        - >  : slt + bnez (check if y < x, branch if not zero)
        - >= : slt + beqz (check if x < y, branch if zero)

        Args:
            instruction: TAC conditional goto instruction
        """
        label = instruction.label
        self.label_manager.reference_label(label)

        if instruction.operator and instruction.operand2:
            # Relational: if x relop y goto L
            self._translate_relational_branch(
                instruction.condition,
                instruction.operator,
                instruction.operand2,
                label,
            )
        else:
            # Simple: if x goto L (branch if x != 0)
            self._translate_simple_branch(instruction.condition, label)

    def translate_label(self, instruction: LabelInstruction) -> None:
        """
        Emit a label.

        TAC: L:
        MIPS: L:

        Args:
            instruction: TAC label instruction
        """
        label = instruction.label
        self.label_manager.define_label(label)
        self.base.emit_label(label)

    def _translate_simple_branch(self, condition: str, label: str) -> None:
        """
        Translate simple conditional: if x goto L

        Strategy: Branch if condition is non-zero
        MIPS: bnez $rx, L

        Args:
            condition: Variable to test
            label: Target label
        """
        # Load condition into register
        reg = self._load_operand(condition)

        # Branch if not zero
        self.base.emit_text(
            MIPSInstruction(
                "bnez", (reg, label), comment=f"if {condition} goto {label}"
            )
        )

    def _translate_relational_branch(
        self, left: str, operator: str, right: str, label: str
    ) -> None:
        """
        Translate relational conditional: if x relop y goto L

        Args:
            left: Left operand
            operator: Relational operator (==, !=, <, <=, >, >=)
            right: Right operand
            label: Target label
        """
        # Load operands into registers
        reg_left = self._load_operand(left)
        reg_right = self._load_operand(right, forbidden=[reg_left])

        comment = f"if {left} {operator} {right} goto {label}"

        if operator == "==":
            # Branch if equal
            self.base.emit_text(
                MIPSInstruction("beq", (reg_left, reg_right, label), comment=comment)
            )

        elif operator == "!=":
            # Branch if not equal
            self.base.emit_text(
                MIPSInstruction("bne", (reg_left, reg_right, label), comment=comment)
            )

        elif operator == "<":
            # Less than: slt $t, left, right; bnez $t, label
            temp_reg = self._get_temp_register(forbidden=[reg_left, reg_right])
            self.base.emit_text(
                MIPSInstruction(
                    "slt", (temp_reg, reg_left, reg_right), comment=f"{left} < {right}"
                )
            )
            self.base.emit_text(
                MIPSInstruction("bnez", (temp_reg, label), comment=comment)
            )

        elif operator == "<=":
            # Less or equal: slt $t, right, left; beqz $t, label
            # (if right < left is false, then left <= right)
            temp_reg = self._get_temp_register(forbidden=[reg_left, reg_right])
            self.base.emit_text(
                MIPSInstruction(
                    "slt", (temp_reg, reg_right, reg_left), comment=f"{right} < {left}"
                )
            )
            self.base.emit_text(
                MIPSInstruction("beqz", (temp_reg, label), comment=comment)
            )

        elif operator == ">":
            # Greater than: slt $t, right, left; bnez $t, label
            temp_reg = self._get_temp_register(forbidden=[reg_left, reg_right])
            self.base.emit_text(
                MIPSInstruction(
                    "slt", (temp_reg, reg_right, reg_left), comment=f"{right} < {left}"
                )
            )
            self.base.emit_text(
                MIPSInstruction("bnez", (temp_reg, label), comment=comment)
            )

        elif operator == ">=":
            # Greater or equal: slt $t, left, right; beqz $t, label
            # (if left < right is false, then left >= right)
            temp_reg = self._get_temp_register(forbidden=[reg_left, reg_right])
            self.base.emit_text(
                MIPSInstruction(
                    "slt", (temp_reg, reg_left, reg_right), comment=f"{left} < {right}"
                )
            )
            self.base.emit_text(
                MIPSInstruction("beqz", (temp_reg, label), comment=comment)
            )

        else:
            raise ValueError(f"Unsupported relational operator: {operator}")

    def _load_operand(self, operand: str, forbidden: list = None) -> str:
        """
        Load an operand into a register.

        If the operand is a constant, load it with 'li'.
        If it's a variable, acquire a register and load from memory if needed.

        Args:
            operand: The operand to load (variable name or constant)
            forbidden: List of registers that should not be used

        Returns:
            Register name containing the operand value
        """
        if forbidden is None:
            forbidden = []

        # Check if operand is a constant
        if self._is_constant(operand):
            # Get a temporary register and load the immediate value
            temp_reg = self._get_temp_register(forbidden=forbidden)
            self.base.emit_text(
                MIPSInstruction("li", (temp_reg, operand), comment=f"load {operand}")
            )
            return temp_reg

        # It's a variable - acquire a register for it
        reg, spills, loads = self.base.acquire_register(
            operand, is_write=False, forbidden_registers=forbidden
        )

        # Materialize spills and loads
        self.base.materialise_spills(spills)
        self.base.materialise_loads(loads)

        return reg

    def _get_temp_register(self, forbidden: list = None) -> str:
        """
        Get a temporary register for intermediate results.

        Args:
            forbidden: List of registers that should not be used

        Returns:
            A temporary register name
        """
        if forbidden is None:
            forbidden = []

        # Generate a unique temporary variable name
        temp_var = f"_ctrl_temp_{id(self)}"

        # Acquire a register for it
        reg, spills, _ = self.base.acquire_register(
            temp_var, is_write=True, forbidden_registers=forbidden
        )

        # Materialize any necessary spills
        self.base.materialise_spills(spills)

        return reg

    def _is_constant(self, operand: str) -> bool:
        """
        Check if an operand is a numeric constant.

        Args:
            operand: String operand from TAC

        Returns:
            True if operand is a number (integer or float)
        """
        if operand is None:
            return False
        try:
            int(operand)
            return True
        except ValueError:
            try:
                float(operand)
                return True
            except ValueError:
                return False

    def validate_labels(self) -> None:
        """
        Validate that all referenced labels are defined.

        Raises:
            LabelResolutionError: If there are undefined labels
        """
        self.label_manager.validate()

    def reset(self) -> None:
        """Reset the control flow translator state."""
        self.label_manager.reset()
