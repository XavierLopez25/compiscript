"""
MIPS Calling Convention Implementation

This module implements the MIPS calling convention (MIPS ABI) for parameter passing,
return values, and register preservation.

MIPS Register Usage Convention:
┌──────────────┬─────────────────┬────────────────────────────────────┐
│ Register     │ Name            │ Usage                              │
├──────────────┼─────────────────┼────────────────────────────────────┤
│ $0           │ $zero           │ Always 0                           │
│ $1           │ $at             │ Assembler temporary (avoid)        │
│ $2-$3        │ $v0-$v1         │ Function return values (CALLER)    │
│ $4-$7        │ $a0-$a3         │ Function arguments (CALLER)        │
│ $8-$15       │ $t0-$t7         │ Temporaries (CALLER-saved)         │
│ $16-$23      │ $s0-$s7         │ Saved temps (CALLEE-saved)         │
│ $24-$25      │ $t8-$t9         │ More temporaries (CALLER-saved)    │
│ $26-$27      │ $k0-$k1         │ Kernel/OS (avoid)                  │
│ $28          │ $gp             │ Global pointer                     │
│ $29          │ $sp             │ Stack pointer (CALLEE-saved)       │
│ $30          │ $fp             │ Frame pointer (CALLEE-saved)       │
│ $31          │ $ra             │ Return address (CALLEE-saved)      │
└──────────────┴─────────────────┴────────────────────────────────────┘

Calling Convention Rules:
1. First 4 parameters → $a0-$a3
2. Additional parameters → Stack (pushed right-to-left)
3. Return value → $v0 (or $v0-$v1 for 64-bit)
4. Caller saves: $t0-$t9, $a0-$a3, $v0-$v1 (if needed)
5. Callee saves: $s0-$s7, $fp, $ra (if used)
6. Stack grows downward (toward lower addresses)
7. Stack must be aligned to 8-byte boundary
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .instruction import MIPSInstruction


# Register sets
ARGUMENT_REGISTERS = ["$a0", "$a1", "$a2", "$a3"]
RETURN_REGISTERS = ["$v0", "$v1"]
TEMPORARY_REGISTERS = ["$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7", "$t8", "$t9"]
SAVED_REGISTERS = ["$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7"]
SPECIAL_REGISTERS = {
    "zero": "$zero",
    "at": "$at",
    "sp": "$sp",
    "fp": "$fp",
    "ra": "$ra",
    "gp": "$gp",
}


@dataclass
class ParameterLocation:
    """Describes where a parameter is located."""
    index: int  # Parameter index (0-based)
    in_register: bool  # True if in $a0-$a3, False if on stack
    register: Optional[str]  # Register name if in_register
    stack_offset: Optional[int]  # Offset from $sp if on stack


@dataclass
class CallingContext:
    """Context for a function call, tracking parameter and return handling."""
    function_name: str
    param_count: int
    has_return_value: bool
    param_locations: List[ParameterLocation]
    stack_space_needed: int  # Bytes needed for stack parameters


class CallingConvention:
    """
    Implements MIPS calling convention for parameter passing and returns.

    This class helps generate correct MIPS code for:
    - Parameter passing (registers + stack)
    - Return value handling
    - Register preservation
    """

    @staticmethod
    def get_param_location(param_index: int, total_params: int) -> ParameterLocation:
        """
        Determine where a parameter should be placed.

        Args:
            param_index: 0-based index of the parameter
            total_params: Total number of parameters

        Returns:
            ParameterLocation describing where the parameter goes
        """
        if param_index < 4:
            # First 4 params go in $a0-$a3
            return ParameterLocation(
                index=param_index,
                in_register=True,
                register=ARGUMENT_REGISTERS[param_index],
                stack_offset=None,
            )
        else:
            # Params 5+ go on stack
            # Stack offset is calculated as: (param_index - 4) * 4
            # These are pushed in order, so param 5 is at 0($sp), param 6 at 4($sp), etc.
            stack_offset = (param_index - 4) * 4
            return ParameterLocation(
                index=param_index,
                in_register=False,
                register=None,
                stack_offset=stack_offset,
            )

    @staticmethod
    def create_calling_context(
        function_name: str, param_count: int, has_return_value: bool = True
    ) -> CallingContext:
        """
        Create a calling context for a function call.

        Args:
            function_name: Name of the function being called
            param_count: Number of parameters
            has_return_value: Whether the function returns a value

        Returns:
            CallingContext with parameter locations computed
        """
        param_locations = [
            CallingConvention.get_param_location(i, param_count)
            for i in range(param_count)
        ]

        # Calculate stack space needed for params beyond first 4
        stack_params = max(0, param_count - 4)
        stack_space_needed = stack_params * 4

        return CallingContext(
            function_name=function_name,
            param_count=param_count,
            has_return_value=has_return_value,
            param_locations=param_locations,
            stack_space_needed=stack_space_needed,
        )

    @staticmethod
    def generate_push_param(
        param_value: str, param_location: ParameterLocation, temp_reg: str = "$t0"
    ) -> List[MIPSInstruction]:
        """
        Generate instructions to push a parameter.

        Args:
            param_value: The value to push (variable name, constant, or register)
            param_location: Where the parameter should go
            temp_reg: Temporary register to use for loading

        Returns:
            List of MIPS instructions
        """
        instructions = []

        if param_location.in_register:
            # Load value into argument register
            target_reg = param_location.register

            # Check if param_value is already a register
            if param_value.startswith("$"):
                instructions.append(
                    MIPSInstruction(
                        "move",
                        (target_reg, param_value),
                        comment=f"param {param_location.index}",
                    )
                )
            elif param_value.isdigit() or (param_value.startswith("-") and param_value[1:].isdigit()):
                # It's a constant
                instructions.append(
                    MIPSInstruction(
                        "li", (target_reg, param_value), comment=f"param {param_location.index}"
                    )
                )
            else:
                # It's a variable - need to load from memory
                instructions.append(
                    MIPSInstruction(
                        "lw", (target_reg, param_value), comment=f"load param {param_location.index}"
                    )
                )
        else:
            # Push to stack
            # First, load value into temp register
            if param_value.startswith("$"):
                # Already in register
                reg_to_push = param_value
            elif param_value.isdigit() or (param_value.startswith("-") and param_value[1:].isdigit()):
                # Constant
                instructions.append(MIPSInstruction("li", (temp_reg, param_value)))
                reg_to_push = temp_reg
            else:
                # Variable
                instructions.append(MIPSInstruction("lw", (temp_reg, param_value)))
                reg_to_push = temp_reg

            # Allocate space on stack and store
            instructions.append(
                MIPSInstruction("addi", ("$sp", "$sp", "-4"), comment="allocate stack param")
            )
            instructions.append(
                MIPSInstruction(
                    "sw",
                    (reg_to_push, "0($sp)"),
                    comment=f"push param {param_location.index}",
                )
            )

        return instructions

    @staticmethod
    def generate_pop_params(param_count: int) -> List[MIPSInstruction]:
        """
        Generate instructions to pop parameters from stack after a call.

        Args:
            param_count: Total number of parameters

        Returns:
            List of MIPS instructions to clean up stack
        """
        # Only stack parameters (beyond first 4) need to be popped
        stack_params = max(0, param_count - 4)

        if stack_params == 0:
            return []

        bytes_to_pop = stack_params * 4
        return [
            MIPSInstruction(
                "addi",
                ("$sp", "$sp", str(bytes_to_pop)),
                comment=f"pop {stack_params} params",
            )
        ]

    @staticmethod
    def generate_function_call(function_label: str) -> List[MIPSInstruction]:
        """
        Generate instruction to call a function.

        Args:
            function_label: Label of the function to call

        Returns:
            List containing jal instruction
        """
        return [MIPSInstruction("jal", (function_label,), comment=f"call {function_label}")]

    @staticmethod
    def generate_return_value_retrieval(
        target: str, temp_reg: str = "$t0"
    ) -> List[MIPSInstruction]:
        """
        Generate instructions to retrieve return value from $v0.

        Args:
            target: Where to store the return value (variable or register)
            temp_reg: Temporary register (not used here, but for consistency)

        Returns:
            List of MIPS instructions
        """
        if target.startswith("$"):
            # Target is a register
            if target == "$v0":
                # Already in place
                return []
            return [MIPSInstruction("move", (target, "$v0"), comment="get return value")]
        else:
            # Target is a variable - store to memory
            return [MIPSInstruction("sw", ("$v0", target), comment="store return value")]

    @staticmethod
    def generate_return_statement(
        return_value: Optional[str] = None, temp_reg: str = "$t0"
    ) -> List[MIPSInstruction]:
        """
        Generate instructions to return from a function.

        Note: This only loads the return value into $v0.
        The function epilogue (restoring registers, etc.) is handled separately.

        Args:
            return_value: Value to return (variable, constant, or register)
            temp_reg: Temporary register for intermediate operations

        Returns:
            List of MIPS instructions
        """
        if return_value is None:
            # Void return - no value to load
            return []

        instructions = []

        if return_value.startswith("$"):
            # Already in a register
            if return_value != "$v0":
                instructions.append(
                    MIPSInstruction("move", ("$v0", return_value), comment="set return value")
                )
        elif return_value.isdigit() or (
            return_value.startswith("-") and return_value[1:].isdigit()
        ):
            # Constant
            instructions.append(
                MIPSInstruction("li", ("$v0", return_value), comment="set return value")
            )
        else:
            # Variable
            instructions.append(
                MIPSInstruction("lw", ("$v0", return_value), comment="load return value")
            )

        return instructions

    @staticmethod
    def get_caller_saved_registers() -> List[str]:
        """
        Get list of caller-saved registers.

        These registers may be clobbered by a function call,
        so the caller must save them if needed.
        """
        return TEMPORARY_REGISTERS + ARGUMENT_REGISTERS + RETURN_REGISTERS

    @staticmethod
    def get_callee_saved_registers() -> List[str]:
        """
        Get list of callee-saved registers.

        These registers must be preserved by the callee if used.
        """
        return SAVED_REGISTERS + ["$fp", "$ra"]

    @staticmethod
    def is_caller_saved(register: str) -> bool:
        """Check if a register is caller-saved."""
        return register in CallingConvention.get_caller_saved_registers()

    @staticmethod
    def is_callee_saved(register: str) -> bool:
        """Check if a register is callee-saved."""
        return register in CallingConvention.get_callee_saved_registers()
