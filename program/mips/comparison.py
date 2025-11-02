from __future__ import annotations
from typing import List
from .instruction import MIPSInstruction

def translate_less_than(
    dest_reg: str,
    src1_reg: str,
    src2_operand: str,
    *,
    is_immediate: bool = False,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for less than: dest = (src1 < src2) ? 1 : 0

    Args:
        dest_reg: Destination register (receives 1 if true, 0 if false)
        src1_reg: First source register
        src2_operand: Second operand (register or immediate)
        is_immediate: True if src2_operand is an immediate value

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 < t2) ? 1 : 0
        translate_less_than("$t0", "$t1", "$t2")
        # [slt $t0, $t1, $t2]

        # t0 = (t1 < 10) ? 1 : 0
        translate_less_than("$t0", "$t1", "10", is_immediate=True)
        # [slti $t0, $t1, 10]

    Note:
        slt = "set less than"
        Result is 1 if src1 < src2, otherwise 0
    """
    if is_immediate:
        return [
            MIPSInstruction(
                "slti",
                (dest_reg, src1_reg, src2_operand),
                comment=f"{dest_reg} = ({src1_reg} < {src2_operand})",
            )
        ]
    else:
        return [
            MIPSInstruction(
                "slt",
                (dest_reg, src1_reg, src2_operand),
                comment=f"{dest_reg} = ({src1_reg} < {src2_operand})",
            )
        ]

def translate_less_equal(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for less or equal: dest = (src1 <= src2) ? 1 : 0

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 <= t2) ? 1 : 0
        translate_less_equal("$t0", "$t1", "$t2")
        # [slt $t0, $t2, $t1,  # $t0 = (t2 < t1)
        #    xori $t0, $t0, 1]    # $t0 = !$t0 = (t1 <= t2)

    Note:
        MIPS doesn't have a direct "sle" (set less or equal) instruction.
        We implement it as: dest = !(src2 < src1)
        Logic: src1 <= src2  ≡  !(src2 < src1)  ≡  !(src1 > src2)
    """
    return [
        MIPSInstruction(
            "slt",
            (dest_reg, src2_reg, src1_reg),
            comment=f"{dest_reg} = ({src2_reg} < {src1_reg})",
        ),
        MIPSInstruction(
            "xori",
            (dest_reg, dest_reg, "1"),
            comment=f"{dest_reg} = !{dest_reg} = ({src1_reg} <= {src2_reg})",
        ),
    ]

def translate_greater_than(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for greater than: dest = (src1 > src2) ? 1 : 0

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 > t2) ? 1 : 0
        translate_greater_than("$t0", "$t1", "$t2")
        # [slt $t0, $t2, $t1]  # swap operands

    Note:
        MIPS doesn't have sgt instruction.
        We implement it by swapping operands: src1 > src2  ≡  src2 < src1
    """
    return [
        MIPSInstruction(
            "slt",
            (dest_reg, src2_reg, src1_reg),
            comment=f"{dest_reg} = ({src1_reg} > {src2_reg})",
        )
    ]

def translate_greater_equal(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for greater or equal: dest = (src1 >= src2) ? 1 : 0

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 >= t2) ? 1 : 0
        translate_greater_equal("$t0", "$t1", "$t2")
        # [slt $t0, $t1, $t2,   # $t0 = (t1 < t2)
        #    xori $t0, $t0, 1]    # $t0 = !$t0 = (t1 >= t2)

    Note:
        We implement it as: dest = !(src1 < src2)
        Logic: src1 >= src2  ≡  !(src1 < src2)
    """
    return [
        MIPSInstruction(
            "slt",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = ({src1_reg} < {src2_reg})",
        ),
        MIPSInstruction(
            "xori",
            (dest_reg, dest_reg, "1"),
            comment=f"{dest_reg} = !{dest_reg} = ({src1_reg} >= {src2_reg})",
        ),
    ]

