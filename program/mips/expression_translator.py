from __future__ import annotations
from typing import List, Optional
from tac.instruction import AssignInstruction

from .arithmetic import (
    translate_add,
    translate_div,
    translate_logical_and,
    translate_logical_or,
    translate_logical_xor,
    translate_mod,
    translate_mult,
    translate_negate,
    translate_sub,
)
from .comparison import (
    translate_boolean_and,
    translate_boolean_or,
    translate_equal,
    translate_greater_equal,
    translate_greater_than,
    translate_less_equal,
    translate_less_than,
    translate_logical_not,
    translate_not_equal,
)
from .instruction import MIPSInstruction
from .translator_base import MIPSTranslatorBase

def is_constant(operand: str) -> bool:
    """
    Check if an operand is a numeric constant.

    Args:
        operand: String operand from TAC

    Returns:
        True if operand is a number (integer or float)

    Examples:
        is_constant("42") to True
        is_constant("-5") to True
        is_constant("t1") to False
        is_constant("x") to False
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

class ExpressionTranslator:
    """
    Translates TAC expression instructions to MIPS assembly.

    This class handles:
    - Binary arithmetic operations (+, -, *, /, %)
    - Unary operations (-, !)
    - Comparison operations (<, >, <=, >=, ==, !=)
    - Logical operations (&&, ||, &, |, ^)
    - Simple assignments (x = y)
    - Constant loading (x = 5)

    The translator integrates with the register allocator to manage
    register usage and generate efficient MIPS code.
    """

    def __init__(self, translator_base: MIPSTranslatorBase):
        """
        Initialize the expression translator.

        Args:
            translator_base: Base translator providing register allocation
                            and instruction emission facilities
        """
        self.base = translator_base

    def translate_assignment(self, instruction: AssignInstruction) -> None:
        """
        Translate a TAC assignment instruction to MIPS.

        This is the main entry point that dispatches to specific handlers
        based on the type of assignment:
        - Binary operations (x = y + z)
        - Unary operations (x = -y, x = !y)
        - Simple assignments (x = y)
        - Constant assignments (x = 5)

        Args:
            instruction: TAC assignment instruction to translate

        Examples:
            # Binary: t1 = a + b
            AssignInstruction("t1", "a", "+", "b")

            # Unary: t2 = -a
            AssignInstruction("t2", "a", "-", None)

            # Simple: t3 = x
            AssignInstruction("t3", "x", None, None)

            # Constant: t4 = 42
            AssignInstruction("t4", "42", None, None)
        """
        target = instruction.target
        operand1 = instruction.operand1
        operator = instruction.operator
        operand2 = instruction.operand2

        # Dispatch based on instruction pattern
        if operator and operand2:
            # Binary operation: target = operand1 op operand2
            self._translate_binary_operation(target, operand1, operator, operand2)
        elif operator:
            # Unary operation: target = op operand1
            self._translate_unary_operation(target, operator, operand1)
        else:
            # Simple assignment: target = operand1
            self._translate_simple_assignment(target, operand1)

    # Binary operations
    def _translate_binary_operation(
        self,
        target: str,
        operand1: str,
        operator: str,
        operand2: str,
    ) -> None:
        """
        Translate binary operation: target = operand1 op operand2

        Steps:
        1. Acquire register for destination (target)
        2. Load operand1 into a register
        3. Load operand2 into a register (or use immediate)
        4. Generate operation instruction(s)
        5. Update descriptors

        Args:
            target: Destination variable
            operand1: Left operand
            operator: Operation (+, -, *, /, %, <, >, etc.)
            operand2: Right operand
        """
        # Acquire destination register
        dest_reg, spills, loads = self.base.acquire_register(target, is_write=True)
        self.base.materialise_spills(spills)
        self.base.materialise_loads(loads)

        # Load operand1 into register
        src1_reg = self._load_operand(operand1, forbidden=[dest_reg])

        # Handle operand2 (might be immediate)
        is_immediate = is_constant(operand2)

        if is_immediate:
            # Use immediate value directly
            src2_operand = operand2
            instructions = self._generate_binary_instructions(
                operator, dest_reg, src1_reg, src2_operand, is_immediate=True
            )
        else:
            # Load operand2 into register
            src2_reg = self._load_operand(operand2, forbidden=[dest_reg, src1_reg])
            instructions = self._generate_binary_instructions(
                operator, dest_reg, src1_reg, src2_reg, is_immediate=False
            )

        # Emit generated instructions
        self.base.emit_text_many(instructions)

    def _generate_binary_instructions(
        self,
        operator: str,
        dest_reg: str,
        src1_reg: str,
        src2_operand: str,
        is_immediate: bool = False,
    ) -> List[MIPSInstruction]:
        """
        Generate MIPS instructions for binary operations.

        Args:
            operator: Operation symbol (+, -, *, etc.)
            dest_reg: Destination register
            src1_reg: First source register
            src2_operand: Second operand (register or immediate)
            is_immediate: True if src2_operand is a constant

        Returns:
            List of MIPS instructions
        """
        # Arithmetic operations
        if operator == "+":
            return translate_add(dest_reg, src1_reg, src2_operand, is_immediate=is_immediate)
        elif operator == "-":
            return translate_sub(dest_reg, src1_reg, src2_operand)
        elif operator == "*":
            return translate_mult(dest_reg, src1_reg, src2_operand)
        elif operator == "/":
            return translate_div(dest_reg, src1_reg, src2_operand)
        elif operator == "%":
            return translate_mod(dest_reg, src1_reg, src2_operand)

        # Comparison operations
        elif operator == "<":
            return translate_less_than(dest_reg, src1_reg, src2_operand, is_immediate=is_immediate)
        elif operator == ">":
            return translate_greater_than(dest_reg, src1_reg, src2_operand)
        elif operator == "<=":
            return translate_less_equal(dest_reg, src1_reg, src2_operand)
        elif operator == ">=":
            return translate_greater_equal(dest_reg, src1_reg, src2_operand)
        elif operator == "==":
            return translate_equal(dest_reg, src1_reg, src2_operand)
        elif operator == "!=":
            return translate_not_equal(dest_reg, src1_reg, src2_operand)

        # Logical operations
        elif operator == "&&":
            # Requires temp register for boolean conversion
            temp_reg, spills, loads = self.base.acquire_register(
                f"_temp_{dest_reg}",
                is_write=True,
                forbidden_registers=[dest_reg, src1_reg, src2_operand]
            )
            self.base.materialise_spills(spills)
            self.base.materialise_loads(loads)
            instructions = translate_boolean_and(dest_reg, src1_reg, src2_operand, temp_reg)
            self.base.release_register(temp_reg)
            return instructions
        elif operator == "||":
            return translate_boolean_or(dest_reg, src1_reg, src2_operand)

        # Bitwise operations
        elif operator == "&":
            return translate_logical_and(dest_reg, src1_reg, src2_operand)
        elif operator == "|":
            return translate_logical_or(dest_reg, src1_reg, src2_operand)
        elif operator == "^":
            return translate_logical_xor(dest_reg, src1_reg, src2_operand)

        else:
            raise ValueError(f"Unsupported binary operator: {operator}")

    # Unary operations
    def _translate_unary_operation(
        self,
        target: str,
        operator: str,
        operand: str,
    ) -> None:
        """
        Translate unary operation: target = op operand

        Args:
            target: Destination variable
            operator: Operation (-, !)
            operand: Source operand
        """
        # Acquire destination register
        dest_reg, spills, loads = self.base.acquire_register(target, is_write=True)
        self.base.materialise_spills(spills)
        self.base.materialise_loads(loads)

        # Load operand into register
        src_reg = self._load_operand(operand, forbidden=[dest_reg])

        # Generate instruction based on operator
        if operator == "-":
            instructions = translate_negate(dest_reg, src_reg)
        elif operator == "!":
            instructions = translate_logical_not(dest_reg, src_reg)
        else:
            raise ValueError(f"Unsupported unary operator: {operator}")

        self.base.emit_text_many(instructions)

    # Simple assignments
    def _translate_simple_assignment(self, target: str, source: str) -> None:
        """
        Translate simple assignment: target = source

        Cases:
        1. Constant: target = 42  to  li $dest, 42
        2. Variable: target = x   to  move $dest, $src

        Args:
            target: Destination variable
            source: Source operand (variable or constant)
        """
        # Acquire destination register
        dest_reg, spills, loads = self.base.acquire_register(target, is_write=True)
        self.base.materialise_spills(spills)
        self.base.materialise_loads(loads)

        if is_constant(source):
            # Load immediate value
            self.base.emit_text(
                MIPSInstruction(
                    "li",
                    (dest_reg, source),
                    comment=f"{target} = {source}",
                )
            )
        else:
            # Load from variable
            src_reg = self._load_operand(source, forbidden=[dest_reg])
            self.base.emit_text(
                MIPSInstruction(
                    "move",
                    (dest_reg, src_reg),
                    comment=f"{target} = {source}",
                )
            )

    # Helper methods
    def _load_operand(
        self,
        operand: str,
        forbidden: Optional[List[str]] = None,
    ) -> str:
        """
        Load an operand into a register.

        If the operand is a constant, load it with 'li'.
        If it's a variable, acquire a register for it.

        Args:
            operand: Variable name or constant
            forbidden: Registers that cannot be used

        Returns:
            Register name containing the operand value
        """
        if is_constant(operand):
            temp_var = f"_const_{operand}"
            temp_reg, spills, loads = self.base.acquire_register(
                temp_var,
                is_write=True,
                forbidden_registers=forbidden,
            )
            self.base.materialise_spills(spills)

            self.base.emit_text(
                MIPSInstruction(
                    "li",
                    (temp_reg, operand),
                    comment=f"load constant {operand}",
                )
            )
            return temp_reg
        else:
            # Acquire register for variable
            reg, spills, loads = self.base.acquire_register(
                operand,
                is_write=False,
                forbidden_registers=forbidden,
            )
            self.base.materialise_spills(spills)
            self.base.materialise_loads(loads)
            return reg