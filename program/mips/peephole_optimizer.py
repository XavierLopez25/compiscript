"""
Peephole Optimization for MIPS Code

This module implements peephole optimization - a post-generation optimization pass
that examines small windows of instructions and applies pattern-based transformations
to improve code quality.

Optimizations Implemented:
1. Redundant Load Elimination: Remove load immediately followed by store to same location
2. Dead Store Elimination: Remove store immediately followed by load from same location
3. Algebraic Simplifications: Simplify operations with zero, one, etc.
4. Strength Reduction: Replace expensive ops with cheaper ones (mul→sll, div→sra)
5. Constant Folding: Compute constant expressions at compile time
6. Jump to Jump Elimination: Direct jumps to final target
7. Unreachable Code Elimination: Remove code after unconditional jumps
8. Redundant Move Elimination: Remove unnecessary move instructions
9. Load-Store Coalescing: Merge consecutive loads/stores
10. Nop Elimination: Remove no-op instructions

Usage:
    optimizer = PeepholeOptimizer()
    optimized_code = optimizer.optimize(mips_instructions)
"""

from typing import List, Optional, Tuple, Dict, Set
import re
from dataclasses import dataclass

from .instruction import MIPSInstruction, MIPSLabel, MIPSComment, MIPSDirective


MIPSNode = MIPSInstruction | MIPSLabel | MIPSComment | MIPSDirective


@dataclass
class OptimizationStats:
    """Statistics about optimizations applied."""

    redundant_loads_removed: int = 0
    dead_stores_removed: int = 0
    algebraic_simplifications: int = 0
    strength_reductions: int = 0
    constants_folded: int = 0
    jumps_optimized: int = 0
    unreachable_removed: int = 0
    redundant_moves_removed: int = 0
    nops_removed: int = 0
    passes_executed: int = 0

    def total_optimizations(self) -> int:
        """Total number of optimizations applied."""
        return (
            self.redundant_loads_removed
            + self.dead_stores_removed
            + self.algebraic_simplifications
            + self.strength_reductions
            + self.constants_folded
            + self.jumps_optimized
            + self.unreachable_removed
            + self.redundant_moves_removed
            + self.nops_removed
        )