def translate_equal(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for equality: dest = (src1 == src2) ? 1 : 0

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 == t2) ? 1 : 0
        translate_equal("$t0", "$t1", "$t2")
        # [sub $t0, $t1, $t2,         # $t0 = t1 - t2
        #    sltiu $t0, $t0, 1]         # $t0 = ($t0 < 1) = ($t0 == 0)

    Note:
        MIPS doesn't have a direct "seq" instruction in base ISA.
        We implement it as: dest = (src1 - src2 == 0)
        - Subtract the values
        - Use sltiu (set less than immediate unsigned) with 1
        - This produces 1 only if difference is 0
    """
    return [
        MIPSInstruction(
            "sub",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} - {src2_reg}",
        ),
        MIPSInstruction(
            "sltiu",
            (dest_reg, dest_reg, "1"),
            comment=f"{dest_reg} = ({dest_reg} == 0)",
        ),
    ]

def translate_not_equal(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for inequality: dest = (src1 != src2) ? 1 : 0

    Args:
        dest_reg: Destination register
        src1_reg: First source register
        src2_reg: Second source register

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = (t1 != t2) ? 1 : 0
        translate_not_equal("$t0", "$t1", "$t2")
        # [sub $t0, $t1, $t2,      # $t0 = t1 - t2
        #    sltu $t0, $zero, $t0]   # $t0 = (0 < $t0) = ($t0 != 0)

    Note:
        We implement it as: dest = (src1 - src2 != 0)
        - Subtract the values
        - Use sltu with $zero as first operand
        - This produces 1 if difference is non-zero
    """
    return [
        MIPSInstruction(
            "sub",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} - {src2_reg}",
        ),
        MIPSInstruction(
            "sltu",
            (dest_reg, "$zero", dest_reg),
            comment=f"{dest_reg} = ({dest_reg} != 0)",
        ),
    ]

def translate_logical_not(
    dest_reg: str,
    src_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for logical NOT: dest = !src

    Args:
        dest_reg: Destination register
        src_reg: Source register to negate

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = !t1
        translate_logical_not("$t0", "$t1")
        # [sltiu $t0, $t1, 1]  # $t0 = (t1 < 1) = (t1 == 0)

    Note:
        Logical NOT converts:
        - 0 to 1
        - non-zero to 0

        We use sltiu with 1: result is 1 only if src < 1 (i.e., src == 0)
    """
    return [
        MIPSInstruction(
            "sltiu",
            (dest_reg, src_reg, "1"),
            comment=f"{dest_reg} = !{src_reg}",
        )
    ]

def translate_boolean_and(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
    temp_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for logical AND: dest = src1 && src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register (boolean)
        src2_reg: Second source register (boolean)
        temp_reg: Temporary register for intermediate calculation

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 && t2
        translate_boolean_and("$t0", "$t1", "$t2", "$t3")
        # [sltu $t3, $zero, $t1,   # $t3 = (t1 != 0)
        #    sltu $t0, $zero, $t2,   # $t0 = (t2 != 0)
        #    and $t0, $t3, $t0]      # $t0 = $t3 & $t0

    Note:
        Logical AND (&&) is different from bitwise AND (&).
        Steps:
        1. Convert src1 to boolean (0 or 1)
        2. Convert src2 to boolean (0 or 1)
        3. Bitwise AND the results
    """
    return [
        MIPSInstruction(
            "sltu",
            (temp_reg, "$zero", src1_reg),
            comment=f"{temp_reg} = ({src1_reg} != 0)",
        ),
        MIPSInstruction(
            "sltu",
            (dest_reg, "$zero", src2_reg),
            comment=f"{dest_reg} = ({src2_reg} != 0)",
        ),
        MIPSInstruction(
            "and",
            (dest_reg, temp_reg, dest_reg),
            comment=f"{dest_reg} = {src1_reg} && {src2_reg}",
        ),
    ]

def translate_boolean_or(
    dest_reg: str,
    src1_reg: str,
    src2_reg: str,
) -> List[MIPSInstruction]:
    """
    Generate MIPS instructions for logical OR: dest = src1 || src2

    Args:
        dest_reg: Destination register
        src1_reg: First source register (boolean)
        src2_reg: Second source register (boolean)

    Returns:
        List of MIPS instructions

    Examples:
        # t0 = t1 || t2
        translate_boolean_or("$t0", "$t1", "$t2")
        # [or $t0, $t1, $t2,       # $t0 = t1 | t2
        #    sltu $t0, $zero, $t0]   # $t0 = ($t0 != 0)

    Note:
        Logical OR (||) is different from bitwise OR (|).
        Steps:
        1. Bitwise OR the operands
        2. Convert result to boolean (0 or 1)
    """
    return [
        MIPSInstruction(
            "or",
            (dest_reg, src1_reg, src2_reg),
            comment=f"{dest_reg} = {src1_reg} | {src2_reg}",
        ),
        MIPSInstruction(
            "sltu",
            (dest_reg, "$zero", dest_reg),
            comment=f"{dest_reg} = ({dest_reg} != 0)",
        ),
    ]