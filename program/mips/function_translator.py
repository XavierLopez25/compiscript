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

    def __init__(self, data_section_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.data_section_manager = data_section_manager
        self.activation_manager = ActivationRecordManager()
        self.current_function: Optional[str] = None
        self.pending_params: List[PendingParameter] = []
        self.param_counter: int = 0

        # Track which functions have been defined
        self.defined_functions: Set[str] = set()

        # Track leaf functions that don't need a full frame
        # Format: {func_name: True/False}
        self.simple_leaf_functions: Set[str] = set()

    @staticmethod
    def sanitize_function_name(func_name: str) -> str:
        """
        Sanitize function names to avoid conflicts with MIPS reserved words.

        MIPS instruction names that conflict with user functions:
        - add, sub, mul, div, and, or, xor, nor, sll, srl, sra
        - lb, lh, lw, sb, sh, sw, la, li, move
        - beq, bne, blt, ble, bgt, bge, j, jal, jr

        Runtime function names we want to preserve:
        - print, print_int, print_newline, allocate_array, string_concat, int_to_string

        Args:
            func_name: Original function name from TAC

        Returns:
            Sanitized function name safe for MIPS
        """
        # List of MIPS reserved instruction names
        reserved_instructions = {
            'add', 'sub', 'mul', 'div', 'mod',
            'and', 'or', 'xor', 'nor', 'not',
            'sll', 'srl', 'sra',
            'lb', 'lh', 'lw', 'sb', 'sh', 'sw',
            'la', 'li', 'lui', 'ori',
            'move', 'mfhi', 'mflo',
            'beq', 'bne', 'blt', 'ble', 'bgt', 'bge', 'bltz', 'bgez', 'beqz', 'bnez',
            'j', 'jal', 'jr', 'jalr',
            'syscall', 'break', 'nop'
        }

        # Runtime functions that should NOT be prefixed
        runtime_functions = {
            'print', 'print_int', 'print_newline',
            'allocate_array', 'string_concat', 'int_to_string',
            'main'
        }

        # Check if it's a runtime function or already has a known prefix
        if func_name in runtime_functions:
            return func_name

        # Check if it's a method/constructor (already has Class_ prefix)
        if '_constructor' in func_name or func_name.startswith('method_') or func_name.startswith('default_constructor_'):
            return func_name

        # Check if it conflicts with reserved instruction
        if func_name.lower() in reserved_instructions:
            return f"user_{func_name}"

        # Otherwise, return as-is
        return func_name

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

        # Sanitize function name to avoid conflicts with MIPS instructions
        func_name = self.sanitize_function_name(instr.name)
        self.current_function = func_name
        self.defined_functions.add(func_name)

        # Get or create activation record
        # Use frame_size from TAC if available
        if not self.activation_manager.get_record(func_name):
            builder = ActivationRecordBuilder(func_name, instr.param_count)

            # Use frame_size from TAC if provided
            if hasattr(instr, 'frame_size') and instr.frame_size > 0:
                # TAC provided frame size - use it directly
                builder.set_spill_area_size(instr.frame_size)
            else:
                # Fallback to estimated size
                # For methods/constructors, ensure minimum frame size for parameters
                min_frame = max(instr.param_count * 4, 16)  # At least 16 bytes
                builder.set_saved_registers([])  # No $s registers for simple case
                builder.set_spill_area_size(max(self.required_spill_space, min_frame))

            builder.set_max_outgoing_params(0)  # Will be updated if needed
            record = builder.build()
            self.activation_manager.register_function(record)

        record = self.activation_manager.enter_function(func_name)

        # Detect simple leaf functions that can be optimized
        # DISABLED: This optimization is unsafe because it doesn't detect recursive calls
        # Functions marked as leaf but containing calls will try to spill to uninitialized $fp
        # causing "Bad address" errors at address 0x00000000
        # TODO: Implement proper call detection before re-enabling this optimization
        # if (hasattr(instr, 'frame_size') and instr.frame_size == 48 and
        #     instr.param_count == 1):
        #     self.simple_leaf_functions.add(func_name)

        # Reset register allocator for new function scope
        # This ensures clean state and allows parameter pre-registration
        self.register_allocator.reset()

        # Pre-register parameter locations BEFORE generating prologue
        # This ensures the register allocator knows where parameters are
        param_names = getattr(instr, 'param_names', [])

        # For methods/constructors without param_names, infer from function name
        if not param_names and record.param_count > 0:
            # Check if it's a constructor or method (contains 'constructor' or starts with method_)
            if 'constructor' in func_name.lower() or func_name.startswith('method_'):
                # First param is always 'this' for methods/constructors
                param_names = ['this'] + [f'param{i}' for i in range(1, record.param_count)]
            else:
                param_names = [f'param{i}' for i in range(record.param_count)]

        # For simple leaf functions, parameters will be copied in the prologue
        # For regular functions, parameters are on the stack
        if func_name not in self.simple_leaf_functions:
            # Regular function - parameters go on stack
            for i in range(min(record.param_count, 4)):
                if i < len(param_names):
                    param_name = param_names[i]
                    param_offset = i * 4
                    # Force the register allocator to use this specific stack location
                    self.register_allocator.force_stack_location(param_name, param_offset)

        # Emit function label BEFORE prologue so calls land on prologue
        # This is important for methods that have an extra label in TAC
        self.emit_label(func_name)

        # Generate prologue
        self._generate_function_prologue(record, instr)

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

        # Sanitize function name to match what was emitted in BeginFunc
        sanitized_func_name = self.sanitize_function_name(instr.function)

        # Create calling context
        context = CallingConvention.create_calling_context(
            function_name=sanitized_func_name,
            param_count=instr.param_count,
            has_return_value=instr.target is not None,
        )

        # Validate we have the right number of parameters
        if len(self.pending_params) != instr.param_count:
            raise ValueError(
                f"Parameter mismatch: expected {instr.param_count}, "
                f"got {len(self.pending_params)}"
            )

        # IMPORTANT: Spill all caller-saved registers before function call
        # This preserves live variables in $t0-$t9 which the callee can modify
        caller_spills = self.spill_caller_saved()
        if caller_spills:
            self.emit_comment("Save caller-saved registers")
            self.materialise_spills(caller_spills)

        # Generate parameter passing code
        for param in self.pending_params:
            location = context.param_locations[param.index]
            # Get the actual value/register for the parameter
            param_source = self._get_param_source(param.value)
            instructions = CallingConvention.generate_push_param(
                param_source, location, temp_reg="$t0"
            )
            self.emit_text_many(instructions)

        # Generate the call (use sanitized function name)
        call_instrs = CallingConvention.generate_function_call(sanitized_func_name)
        self.emit_text_many(call_instrs)

        # After the call, mark caller-saved registers as invalid so future uses reload from memory
        self.invalidate_caller_saved()

        # Retrieve return value if needed
        if instr.target:
            # Use register allocator to get a register for the return value
            dest_reg, spills, loads = self.acquire_register(instr.target, is_write=True)
            self.materialise_spills(spills)
            self.materialise_loads(loads)

            # Move return value from $v0 to destination register
            if dest_reg != "$v0":
                self.emit_text(MIPSInstruction("move", (dest_reg, "$v0"), comment="get return value"))

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
            # Check if the value is a literal constant
            if instr.value.lstrip('-').isdigit():
                # It's a numeric literal - load directly
                self.emit_text(MIPSInstruction("li", ("$v0", instr.value), comment="return literal value"))
            elif instr.value.startswith('"') and instr.value.endswith('"'):
                # It's a string literal - add to data section and load address
                label = self.data_section_manager.add_string_literal(instr.value)
                self.emit_text(MIPSInstruction("la", ("$v0", label), comment="return string literal"))
            else:
                # It's a variable - try to get from register allocator
                try:
                    reg, spills, loads = self.acquire_register(instr.value, is_write=False)
                    self.materialise_spills(spills)
                    self.materialise_loads(loads)

                    # Move from the register to $v0
                    if reg != "$v0":
                        self.emit_text(MIPSInstruction("move", ("$v0", reg), comment="set return value"))
                except:
                    # Fallback to old method if register allocation fails
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

    def _generate_function_prologue(self, record: ActivationRecord, instr: BeginFuncInstruction) -> None:
        """
        Generate the function prologue.

        Args:
            record: Activation record for the function
            instr: BeginFunc TAC instruction with parameter names
        """
        func_name = self.sanitize_function_name(instr.name)

        # Check if this is a simple leaf function that doesn't need a full frame
        if func_name in self.simple_leaf_functions:
            # Simple leaf function - no frame needed, just return directly
            # Parameters stay in $a0-$a3, no stack manipulation
            self.emit_comment("Leaf function - no frame needed")

            # Copy parameter from $a0 to a temporary register so it can be used
            # by the register allocator (which doesn't manage $a0)
            param_regs = ["$a0", "$a1", "$a2", "$a3"]
            param_names = getattr(instr, 'param_names', [])

            for i in range(min(record.param_count, 4)):
                if i < len(param_names):
                    param_name = param_names[i]
                    # Allocate a register for the parameter (write=True since we're setting it)
                    dest_reg, spills, loads = self.register_allocator.get_register(
                        param_name, is_write=True
                    )
                    # Copy from argument register to allocated register
                    self.emit_text(
                        MIPSInstruction("move", (dest_reg, param_regs[i]),
                                      comment=f"copy parameter '{param_name}' from {param_regs[i]}")
                    )
            return

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

        # Set new frame pointer to point to base of allocated frame
        self.emit_text(
            MIPSInstruction(
                "move", ("$fp", "$sp"), comment="set frame pointer"
            )
        )

        # Save function parameters from $a0-$a3 to stack
        # Parameters are at known offsets in the activation record
        param_regs = ["$a0", "$a1", "$a2", "$a3"]
        param_names = getattr(instr, 'param_names', [])

        for i in range(min(record.param_count, 4)):
            # Parameters are stored at the beginning of the local variable area
            # Offset from $sp: 0, 4, 8, 12 for params 0-3
            param_offset = i * 4
            param_name = param_names[i] if i < len(param_names) else f"param{i}"
            self.emit_text(
                MIPSInstruction("sw", (param_regs[i], f"{param_offset}($sp)"),
                              comment=f"save parameter '{param_name}' from {param_regs[i]}")
            )
            # Note: Parameter locations are already registered in translate_begin_func

    def _generate_function_epilogue(self, record: ActivationRecord) -> None:
        """
        Generate the function epilogue.

        Args:
            record: Activation record for the function
        """
        # Check if this is a simple leaf function
        if self.current_function in self.simple_leaf_functions:
            # Simple leaf - no frame to restore, just return
            # Result should already be in $v0
            self.emit_text(MIPSInstruction("jr", ("$ra",), comment="return"))
            return

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