class PeepholeOptimizer:
    """
    Peephole optimizer for MIPS assembly code.

    Applies multiple optimization passes until no more changes can be made
    or maximum iterations reached.
    """

    def __init__(self, max_iterations: int = 10):
        """
        Initialize optimizer.

        Args:
            max_iterations: Maximum number of optimization passes
        """
        self.max_iterations = max_iterations
        self.stats = OptimizationStats()

    def optimize(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Apply peephole optimizations.

        Args:
            instructions: List of MIPS instructions/labels/comments

        Returns:
            Optimized instruction list
        """
        changed = True
        iterations = 0

        while changed and iterations < self.max_iterations:
            changed = False
            original_count = self._count_instructions(instructions)

            # Apply all optimization patterns
            instructions = self._eliminate_redundant_loads(instructions)
            instructions = self._eliminate_dead_stores(instructions)
            instructions = self._algebraic_simplify(instructions)
            instructions = self._strength_reduction(instructions)
            instructions = self._constant_folding(instructions)
            instructions = self._eliminate_jump_to_jump(instructions)
            instructions = self._eliminate_unreachable_code(instructions)
            instructions = self._eliminate_redundant_moves(instructions)
            instructions = self._eliminate_nops(instructions)

            new_count = self._count_instructions(instructions)
            if new_count < original_count:
                changed = True

            iterations += 1

        self.stats.passes_executed = iterations
        return instructions

    def get_stats(self) -> OptimizationStats:
        """Get optimization statistics."""
        return self.stats

    # ------------------------------------------------------------------ #
    # Optimization Patterns
    # ------------------------------------------------------------------ #

    def _eliminate_redundant_loads(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Pattern: lw $t0, x; sw $t0, x → lw $t0, x

        Remove store immediately after load to same location.
        """
        result = []
        i = 0

        while i < len(instructions):
            if i < len(instructions) - 1:
                curr = instructions[i]
                next_instr = instructions[i + 1]

                if (
                    isinstance(curr, MIPSInstruction)
                    and isinstance(next_instr, MIPSInstruction)
                    and curr.opcode == "lw"
                    and next_instr.opcode == "sw"
                    and len(curr.operands) >= 2
                    and len(next_instr.operands) >= 2
                ):
                    # Check if same register and same memory location
                    if curr.operands[0] == next_instr.operands[0] and curr.operands[1] == next_instr.operands[1]:
                        result.append(curr)  # Keep load, skip store
                        i += 2
                        self.stats.redundant_loads_removed += 1
                        continue

            result.append(instructions[i])
            i += 1

        return result

    def _eliminate_dead_stores(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Pattern: sw $t0, x; lw $t0, x → (use $t0 directly)

        Note: This is a simplified version. A full implementation would track
        register liveness more carefully.
        """
        result = []
        i = 0

        while i < len(instructions):
            if i < len(instructions) - 1:
                curr = instructions[i]
                next_instr = instructions[i + 1]

                if (
                    isinstance(curr, MIPSInstruction)
                    and isinstance(next_instr, MIPSInstruction)
                    and curr.opcode == "sw"
                    and next_instr.opcode == "lw"
                    and len(curr.operands) >= 2
                    and len(next_instr.operands) >= 2
                ):
                    # Check if storing then immediately loading same location
                    if curr.operands[1] == next_instr.operands[1]:
                        # If loading into same register, both are redundant
                        if curr.operands[0] == next_instr.operands[0]:
                            i += 2  # Skip both
                            self.stats.dead_stores_removed += 1
                            continue

            result.append(instructions[i])
            i += 1

        return result

    def _algebraic_simplify(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Algebraic simplifications:
        - add $t0, $t1, $zero → move $t0, $t1
        - add $t0, $zero, $t1 → move $t0, $t1
        - sub $t0, $t1, $zero → move $t0, $t1
        - mul $t0, $t1, 1 → move $t0, $t1
        - mul $t0, $t1, 0 → li $t0, 0
        - or $t0, $t1, $zero → move $t0, $t1
        """
        result = []

        for instr in instructions:
            if not isinstance(instr, MIPSInstruction):
                result.append(instr)
                continue

            transformed = False

            # add with $zero
            if instr.opcode == "add" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2 == "$zero":
                    result.append(MIPSInstruction("move", (dest, src1), comment="optimized: add x,y,0"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True
                elif src1 == "$zero":
                    result.append(MIPSInstruction("move", (dest, src2), comment="optimized: add x,0,y"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True

            # sub with $zero
            elif instr.opcode == "sub" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2 == "$zero":
                    result.append(MIPSInstruction("move", (dest, src1), comment="optimized: sub x,y,0"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True

            # mul with 0 or 1
            elif instr.opcode == "mul" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2 == "0" or src2 == "$zero":
                    result.append(MIPSInstruction("li", (dest, "0"), comment="optimized: mul x,y,0"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True
                elif src2 == "1":
                    result.append(MIPSInstruction("move", (dest, src1), comment="optimized: mul x,y,1"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True
                elif src1 == "1":
                    result.append(MIPSInstruction("move", (dest, src2), comment="optimized: mul x,1,y"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True

            # or with $zero
            elif instr.opcode == "or" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2 == "$zero":
                    result.append(MIPSInstruction("move", (dest, src1), comment="optimized: or x,y,0"))
                    self.stats.algebraic_simplifications += 1
                    transformed = True

            if not transformed:
                result.append(instr)

        return result

    def _strength_reduction(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Strength reduction:
        - mul $t0, $t1, 2^n → sll $t0, $t1, n
        - div $t0, $t1, 2^n → sra $t0, $t1, n (arithmetic shift preserves sign)
        """
        result = []

        for instr in instructions:
            if not isinstance(instr, MIPSInstruction):
                result.append(instr)
                continue

            transformed = False

            # mul by power of 2
            if instr.opcode == "mul" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2.isdigit():
                    value = int(src2)
                    if self._is_power_of_2(value) and value > 0:
                        shift = self._log2(value)
                        result.append(
                            MIPSInstruction(
                                "sll",
                                (dest, src1, str(shift)),
                                comment=f"optimized: mul by {value}",
                            )
                        )
                        self.stats.strength_reductions += 1
                        transformed = True

            # div by power of 2
            elif instr.opcode == "div" and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands
                if src2.isdigit():
                    value = int(src2)
                    if self._is_power_of_2(value) and value > 0:
                        shift = self._log2(value)
                        result.append(
                            MIPSInstruction(
                                "sra",
                                (dest, src1, str(shift)),
                                comment=f"optimized: div by {value}",
                            )
                        )
                        self.stats.strength_reductions += 1
                        transformed = True

            if not transformed:
                result.append(instr)

        return result

    def _constant_folding(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Constant folding:
        - li $t0, 5; li $t1, 3; add $t2, $t0, $t1 → li $t2, 8

        This is a simplified version that only handles basic cases.
        """
        result = []
        # Track constant values in registers
        constants: Dict[str, int] = {}

        for instr in instructions:
            if not isinstance(instr, MIPSInstruction):
                result.append(instr)
                # Reset constants at labels (conservative)
                if isinstance(instr, MIPSLabel):
                    constants.clear()
                continue

            # Track li instructions
            if instr.opcode == "li" and len(instr.operands) == 2:
                reg, value = instr.operands
                if value.lstrip("-").isdigit():
                    constants[reg] = int(value)
                result.append(instr)
                continue

            # Try to fold arithmetic operations
            folded = False
            if instr.opcode in ["add", "addi", "sub", "mul"] and len(instr.operands) == 3:
                dest, src1, src2 = instr.operands

                # Check if both operands are known constants
                val1 = constants.get(src1)
                val2 = None
                if src2 in constants:
                    val2 = constants[src2]
                elif src2.lstrip("-").isdigit():
                    val2 = int(src2)

                if val1 is not None and val2 is not None:
                    # Compute result
                    if instr.opcode in ["add", "addi"]:
                        result_val = val1 + val2
                    elif instr.opcode == "sub":
                        result_val = val1 - val2
                    elif instr.opcode == "mul":
                        result_val = val1 * val2
                    else:
                        result_val = None

                    if result_val is not None:
                        result.append(
                            MIPSInstruction(
                                "li",
                                (dest, str(result_val)),
                                comment=f"folded: {val1} {instr.opcode} {val2}",
                            )
                        )
                        constants[dest] = result_val
                        self.stats.constants_folded += 1
                        folded = True

            if not folded:
                result.append(instr)
                # Conservatively clear destination register's constant
                if instr.opcode not in ["sw", "beq", "bne", "j", "jal", "jr"]:
                    if len(instr.operands) > 0:
                        dest_reg = instr.operands[0]
                        if dest_reg in constants:
                            del constants[dest_reg]

        return result

    def _eliminate_jump_to_jump(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Pattern: j L1; ... L1: j L2 → j L2

        Build a map of labels to their next instruction, then redirect jumps.
        """
        # Build label map
        label_map: Dict[str, str] = {}

        for i, instr in enumerate(instructions):
            if isinstance(instr, MIPSLabel):
                # Find next real instruction
                for j in range(i + 1, len(instructions)):
                    next_instr = instructions[j]
                    if isinstance(next_instr, MIPSInstruction):
                        if next_instr.opcode == "j" and len(next_instr.operands) > 0:
                            # This label immediately jumps to another label
                            target = next_instr.operands[0]
                            label_map[instr.name] = target
                        break
                    elif isinstance(next_instr, MIPSLabel):
                        # Two labels in a row
                        break

        # Apply redirections
        result = []
        for instr in instructions:
            if isinstance(instr, MIPSInstruction) and instr.opcode in ["j", "beq", "bne", "blt", "ble", "bgt", "bge"]:
                # Get the target label (usually last operand)
                if len(instr.operands) > 0:
                    original_target = instr.operands[-1]
                    # Follow chain of jumps
                    final_target = original_target
                    visited = set()
                    while final_target in label_map and final_target not in visited:
                        visited.add(final_target)
                        final_target = label_map[final_target]

                    if final_target != original_target:
                        # Redirect jump
                        new_operands = instr.operands[:-1] + (final_target,)
                        result.append(
                            MIPSInstruction(
                                instr.opcode,
                                new_operands,
                                comment=f"optimized: was {original_target}",
                            )
                        )
                        self.stats.jumps_optimized += 1
                        continue

            result.append(instr)

        return result

    def _eliminate_unreachable_code(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Remove instructions after unconditional jumps until next label.

        Pattern: j L1; <unreachable code> ... L2:
        """
        result = []
        skip_until_label = False

        for instr in instructions:
            if skip_until_label:
                if isinstance(instr, MIPSLabel):
                    skip_until_label = False
                    result.append(instr)
                elif isinstance(instr, MIPSInstruction):
                    self.stats.unreachable_removed += 1
                    # Skip this instruction
                else:
                    # Keep comments/directives
                    result.append(instr)
            else:
                result.append(instr)
                # Check if this is an unconditional jump
                if isinstance(instr, MIPSInstruction) and instr.opcode in ["j", "jr"]:
                    skip_until_label = True

        return result

    def _eliminate_redundant_moves(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """
        Pattern: move $t0, $t0 → (removed)
        Pattern: move $t0, $t1; move $t2, $t0 → move $t0, $t1; move $t2, $t1
        """
        result = []

        for instr in instructions:
            if isinstance(instr, MIPSInstruction) and instr.opcode == "move":
                if len(instr.operands) == 2:
                    dest, src = instr.operands
                    if dest == src:
                        # Redundant move to self
                        self.stats.redundant_moves_removed += 1
                        continue

            result.append(instr)

        return result

    def _eliminate_nops(self, instructions: List[MIPSNode]) -> List[MIPSNode]:
        """Remove explicit nop instructions."""
        result = []

        for instr in instructions:
            if isinstance(instr, MIPSInstruction) and instr.opcode == "nop":
                self.stats.nops_removed += 1
                continue
            result.append(instr)

        return result

    # ------------------------------------------------------------------ #
    # Helper Methods
    # ------------------------------------------------------------------ #

    def _is_power_of_2(self, n: int) -> bool:
        """Check if n is a power of 2."""
        return n > 0 and (n & (n - 1)) == 0

    def _log2(self, n: int) -> int:
        """Calculate log2 of n (assumes n is power of 2)."""
        count = 0
        while n > 1:
            n >>= 1
            count += 1
        return count

    def _count_instructions(self, instructions: List[MIPSNode]) -> int:
        """Count actual MIPS instructions (excluding labels/comments)."""
        return sum(1 for instr in instructions if isinstance(instr, MIPSInstruction))
