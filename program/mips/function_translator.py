"""
Function Call and Return Translation for MIPS

This module translates TAC function-related instructions to MIPS assembly:
- BeginFunc: Function prologue (save registers, allocate frame)
- EndFunc: Function epilogue (restore registers, deallocate frame, return)
- PushParam: Parameter passing
- call: Function invocation
- PopParams: Stack cleanup after call
- return: Return from function

TAC Function Call Pattern:
    BeginFunc foo, 2
    func_foo:
        ... function body ...
        return result
    EndFunc foo

    PushParam arg1
    PushParam arg2
    result = call foo, 2
    PopParams 2
"""

from typing import List, Optional, Dict, Set
from dataclasses import dataclass

from tac.instruction import (
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
)

from .translator_base import MIPSTranslatorBase
from .instruction import MIPSInstruction, MIPSLabel, MIPSComment
from .activation_record import (
    ActivationRecord,
    ActivationRecordBuilder,
    ActivationRecordManager,
)
from .calling_convention import CallingConvention, CallingContext


@dataclass
class PendingParameter:
    """Tracks a parameter being prepared for a function call."""
    value: str  # Variable name, constant, or register
    index: int  # Parameter index (0-based)


class FunctionTranslator(MIPSTranslatorBase):
    """
    Translates TAC function calls to MIPS assembly.

    Handles:
    - Function prologues and epilogues
    - Parameter passing via registers and stack
    - Return value handling
    - Register preservation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.activation_manager = ActivationRecordManager()
        self.current_function: Optional[str] = None
        self.pending_params: List[PendingParameter] = []
        self.param_counter: int = 0

        # Track which functions have been defined
        self.defined_functions: Set[str] = set()

    def translate_begin_func(self, instr: BeginFuncInstruction) -> None:
        """
        Translate BeginFunc instruction to MIPS function prologue.

        Prologue steps:
        1. Save $ra (return address)
        2. Save $fp (old frame pointer)
        3. Save any $s registers we'll use
        4. Allocate space for locals and temporaries
        5. Set new $fp

        Args:
            instr: BeginFunc TAC instruction
        """
        self.emit_comment(f"Function: {instr.name} (params: {instr.param_count})")

        func_name = instr.name
        self.current_function = func_name
        self.defined_functions.add(func_name)

        # Get or create activation record
        # For now, we'll create a simple one
        # In a real implementation, you'd analyze the function body first
        # to determine local variables and register usage
        if not self.activation_manager.get_record(func_name):
            builder = ActivationRecordBuilder(func_name, instr.param_count)
            # TODO: Analyze function body to determine:
            # - Local variables
            # - Saved registers needed
            # - Spill space
            # - Max outgoing params
            # For now, use defaults
            builder.set_saved_registers([])  # No $s registers for simple case
            builder.set_spill_area_size(self.required_spill_space)
            builder.set_max_outgoing_params(0)  # Will be updated if needed
            record = builder.build()
            self.activation_manager.register_function(record)

        record = self.activation_manager.enter_function(func_name)

        # Generate prologue
        self._generate_function_prologue(record)

    def translate_end_func(self, instr: EndFuncInstruction) -> None:
        """
        Translate EndFunc instruction to MIPS function epilogue.

        Epilogue steps:
        1. Restore saved $s registers
        2. Restore $fp
        3. Restore $ra
        4. Deallocate frame
        5. Return (jr $ra)

        Args:
            instr: EndFunc TAC instruction
        """
        record = self.activation_manager.get_current_record()
        if not record:
            raise ValueError(f"EndFunc without corresponding BeginFunc: {instr.name}")

        self.emit_comment(f"End function: {instr.name}")

        # Generate epilogue
        self._generate_function_epilogue(record)

        self.activation_manager.exit_function()
        self.current_function = None

    def translate_push_param(self, instr: PushParamInstruction) -> None:
        """
        Translate PushParam instruction.

        Parameters are collected in order. When we see the corresponding
        'call' instruction, we'll emit all the parameter passing code.

        Args:
            instr: PushParam TAC instruction
        """
        # Queue the parameter
        param = PendingParameter(
            value=instr.param,
            index=self.param_counter,
        )
        self.pending_params.append(param)
        self.param_counter += 1

    def translate_call(self, instr: CallInstruction) -> None:
        """
        Translate call instruction to MIPS function call.

        Steps:
        1. Move/load parameters into $a0-$a3 or push to stack
        2. Call function with jal
        3. Retrieve return value (if any)

        Args:
            instr: Call TAC instruction
        """
        self.emit_comment(f"Call {instr.function} with {instr.param_count} params")

        # Create calling context
        context = CallingConvention.create_calling_context(
            function_name=instr.function,
            param_count=instr.param_count,
            has_return_value=instr.target is not None,
        )

        # Validate we have the right number of parameters
        if len(self.pending_params) != instr.param_count:
            raise ValueError(
                f"Parameter mismatch: expected {instr.param_count}, "
                f"got {len(self.pending_params)}"
            )

        # Generate parameter passing code
        for param in self.pending_params:
            location = context.param_locations[param.index]
            # Get the actual value/register for the parameter
            param_source = self._get_param_source(param.value)
            instructions = CallingConvention.generate_push_param(
                param_source, location, temp_reg="$t0"
            )
            self.emit_text_many(instructions)

        # Generate the call
        call_instrs = CallingConvention.generate_function_call(instr.function)
        self.emit_text_many(call_instrs)

        # Retrieve return value if needed
        if instr.target:
            retrieve_instrs = CallingConvention.generate_return_value_retrieval(
                instr.target, temp_reg="$t0"
            )
            self.emit_text_many(retrieve_instrs)

        # Clear pending parameters
        self.pending_params.clear()
        self.param_counter = 0

    def translate_pop_params(self, instr: PopParamsInstruction) -> None:
        """
        Translate PopParams instruction.

        Cleans up stack space used for parameters beyond first 4.

        Args:
            instr: PopParams TAC instruction
        """
        # Generate stack cleanup
        pop_instrs = CallingConvention.generate_pop_params(instr.param_count)
        if pop_instrs:
            self.emit_comment(f"Clean up {instr.param_count} params")
            self.emit_text_many(pop_instrs)

    def translate_return(self, instr: ReturnInstruction) -> None:
        """
        Translate return instruction.

        Steps:
        1. Load return value into $v0 (if any)
        2. Jump to function epilogue

        The actual restoration of registers and return happens in the epilogue
        generated by EndFunc.

        Args:
            instr: Return TAC instruction
        """
        self.emit_comment("Return statement")

        # Load return value into $v0
        if instr.value:
            return_instrs = CallingConvention.generate_return_statement(
                instr.value, temp_reg="$t0"
            )
            self.emit_text_many(return_instrs)

        # Note: The actual epilogue (restoring registers and jr $ra)
        # is generated by translate_end_func.
        # If there are multiple return statements, we'd need to either:
        # 1. Jump to a common epilogue label
        # 2. Duplicate the epilogue code
        # For simplicity, we'll generate inline epilogue here

        record = self.activation_manager.get_current_record()
        if record:
            self._generate_function_epilogue(record)

    def _generate_function_prologue(self, record: ActivationRecord) -> None:
        """
        Generate the function prologue.

        Args:
            record: Activation record for the function
        """
        # Allocate stack frame
        self.emit_text(
            MIPSInstruction(
                "addi",
                ("$sp", "$sp", str(-record.frame_size)),
                comment=f"allocate frame ({record.frame_size} bytes)",
            )
        )

        # Save $ra
        ra_offset = record.frame_size + record.return_address_offset
        self.emit_text(
            MIPSInstruction("sw", ("$ra", f"{ra_offset}($sp)"), comment="save return address")
        )

        # Save old $fp
        fp_offset = record.frame_size + record.old_fp_offset
        self.emit_text(
            MIPSInstruction("sw", ("$fp", f"{fp_offset}($sp)"), comment="save frame pointer")
        )

        # Save $s registers if used
        for i, reg in enumerate(record.saved_registers):
            offset = fp_offset - 4 * (i + 1)
            self.emit_text(MIPSInstruction("sw", (reg, f"{offset}($sp)"), comment=f"save {reg}"))

        # Set new frame pointer
        self.emit_text(
            MIPSInstruction(
                "addi", ("$fp", "$sp", str(record.frame_size)), comment="set frame pointer"
            )
        )

    def _generate_function_epilogue(self, record: ActivationRecord) -> None:
        """
        Generate the function epilogue.

        Args:
            record: Activation record for the function
        """
        # Restore $s registers if saved
        fp_offset = record.frame_size + record.old_fp_offset
        for i, reg in enumerate(record.saved_registers):
            offset = fp_offset - 4 * (i + 1)
            self.emit_text(MIPSInstruction("lw", (reg, f"{offset}($sp)"), comment=f"restore {reg}"))

        # Restore old $fp
        self.emit_text(
            MIPSInstruction("lw", ("$fp", f"{fp_offset}($sp)"), comment="restore frame pointer")
        )

        # Restore $ra
        ra_offset = record.frame_size + record.return_address_offset
        self.emit_text(
            MIPSInstruction("lw", ("$ra", f"{ra_offset}($sp)"), comment="restore return address")
        )

        # Deallocate frame
        self.emit_text(
            MIPSInstruction(
                "addi", ("$sp", "$sp", str(record.frame_size)), comment="deallocate frame"
            )
        )

        # Return
        self.emit_text(MIPSInstruction("jr", ("$ra",), comment="return"))

    def get_activation_record(self, func_name: str) -> Optional[ActivationRecord]:
        """Get the activation record for a function."""
        return self.activation_manager.get_record(func_name)

    def is_function_defined(self, func_name: str) -> bool:
        """Check if a function has been defined."""
        return func_name in self.defined_functions

    def _get_param_source(self, param_value: str) -> str:
        """
        Get the source for a parameter value (register or label).

        If the param is a variable in a register, get that register.
        If it's a label (_str, _array), return as-is.
        If it's a constant, return as-is.

        Args:
            param_value: Parameter value from TAC

        Returns:
            Register name, label, or constant value
        """
        # Check if it's already a register
        if param_value.startswith("$"):
            return param_value

        # Check if it's a label (string/array)
        if param_value.startswith("_str") or param_value.startswith("_array"):
            return param_value

        # Check if it's a constant
        if param_value.isdigit() or (param_value.startswith("-") and param_value[1:].isdigit()):
            return param_value

        # It's a variable - try to get its register using the allocator
        try:
            reg, spills, loads = self.acquire_register(param_value, is_write=False)
            # Materialize loads if needed
            self.materialise_spills(spills)
            self.materialise_loads(loads)
            return reg
        except:
            # Fallback: return variable name (will use lw)
            return param_value


# Convenience function for standalone usage
def translate_function_call_sequence(
    translator: FunctionTranslator,
    function_name: str,
    params: List[str],
    return_target: Optional[str] = None,
) -> None:
    """
    High-level helper to translate a complete function call sequence.

    Args:
        translator: FunctionTranslator instance
        function_name: Name of function to call
        params: List of parameter values
        return_target: Where to store return value (if any)
    """
    # Push parameters
    for param in params:
        instr = PushParamInstruction(param)
        translator.translate_push_param(instr)

    # Call function
    call_instr = CallInstruction(function_name, len(params), return_target)
    translator.translate_call(call_instr)

    # Pop parameters
    if len(params) > 0:
        pop_instr = PopParamsInstruction(len(params))
        translator.translate_pop_params(pop_instr)
