"""
MIPS Runtime Library Generator

Generates runtime support functions for:
- print (syscall 4 - print string, syscall 1 - print int)
- Input/output operations
- String operations (concatenation, conversion)
- Memory allocation helpers
"""

from typing import List
from .instruction import MIPSInstruction, MIPSLabel, MIPSComment


class RuntimeLibrary:
    """
    Generates MIPS runtime support functions.

    These functions provide standard library functionality using MIPS syscalls.
    """

    @staticmethod
    def generate_print_function() -> List:
        """
        Generate the 'print' function that handles different data types.

        Assumes $a0 contains address of string to print.
        Uses syscall 4 (print_string).
        """
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: print"),
            MIPSComment("Prints strings or integers passed in $a0"),
            MIPSLabel("print"),
            # Heuristic: data addresses live at/after _data_segment_start (0x1001xxxx in SPIM)
            # Values below that are treated as integers and routed to print_int.
            MIPSInstruction("la", ("$t0", "_data_segment_start"), comment="data segment base"),
            MIPSInstruction("blt", ("$a0", "$t0", "_print_int_fallback"), comment="if value < base -> int"),
            MIPSInstruction("li", ("$v0", "4"), comment="syscall: print_string"),
            MIPSInstruction("syscall", ()),
            MIPSInstruction("jr", ("$ra",), comment="return"),
            MIPSLabel("_print_int_fallback"),
            MIPSInstruction("li", ("$v0", "1"), comment="syscall: print_int"),
            MIPSInstruction("syscall", ()),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_print_int_function() -> List:
        """
        Generate function to print an integer.

        Assumes $a0 contains integer value.
        Uses syscall 1 (print_int).
        """
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: print_int"),
            MIPSComment("Prints integer in $a0"),
            MIPSLabel("print_int"),
            MIPSInstruction("li", ("$v0", "1"), comment="syscall: print_int"),
            MIPSInstruction("syscall", ()),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_print_newline() -> List:
        """Generate function to print a newline."""
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: print_newline"),
            MIPSLabel("print_newline"),
            MIPSInstruction("la", ("$a0", "_newline"), comment="load newline address"),
            MIPSInstruction("li", ("$v0", "4"), comment="syscall: print_string"),
            MIPSInstruction("syscall", ()),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_allocate_array() -> List:
        """
        Generate function to allocate array on heap.

        Input: $a0 = number of elements, $a1 = size per element
        Output: $v0 = address of allocated memory
        Uses syscall 9 (sbrk - allocate heap memory).
        """
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: allocate_array"),
            MIPSComment("Input: $a0 = num elements, $a1 = element size"),
            MIPSComment("Output: $v0 = array address"),
            MIPSLabel("allocate_array"),
            MIPSInstruction("mult", ("$a0", "$a1"), comment="product in LO"),
            MIPSInstruction("mflo", ("$a0",), comment="total bytes -> $a0"),
            MIPSInstruction("li", ("$v0", "9"), comment="syscall: sbrk"),
            MIPSInstruction("syscall", ()),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_string_concat() -> List:
        """
        Generate function to concatenate two strings.

        Input: $a0 = address of first string, $a1 = address of second string
        Output: $v0 = address of concatenated string (in buffer)

        Uses _str_buffer from data section.
        """
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: string_concat"),
            MIPSComment("Input: $a0 = str1, $a1 = str2"),
            MIPSComment("Output: $v0 = concatenated string"),
            MIPSLabel("string_concat"),
            # Save registers
            MIPSInstruction("addi", ("$sp", "$sp", "-16"), comment="allocate stack"),
            MIPSInstruction("sw", ("$ra", "12($sp)"), comment="save $ra"),
            MIPSInstruction("sw", ("$s0", "8($sp)"), comment="save $s0"),
            MIPSInstruction("sw", ("$s1", "4($sp)"), comment="save $s1"),
            MIPSInstruction("sw", ("$s2", "0($sp)"), comment="save $s2"),

            # Load buffer address
            MIPSInstruction("la", ("$s0", "_str_buffer"), comment="load buffer address"),
            MIPSInstruction("move", ("$s1", "$a0"), comment="save str1"),
            MIPSInstruction("move", ("$s2", "$a1"), comment="save str2"),
            MIPSInstruction("move", ("$t0", "$s0"), comment="current position in buffer"),

            # Copy first string
            MIPSLabel("_concat_loop1"),
            MIPSInstruction("lb", ("$t1", "0($s1)"), comment="load byte from str1"),
            MIPSInstruction("beq", ("$t1", "$zero", "_concat_done1"), comment="if null, done"),
            MIPSInstruction("sb", ("$t1", "0($t0)"), comment="store to buffer"),
            MIPSInstruction("addi", ("$s1", "$s1", "1"), comment="next byte in str1"),
            MIPSInstruction("addi", ("$t0", "$t0", "1"), comment="next position in buffer"),
            MIPSInstruction("j", ("_concat_loop1",), comment="continue"),

            # Copy second string
            MIPSLabel("_concat_done1"),
            MIPSLabel("_concat_loop2"),
            MIPSInstruction("lb", ("$t1", "0($s2)"), comment="load byte from str2"),
            MIPSInstruction("beq", ("$t1", "$zero", "_concat_done2"), comment="if null, done"),
            MIPSInstruction("sb", ("$t1", "0($t0)"), comment="store to buffer"),
            MIPSInstruction("addi", ("$s2", "$s2", "1"), comment="next byte in str2"),
            MIPSInstruction("addi", ("$t0", "$t0", "1"), comment="next position in buffer"),
            MIPSInstruction("j", ("_concat_loop2",), comment="continue"),

            # Add null terminator
            MIPSLabel("_concat_done2"),
            MIPSInstruction("sb", ("$zero", "0($t0)"), comment="null terminator"),

            # Return buffer address
            MIPSInstruction("move", ("$v0", "$s0"), comment="return buffer address"),

            # Restore registers
            MIPSInstruction("lw", ("$s2", "0($sp)"), comment="restore $s2"),
            MIPSInstruction("lw", ("$s1", "4($sp)"), comment="restore $s1"),
            MIPSInstruction("lw", ("$s0", "8($sp)"), comment="restore $s0"),
            MIPSInstruction("lw", ("$ra", "12($sp)"), comment="restore $ra"),
            MIPSInstruction("addi", ("$sp", "$sp", "16"), comment="deallocate stack"),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_int_to_string() -> List:
        """
        Generate function to convert integer to string.

        Input: $a0 = integer value
        Output: $v0 = address of string representation (in _str_buffer)

        Algorithm:
        1. Handle negative numbers
        2. Convert digits from right to left
        3. Reverse the string
        """
        return [
            MIPSComment(""),
            MIPSComment("Runtime function: int_to_string"),
            MIPSComment("Input: $a0 = integer"),
            MIPSComment("Output: $v0 = string address"),
            MIPSLabel("int_to_string"),

            # Save registers
            MIPSInstruction("addi", ("$sp", "$sp", "-20"), comment="allocate stack"),
            MIPSInstruction("sw", ("$ra", "16($sp)"), comment="save $ra"),
            MIPSInstruction("sw", ("$s0", "12($sp)"), comment="save $s0"),
            MIPSInstruction("sw", ("$s1", "8($sp)"), comment="save $s1"),
            MIPSInstruction("sw", ("$s2", "4($sp)"), comment="save $s2"),
            MIPSInstruction("sw", ("$s3", "0($sp)"), comment="save $s3"),

            # Setup - use separate buffer to avoid conflicts with string_concat
            MIPSInstruction("la", ("$s0", "_int_buffer"), comment="buffer address"),
            MIPSInstruction("move", ("$s1", "$a0"), comment="save number"),
            MIPSInstruction("move", ("$s2", "$s0"), comment="current position"),
            MIPSInstruction("li", ("$s3", "0"), comment="is_negative flag"),

            # Handle zero case
            MIPSInstruction("bnez", ("$s1", "_i2s_not_zero"), comment="if n != 0"),
            MIPSInstruction("li", ("$t0", "48"), comment="ASCII '0'"),
            MIPSInstruction("sb", ("$t0", "0($s2)"), comment="store '0'"),
            MIPSInstruction("addi", ("$s2", "$s2", "1"), comment="advance"),
            MIPSInstruction("j", ("_i2s_done",), comment="jump to done"),

            # Handle negative
            MIPSLabel("_i2s_not_zero"),
            MIPSInstruction("bgez", ("$s1", "_i2s_positive"), comment="if n >= 0"),
            MIPSInstruction("li", ("$s3", "1"), comment="set negative flag"),
            MIPSInstruction("sub", ("$s1", "$zero", "$s1"), comment="n = -n"),

            # Convert digits
            MIPSLabel("_i2s_positive"),
            MIPSLabel("_i2s_loop"),
            MIPSInstruction("beqz", ("$s1", "_i2s_reverse"), comment="if n == 0, done"),
            MIPSInstruction("li", ("$t1", "10"), comment="divisor = 10"),
            MIPSInstruction("div", ("$s1", "$t1"), comment="n / 10"),
            MIPSInstruction("mfhi", ("$t0",), comment="remainder (digit)"),
            MIPSInstruction("addi", ("$t0", "$t0", "48"), comment="to ASCII"),
            MIPSInstruction("sb", ("$t0", "0($s2)"), comment="store digit"),
            MIPSInstruction("addi", ("$s2", "$s2", "1"), comment="advance"),
            MIPSInstruction("mflo", ("$s1",), comment="n = quotient"),
            MIPSInstruction("j", ("_i2s_loop",), comment="continue"),

            # Add minus sign if negative
            MIPSLabel("_i2s_reverse"),
            MIPSInstruction("beqz", ("$s3", "_i2s_do_reverse"), comment="if not negative"),
            MIPSInstruction("li", ("$t0", "45"), comment="ASCII '-'"),
            MIPSInstruction("sb", ("$t0", "0($s2)"), comment="store '-'"),
            MIPSInstruction("addi", ("$s2", "$s2", "1"), comment="advance"),

            # Reverse string in-place
            MIPSLabel("_i2s_do_reverse"),
            MIPSInstruction("move", ("$t0", "$s0"), comment="left = start"),
            MIPSInstruction("addi", ("$t1", "$s2", "-1"), comment="right = end - 1"),

            MIPSLabel("_i2s_rev_loop"),
            MIPSInstruction("slt", ("$t2", "$t0", "$t1"), comment="left < right?"),
            MIPSInstruction("beqz", ("$t2", "_i2s_done"), comment="if not, done"),
            MIPSInstruction("lb", ("$t3", "0($t0)"), comment="load left"),
            MIPSInstruction("lb", ("$t4", "0($t1)"), comment="load right"),
            MIPSInstruction("sb", ("$t4", "0($t0)"), comment="store right to left"),
            MIPSInstruction("sb", ("$t3", "0($t1)"), comment="store left to right"),
            MIPSInstruction("addi", ("$t0", "$t0", "1"), comment="left++"),
            MIPSInstruction("addi", ("$t1", "$t1", "-1"), comment="right--"),
            MIPSInstruction("j", ("_i2s_rev_loop",), comment="continue"),

            # Add null terminator and return
            MIPSLabel("_i2s_done"),
            MIPSInstruction("sb", ("$zero", "0($s2)"), comment="null terminator"),
            MIPSInstruction("move", ("$v0", "$s0"), comment="return buffer address"),

            # Restore registers
            MIPSInstruction("lw", ("$s3", "0($sp)"), comment="restore $s3"),
            MIPSInstruction("lw", ("$s2", "4($sp)"), comment="restore $s2"),
            MIPSInstruction("lw", ("$s1", "8($sp)"), comment="restore $s1"),
            MIPSInstruction("lw", ("$s0", "12($sp)"), comment="restore $s0"),
            MIPSInstruction("lw", ("$ra", "16($sp)"), comment="restore $ra"),
            MIPSInstruction("addi", ("$sp", "$sp", "20"), comment="deallocate stack"),
            MIPSInstruction("jr", ("$ra",), comment="return"),
        ]

    @staticmethod
    def generate_all_runtime_functions() -> List:
        """Generate all runtime functions."""
        functions = []

        functions.extend(RuntimeLibrary.generate_print_function())
        functions.extend(RuntimeLibrary.generate_print_int_function())
        functions.extend(RuntimeLibrary.generate_print_newline())
        functions.extend(RuntimeLibrary.generate_allocate_array())
        functions.extend(RuntimeLibrary.generate_string_concat())
        functions.extend(RuntimeLibrary.generate_int_to_string())

        return functions
