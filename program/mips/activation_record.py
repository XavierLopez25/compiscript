"""
Activation Record Management for MIPS Code Generation

This module manages stack frames (activation records) for function calls,
including calculating frame sizes, managing local variables, and handling
parameter passing.

MIPS Stack Frame Layout (grows downward):
┌─────────────────────────┐  ← Higher addresses
│   Caller's frame        │
├─────────────────────────┤
│   Param N (if N > 4)    │
│   ...                    │
│   Param 5 (if > 4)      │
├─────────────────────────┤  ← $fp (Frame Pointer)
│   Return Address ($ra)  │  ← offset -4 from $fp
├─────────────────────────┤
│   Old Frame Pointer     │  ← offset -8 from $fp
├─────────────────────────┤
│   Saved $s0             │  ← offset -12 (if used)
│   Saved $s1             │  ← offset -16 (if used)
│   ...                    │
│   Saved $s7             │  ← offset -44 (if all used)
├─────────────────────────┤
│   Local Variable 1      │
│   Local Variable 2      │
│   ...                    │
├─────────────────────────┤
│   Spill Area            │  ← Temporary spills
├─────────────────────────┤
│   Outgoing Params       │  ← Space for params to functions we call
└─────────────────────────┘  ← $sp (Stack Pointer)
                             ← Lower addresses
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class LocalVariable:
    """Information about a local variable in the activation record."""
    name: str
    size_bytes: int
    offset: int  # Negative offset from $fp


@dataclass
class ActivationRecord:
    """
    Represents a function's activation record (stack frame).

    Attributes:
        function_name: Name of the function
        param_count: Number of parameters
        local_vars: List of local variables
        saved_registers: Registers that need to be preserved ($s0-$s7)
        frame_size: Total size of the frame in bytes
        return_address_offset: Offset of $ra from $fp
        old_fp_offset: Offset of old $fp from $fp
        locals_start_offset: Where local variables start
        spill_area_size: Size reserved for register spills
        max_outgoing_params: Maximum parameters for any function call
    """
    function_name: str
    param_count: int
    local_vars: List[LocalVariable]
    saved_registers: List[str]
    frame_size: int
    return_address_offset: int
    old_fp_offset: int
    locals_start_offset: int
    spill_area_size: int
    max_outgoing_params: int

    def get_local_offset(self, var_name: str) -> Optional[int]:
        """Get the offset of a local variable from $fp."""
        for var in self.local_vars:
            if var.name == var_name:
                return var.offset
        return None

    def get_param_offset(self, param_index: int) -> int:
        """
        Get the offset of a parameter from $fp.

        First 4 params may be in $a0-$a3 (caller's responsibility).
        Params 5+ are on stack at positive offsets from $fp.

        Args:
            param_index: 0-based parameter index

        Returns:
            Offset from $fp (positive for params 5+)
        """
        if param_index < 4:
            # First 4 params typically passed in registers
            # If accessed from stack, they're at caller's frame
            # This should rarely be used; params are typically in registers
            return 4 * (param_index + 1)
        else:
            # Params beyond 4 are on stack
            # They're at positive offsets from $fp (in caller's frame)
            return 4 * (param_index - 3)

    def get_saved_register_offset(self, register: str) -> Optional[int]:
        """Get the offset where a saved register is stored."""
        if register == "$ra":
            return self.return_address_offset
        if register == "$fp":
            return self.old_fp_offset

        # $s0-$s7 saved after $ra and old $fp
        if register in self.saved_registers:
            idx = self.saved_registers.index(register)
            return self.old_fp_offset - 4 * (idx + 1)

        return None


class ActivationRecordBuilder:
    """
    Builder for constructing activation records with proper sizing.

    Usage:
        builder = ActivationRecordBuilder("myFunc", param_count=2)
        builder.add_local_var("localX", 4)
        builder.add_local_var("localY", 4)
        builder.set_saved_registers(["$s0", "$s1"])
        builder.set_spill_area_size(16)
        builder.set_max_outgoing_params(3)
        record = builder.build()
    """

    def __init__(self, function_name: str, param_count: int):
        self.function_name = function_name
        self.param_count = param_count
        self.local_vars: List[LocalVariable] = []
        self.saved_registers: List[str] = []
        self.spill_area_size: int = 0
        self.max_outgoing_params: int = 0

    def add_local_var(self, name: str, size_bytes: int) -> 'ActivationRecordBuilder':
        """Add a local variable to the frame."""
        self.local_vars.append(LocalVariable(name, size_bytes, 0))
        return self

    def set_saved_registers(self, registers: List[str]) -> 'ActivationRecordBuilder':
        """
        Set which $s registers need to be saved.

        Args:
            registers: List of registers like ["$s0", "$s1", "$s2"]
        """
        # Filter to only $s0-$s7
        self.saved_registers = [r for r in registers if r in [
            "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7"
        ]]
        return self

    def set_spill_area_size(self, size_bytes: int) -> 'ActivationRecordBuilder':
        """Set the size of the register spill area."""
        # Align to 4-byte boundary
        self.spill_area_size = (size_bytes + 3) & ~3
        return self

    def set_max_outgoing_params(self, count: int) -> 'ActivationRecordBuilder':
        """Set the maximum number of parameters for outgoing calls."""
        self.max_outgoing_params = count
        return self

    def build(self) -> ActivationRecord:
        """
        Build the activation record with calculated offsets.

        Frame layout (negative offsets from $fp):
        $fp + 0: [caller's frame boundary]
        $fp - 4: $ra (return address)
        $fp - 8: old $fp
        $fp - 12: $s0 (if saved)
        $fp - 16: $s1 (if saved)
        ...
        $fp - X: local variables
        $fp - Y: spill area
        $fp - Z: outgoing params area
        """
        # Fixed offsets
        return_address_offset = -4
        old_fp_offset = -8

        # Saved registers come after $ra and old $fp
        saved_regs_size = len(self.saved_registers) * 4
        locals_start_offset = old_fp_offset - saved_regs_size

        # Calculate local variable offsets
        current_offset = locals_start_offset
        for var in self.local_vars:
            current_offset -= var.size_bytes
            var.offset = current_offset

        # Add spill area
        spill_start = current_offset - self.spill_area_size

        # Add space for outgoing parameters (if any beyond $a0-$a3)
        outgoing_param_space = 0
        if self.max_outgoing_params > 4:
            outgoing_param_space = (self.max_outgoing_params - 4) * 4

        # Calculate total frame size
        # Must be aligned to 8 bytes for MIPS calling convention
        total_size = (
            4 +  # $ra
            4 +  # old $fp
            saved_regs_size +
            sum(var.size_bytes for var in self.local_vars) +
            self.spill_area_size +
            outgoing_param_space
        )

        # Align to 8-byte boundary
        frame_size = (total_size + 7) & ~7

        return ActivationRecord(
            function_name=self.function_name,
            param_count=self.param_count,
            local_vars=self.local_vars,
            saved_registers=self.saved_registers,
            frame_size=frame_size,
            return_address_offset=return_address_offset,
            old_fp_offset=old_fp_offset,
            locals_start_offset=locals_start_offset,
            spill_area_size=self.spill_area_size,
            max_outgoing_params=self.max_outgoing_params,
        )


class ActivationRecordManager:
    """
    Manages activation records for all functions in the program.

    Maintains a stack of active records to handle nested function calls
    and provides lookup for current frame information.
    """

    def __init__(self):
        self.records: Dict[str, ActivationRecord] = {}
        self.current_function: Optional[str] = None
        self.call_stack: List[str] = []

    def register_function(self, record: ActivationRecord) -> None:
        """Register an activation record for a function."""
        self.records[record.function_name] = record

    def enter_function(self, function_name: str) -> ActivationRecord:
        """
        Enter a function scope.

        Args:
            function_name: Name of the function being entered

        Returns:
            The activation record for this function

        Raises:
            KeyError: If function not registered
        """
        if function_name not in self.records:
            raise KeyError(f"Function {function_name} not registered")

        self.call_stack.append(function_name)
        self.current_function = function_name
        return self.records[function_name]

    def exit_function(self) -> None:
        """Exit the current function scope."""
        if self.call_stack:
            self.call_stack.pop()
        self.current_function = self.call_stack[-1] if self.call_stack else None

    def get_current_record(self) -> Optional[ActivationRecord]:
        """Get the activation record for the current function."""
        if self.current_function:
            return self.records.get(self.current_function)
        return None

    def get_record(self, function_name: str) -> Optional[ActivationRecord]:
        """Get the activation record for a specific function."""
        return self.records.get(function_name)

    def reset(self) -> None:
        """Reset the manager (for testing or new compilation)."""
        self.records.clear()
        self.current_function = None
        self.call_stack.clear()
