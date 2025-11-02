from __future__ import annotations
from typing import List
from .instruction import MIPSInstruction

def translate_add(
    dest_reg: str,
    src1_reg: str,
    src2_operand: str,
    *,
    is_immediate: bool = False,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for addition: dest = src1 + src2

    Args:
        dest_reg: Destination register (e.g., "$t0")
        src1_reg: First source register (e.g., "$t1")
        src2_operand: Second operand (register like "$t2" or immediate value like "5")
        is_immediate: True if src2_operand is an immediate value

    Returns:
        List of MIPS instructions

    Examples:
        # Register + Register: t0 = t1 + t2
        translate_add("$t0", "$t1", "$t2")
        # [add $t0, $t1, $t2]

        # Register + Immediate: t0 = t1 + 5
        translate_add("$t0", "$t1", "5", is_immediate=True)
        # [addi $t0, $t1, 5]
    """
    if is_immediate:
        # Use addi for immediate values
        return [
            MIPSInstruction(
                "addi",
                (dest_reg, src1_reg, src2_operand),
                comment=f"{dest_reg} = {src1_reg} + {src2_operand}",
            )
        ]
    else:
        # Use add for register-to-register addition
        return [
            MIPSInstruction(
                "add",
                (dest_reg, src1_reg, src2_operand),
                comment=f"{dest_reg} = {src1_reg} + {src2_operand}",
            )
        ]

def translate_sub(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for subtraction: dest = src1 - src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register (minuend)
        src2_reg: Second source register (subtrahend)

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 - t2
        translate_sub("$t0", "$t1", "$t2")
        # [sub $t0, $t1, $t2]

    Note:
        MIPS doesn't have a "subi" instruction for immediate subtraction.
        To subtract an immediate, use addi with a negative value:
        t0 = t1 - 5  to addi $t0, $t1, -5
    """
    return [
        MIPSInstruction(
            "sub",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} - {src2_reg}",
        )
    ]

def translate_mult(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for multiplication: dest = src1 * src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 * t2
        translate_mult("$t0", "$t1", "$t2")
        # [mult $t1, $t2, mflo $t0]
    """
    return [
        MIPSInstruction(
            "mul",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} * {src2_reg}",
        )
    ]

def translate_div(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for division: dest = src1 / src2

    Args:
        dest_reg: Destination register (receives quotient)
        src1_reg: First source register (dividend)
        src2_reg: Second source register (divisor)

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 / t2
        translate_div("$t0", "$t1", "$t2")
        # [div $t1, $t2, mflo $t0]

    Note:
        MIPS division stores:
        - Quotient in LO register
        - Remainder in HI register

        We use mflo to get the quotient.
        For remainder (modulo), use mfhi.
    """
    return [
        MIPSInstruction(
            "div",
            (src1_reg, src2_reg),
            comment=f"divide {src1_reg} / {src2_reg}",
        ),
        MIPSInstruction(
            "mflo",
            (dest_reg,),
            comment=f"{dest_reg} = quotient",
        ),
    ]

def translate_mod(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for modulo: dest = src1 % src2

    Args:
        dest_reg: Destination register (receives remainder)
        src1_reg: First source register (dividend)
        src2_reg: Second source register (divisor)

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 % t2
        translate_mod("$t0", "$t1", "$t2")
        # [div $t1, $t2, mfhi $t0]

    Note:
        The modulo operation uses the same div instruction as division,
        but retrieves the remainder from HI register using mfhi.
    """
    return [
        MIPSInstruction(
            "div",
            (src1_reg, src2_reg),
            comment=f"divide {src1_reg} / {src2_reg}",
        ),
        MIPSInstruction(
            "mfhi",
            (dest_reg,),
            comment=f"{dest_reg} = remainder",
        ),
    ]

def translate_negate(
    dest_reg: str,
    src_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for negation: dest = -src

    Args:
        dest_reg: Destination register
        src_reg: Source register to negate

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = -t1
        translate_negate("$t0", "$t1")
        # [sub $t0, $zero, $t1]

    Note:
        MIPS doesn't have a dedicated negate instruction.
        We implement it as: dest = 0 - src
        Using $zero register (always contains 0) for the subtraction.
    """
    return [
        MIPSInstruction(
            "sub",
            (dest_reg, "$zero", src_reg),
            comment=f"{dest_reg} = -{src_reg}",
        )
    ]

def translate_logical_and(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for bitwise AND: dest = src1 & src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 & t2
        translate_logical_and("$t0", "$t1", "$t2")
        # [and $t0, $t1, $t2]

    Note:
        This performs bitwise AND. For logical AND (&&), use comparison
        instructions from comparison.py
    """
    return [
        MIPSInstruction(
            "and",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} & {src2_reg}",
        )
    ]

def translate_logical_or(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for bitwise OR: dest = src1 | src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 | t2
        translate_logical_or("$t0", "$t1", "$t2")
        # [or $t0, $t1, $t2]

    Note:
        This performs bitwise OR. For logical OR (||), use comparison
        instructions from comparison.py
    """
    return [
        MIPSInstruction(
            "or",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} | {src2_reg}",
        )
    ]

def translate_logical_xor(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for bitwise XOR: dest = src1 ^ src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 ^ t2
        translate_logical_xor("$t0", "$t1", "$t2")
        # [xor $t0, $t1, $t2]
    """
    return [
        MIPSInstruction(
            "xor",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} ^ {src2_reg}",
        )
    ]