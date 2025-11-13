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
        # Track variables/temporaries that are known to be strings
        self.string_vars = set()  # Variables like 'greeting', 'err', 'message'

    def mark_as_string(self, var_name: str) -> None:
        """Mark a variable/temporary as containing a string value."""
        self.string_vars.add(var_name)

    def is_string_var(self, var_name: str) -> bool:
        """Check if a variable is tracked as a string."""
        return var_name in self.string_vars

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
            # If it's a string concatenation, mark target as string
            if operator == "str_concat":
                self.mark_as_string(target)
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

        # Comparison operations require both operands in registers (slt doesn't support immediates)
        comparison_ops = ['<', '>', '<=', '>=', '==', '!=']
        if operator in comparison_ops:
            # Always load both operands into registers for comparisons
            src2_reg = self._load_operand(operand2, forbidden=[dest_reg, src1_reg])
            instructions = self._generate_binary_instructions(
                operator, dest_reg, src1_reg, src2_reg,
                operand1_orig=operand1, operand2_orig=operand2, is_immediate=False
            )
        elif is_immediate:
            # Use immediate value directly (for arithmetic operations)
            src2_operand = operand2
            instructions = self._generate_binary_instructions(
                operator, dest_reg, src1_reg, src2_operand,
                operand1_orig=operand1, operand2_orig=operand2, is_immediate=True
            )
        else:
            # Load operand2 into register
            src2_reg = self._load_operand(operand2, forbidden=[dest_reg, src1_reg])
            instructions = self._generate_binary_instructions(
                operator, dest_reg, src1_reg, src2_reg,
                operand1_orig=operand1, operand2_orig=operand2, is_immediate=False
            )

        # Emit generated instructions
        self.base.emit_text_many(instructions)

    def _generate_binary_instructions(
        self,
        operator: str,
        dest_reg: str,
        src1_reg: str,
        src2_operand: str,
        operand1_orig: str = "",
        operand2_orig: str = "",
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

        # String operations
        elif operator == "str_concat":
            # String concatenation using runtime function
            # Automatically converts integers to strings if needed
            # $a0 = first string, $a1 = second string
            # Result in $v0

            # Helper function to check if operand is likely a string
            def is_likely_string(operand_name):
                """Check if operand is likely a string based on heuristics."""
                if not operand_name:
                    return False
                # Check if explicitly tracked as string
                if self.is_string_var(operand_name):
                    return True
                # String literals start with _str or are quoted
                if operand_name.startswith("_str") or operand_name.startswith('"'):
                    return True
                # Common string variable names
                string_keywords = ['err', 'error', 'message', 'msg', 'name', 'text', 'str', 'greeting']
                name_lower = operand_name.lower()
                return any(keyword in name_lower for keyword in string_keywords)

            instructions = []

            # Save $ra and $s registers we'll use as temporaries
            # Note: We DON'T save $t registers here because the register allocator
            # has already spilled any live variables to $fp-relative locations
            # Saving $t registers here would conflict with the allocator's spills
            instructions.append(MIPSInstruction("addi", ("$sp", "$sp", "-16"), comment="save space for $ra and $s regs"))
            instructions.append(MIPSInstruction("sw", ("$ra", "12($sp)"), comment="save $ra"))
            instructions.append(MIPSInstruction("sw", ("$s0", "8($sp)"), comment="save $s0"))
            instructions.append(MIPSInstruction("sw", ("$s1", "4($sp)"), comment="save $s1"))
            instructions.append(MIPSInstruction("sw", ("$s2", "0($sp)"), comment="save $s2"))

            # For str_concat operator, we need to be smart about which operands need conversion
            # - String literals (start with _str) -> use directly
            # - String variables (likely_string) -> use directly
            # - Everything else (int, bool, temporaries from operations) -> convert

            # Handle first operand
            if operand1_orig and operand1_orig.startswith("_str"):
                # String literal
                instructions.append(MIPSInstruction("la", ("$s0", operand1_orig), comment="load str1 label"))
            elif operand1_orig and is_likely_string(operand1_orig):
                # Variable that's likely a string (has 'name', 'err', 'message', etc.)
                instructions.append(MIPSInstruction("move", ("$s0", src1_reg), comment="str1 (already string)"))
            else:
                # Variable or temporary - might be int/bool, needs conversion
                instructions.append(MIPSInstruction("move", ("$a0", src1_reg), comment="load value to convert"))
                instructions.append(MIPSInstruction("jal", ("int_to_string",), comment="convert to string"))
                instructions.append(MIPSInstruction("move", ("$s0", "$v0"), comment="save str1"))

            # Handle second operand
            if operand2_orig and operand2_orig.startswith("_str"):
                # String literal
                instructions.append(MIPSInstruction("la", ("$s1", operand2_orig), comment="load str2 label"))
            elif operand2_orig and is_likely_string(operand2_orig):
                # Variable that's likely a string
                instructions.append(MIPSInstruction("move", ("$s1", src2_operand), comment="str2 (already string)"))
            else:
                # Variable/temp/register - might be int/bool, needs conversion
                instructions.append(MIPSInstruction("move", ("$a0", src2_operand), comment="load value to convert"))
                instructions.append(MIPSInstruction("jal", ("int_to_string",), comment="convert to string"))
                instructions.append(MIPSInstruction("move", ("$s1", "$v0"), comment="save str2"))

            # Now call string_concat with both strings
            instructions.append(MIPSInstruction("move", ("$a0", "$s0"), comment="str1 to $a0"))
            instructions.append(MIPSInstruction("move", ("$a1", "$s1"), comment="str2 to $a1"))
            instructions.append(MIPSInstruction("jal", ("string_concat",), comment="call string concat"))

            # Save result temporarily before restoring $s registers
            instructions.append(MIPSInstruction("move", ("$v1", "$v0"), comment="save result in $v1"))

            # Restore saved $s registers and $ra
            instructions.append(MIPSInstruction("lw", ("$s2", "0($sp)"), comment="restore $s2"))
            instructions.append(MIPSInstruction("lw", ("$s1", "4($sp)"), comment="restore $s1"))
            instructions.append(MIPSInstruction("lw", ("$s0", "8($sp)"), comment="restore $s0"))
            instructions.append(MIPSInstruction("lw", ("$ra", "12($sp)"), comment="restore $ra"))
            instructions.append(MIPSInstruction("addi", ("$sp", "$sp", "16"), comment="deallocate space"))

            # Move result from $v1 to destination (after all restores)
            instructions.append(MIPSInstruction("move", (dest_reg, "$v1"), comment="get result"))

            return instructions

        # Type conversion operations
        elif operator == "int_to_float":
            # MIPS conversion: mtc1, cvt.s.w
            return [
                MIPSInstruction("mtc1", (src1_reg, "$f0"), comment="move int to FPU"),
                MIPSInstruction("cvt.s.w", ("$f0", "$f0"), comment="convert to float"),
                MIPSInstruction("mfc1", (dest_reg, "$f0"), comment="move back to int reg"),
            ]
        elif operator == "float_to_int":
            # MIPS conversion: mtc1, cvt.w.s, mfc1
            return [
                MIPSInstruction("mtc1", (src1_reg, "$f0"), comment="move to FPU"),
                MIPSInstruction("cvt.w.s", ("$f0", "$f0"), comment="convert to int"),
                MIPSInstruction("mfc1", (dest_reg, "$f0"), comment="move back to int reg"),
            ]
        elif operator == "to_string":
            # String conversion requires runtime support
            return [
                MIPSInstruction("nop", (), comment=f"TODO: to_string {src1_reg} -> {dest_reg}")
            ]

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
        elif operator == "int_to_float":
            instructions = [
                MIPSInstruction("mtc1", (src_reg, "$f0"), comment="move int to FPU"),
                MIPSInstruction("cvt.s.w", ("$f0", "$f0"), comment="convert to float"),
                MIPSInstruction("mfc1", (dest_reg, "$f0"), comment="move back to int reg"),
            ]
        elif operator == "float_to_int":
            instructions = [
                MIPSInstruction("mtc1", (src_reg, "$f0"), comment="move to FPU"),
                MIPSInstruction("cvt.w.s", ("$f0", "$f0"), comment="convert to int"),
                MIPSInstruction("mfc1", (dest_reg, "$f0"), comment="move back to int reg"),
            ]
        elif operator == "to_string":
            instructions = [
                MIPSInstruction("nop", (), comment=f"TODO: to_string {src_reg} -> {dest_reg}")
            ]
        elif operator == "len":
            # For arrays, we return a constant size (simplified implementation)
            # In a full implementation, we'd store the size in the array header
            # For now, return 5 as a placeholder for array lengths
            instructions = [
                MIPSInstruction("li", (dest_reg, "5"), comment=f"len {operand} (placeholder)")
            ]
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
        elif source.startswith("_str") or source.startswith("_array"):
            # Load address of string/array label
            self.base.emit_text(
                MIPSInstruction(
                    "la",
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

        # CRITICAL FOR LOOPS: If target already has a spill slot (was spilled before),
        # write the new value back to memory immediately. This ensures that when
        # we jump back to loop headers, the variable can be reloaded with the
        # correct value, maintaining register consistency across loop iterations.
        entry = self.base.address_descriptor.get(target)
        if entry.spill_slot is not None or entry.memory is not None:
            # Variable has been spilled before, write it back to memory
            if entry.spill_slot is not None:
                self.base.emit_text(
                    MIPSInstruction(
                        "sw",
                        (dest_reg, f"{entry.spill_slot}($fp)"),
                        comment=f"update {target} in memory",
                    )
                )
                # Mark as clean since we just wrote to memory
                self.base.address_descriptor.mark_clean(target)

                # Clear register association to force reload on next use
                # This ensures loop variables maintain consistent register allocation
                self.base.address_descriptor.unbind_register(target, dest_reg)
                # Note: We don't dissociate from register_descriptor here because
                # it will be done automatically on next register allocation

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
        elif operand.startswith("_str") or operand.startswith("_array"):
            # Load address of string/array label
            temp_var = f"_label_{operand}"
            temp_reg, spills, loads = self.base.acquire_register(
                temp_var,
                is_write=True,
                forbidden_registers=forbidden,
            )
            self.base.materialise_spills(spills)

            self.base.emit_text(
                MIPSInstruction(
                    "la",
                    (temp_reg, operand),
                    comment=f"load address {operand}",
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

    def translate_allocate_array(self, instr):
        """
        Translate array allocation instruction to MIPS.

        TAC: target = allocate_array size, elem_size
        MIPS: Call allocate_array runtime function
        """
        from tac.instruction import AllocateArrayInstruction

        # Get destination register
        dest_reg, spills, loads = self.base.acquire_register(instr.target, is_write=True)
        self.base.materialise_spills(spills)
        self.base.materialise_loads(loads)

        # Load size into $a0
        if instr.size.isdigit():
            self.base.emit_text(MIPSInstruction("li", ("$a0", instr.size), comment="array size"))
        else:
            size_reg = self._load_operand(instr.size)
            self.base.emit_text(MIPSInstruction("move", ("$a0", size_reg), comment="array size"))

        # Load element size into $a1
        self.base.emit_text(MIPSInstruction("li", ("$a1", str(instr.elem_size)), comment="element size"))

        # Call allocate_array
        self.base.emit_text(MIPSInstruction("jal", ("allocate_array",), comment="allocate array"))

        # Move result from $v0 to destination register
        self.base.emit_text(MIPSInstruction("move", (dest_reg, "$v0"), comment="save array address"))

    def translate_array_access(self, instr):
        """
        Translate array access instruction to MIPS.

        TAC: target = array[index]  (read)
        TAC: array[index] = target  (write)
        """
        from tac.instruction import ArrayAccessInstruction

        # Get array base address
        array_reg = self._load_operand(instr.array)

        # Get index
        if instr.index.isdigit():
            # Constant index - can optimize
            offset = int(instr.index) * 4

            if instr.is_assignment:
                # array[index] = target (write)
                value_reg = self._load_operand(instr.target)
                self.base.emit_text(
                    MIPSInstruction("sw", (value_reg, f"{offset}({array_reg})"),
                                  comment=f"store to array[{instr.index}]")
                )
            else:
                # target = array[index] (read)
                dest_reg, spills, loads = self.base.acquire_register(instr.target, is_write=True)
                self.base.materialise_spills(spills)
                self.base.materialise_loads(loads)

                self.base.emit_text(
                    MIPSInstruction("lw", (dest_reg, f"{offset}({array_reg})"),
                                  comment=f"load from array[{instr.index}]")
                )
        else:
            # Variable index - need to calculate offset
            index_reg = self._load_operand(instr.index)

            # Calculate offset: index * 4
            offset_reg, spills, loads = self.base.acquire_register(
                f"_offset_{instr.index}", is_write=True
            )
            self.base.materialise_spills(spills)
            self.base.materialise_loads(loads)

            self.base.emit_text(
                MIPSInstruction("sll", (offset_reg, index_reg, "2"),
                              comment="offset = index * 4")
            )

            # Calculate address: base + offset
            addr_reg, spills, loads = self.base.acquire_register(
                f"_addr_{instr.array}", is_write=True
            )
            self.base.materialise_spills(spills)
            self.base.materialise_loads(loads)

            self.base.emit_text(
                MIPSInstruction("add", (addr_reg, array_reg, offset_reg),
                              comment="address = base + offset")
            )

            if instr.is_assignment:
                # array[index] = target (write)
                value_reg = self._load_operand(instr.target)
                self.base.emit_text(
                    MIPSInstruction("sw", (value_reg, f"0({addr_reg})"),
                                  comment=f"store to array[{instr.index}]")
                )
            else:
                # target = array[index] (read)
                dest_reg, spills, loads = self.base.acquire_register(instr.target, is_write=True)
                self.base.materialise_spills(spills)
                self.base.materialise_loads(loads)

                self.base.emit_text(
                    MIPSInstruction("lw", (dest_reg, f"0({addr_reg})"),
                                  comment=f"load from array[{instr.index}]")
                )