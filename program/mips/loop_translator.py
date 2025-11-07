"""
Loop-specific optimizations for MIPS code generation.

This module provides utilities and optimizations for handling loop constructs
that are already lowered to TAC goto/conditional-goto/label instructions.

While TAC has already converted high-level loops (while, for, foreach) into
goto-based control flow, this module helps identify loop patterns and apply
loop-specific optimizations.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class LoopInfo:
    """
    Information about a detected loop structure.

    Attributes:
        header_label: The label at the loop entry point
        exit_label: The label after the loop
        continue_label: The label for continue statements (optional)
        loop_type: Type of loop (while, for, do-while, foreach, unknown)
        body_labels: Set of labels within the loop body
    """

    header_label: str
    exit_label: str
    continue_label: Optional[str] = None
    loop_type: str = "unknown"
    body_labels: Set[str] = None

    def __post_init__(self):
        if self.body_labels is None:
            self.body_labels = set()


class LoopPatternDetector:
    """
    Detects loop patterns in TAC instruction sequences.

    This class analyzes TAC labels and gotos to identify loop structures
    based on common naming patterns:
    - while_start/while_end
    - for_cond/for_update/for_end
    - do_start/do_cond/do_end
    - foreach_start/foreach_continue/foreach_end
    """

    def __init__(self):
        self._detected_loops: Dict[str, LoopInfo] = {}

    def detect_while_loop(self, label: str) -> Optional[LoopInfo]:
        """
        Detect if a label marks the start of a while loop.

        Pattern:
            while_startN:
                if cond == 0 goto while_endM
                ... body ...
                goto while_startN
            while_endM:

        Args:
            label: The label to check

        Returns:
            LoopInfo if this is a while loop start, None otherwise
        """
        if label.startswith("while_start"):
            # Extract number: while_start1 → 1
            try:
                num = label.replace("while_start", "")
                exit_label = f"while_end{num}"
                return LoopInfo(
                    header_label=label,
                    exit_label=exit_label,
                    loop_type="while",
                )
            except ValueError:
                pass
        return None

    def detect_for_loop(self, label: str) -> Optional[LoopInfo]:
        """
        Detect if a label marks part of a for loop.

        Pattern:
            for_condN:
                if cond == 0 goto for_endM
                ... body ...
                goto for_updateK
            for_updateK:
                ... update ...
                goto for_condN
            for_endM:

        Args:
            label: The label to check

        Returns:
            LoopInfo if this is a for loop condition label, None otherwise
        """
        if label.startswith("for_cond"):
            try:
                num = label.replace("for_cond", "")
                exit_label = f"for_end{num}"
                continue_label = f"for_update{num}"
                return LoopInfo(
                    header_label=label,
                    exit_label=exit_label,
                    continue_label=continue_label,
                    loop_type="for",
                )
            except ValueError:
                pass
        return None

    def detect_do_while_loop(self, label: str) -> Optional[LoopInfo]:
        """
        Detect if a label marks the start of a do-while loop.

        Pattern:
            do_startN:
                ... body ...
            do_condM:
                if cond != 0 goto do_startN
            do_endK:

        Args:
            label: The label to check

        Returns:
            LoopInfo if this is a do-while loop start, None otherwise
        """
        if label.startswith("do_start"):
            try:
                num = label.replace("do_start", "")
                exit_label = f"do_end{num}"
                return LoopInfo(
                    header_label=label, exit_label=exit_label, loop_type="do-while"
                )
            except ValueError:
                pass
        return None

    def detect_foreach_loop(self, label: str) -> Optional[LoopInfo]:
        """
        Detect if a label marks the start of a foreach loop.

        Pattern:
            foreach_startN:
                if index >= length goto foreach_endM
                ... body ...
                goto foreach_continueK
            foreach_continueK:
                index = index + 1
                goto foreach_startN
            foreach_endM:

        Args:
            label: The label to check

        Returns:
            LoopInfo if this is a foreach loop start, None otherwise
        """
        if label.startswith("foreach_start"):
            try:
                num = label.replace("foreach_start", "")
                exit_label = f"foreach_end{num}"
                continue_label = f"foreach_continue{num}"
                return LoopInfo(
                    header_label=label,
                    exit_label=exit_label,
                    continue_label=continue_label,
                    loop_type="foreach",
                )
            except ValueError:
                pass
        return None

    def detect_loop(self, label: str) -> Optional[LoopInfo]:
        """
        Detect any loop pattern for the given label.

        Args:
            label: The label to analyze

        Returns:
            LoopInfo if a loop pattern is detected, None otherwise
        """
        # Try each loop pattern detector
        for detector in [
            self.detect_while_loop,
            self.detect_for_loop,
            self.detect_do_while_loop,
            self.detect_foreach_loop,
        ]:
            loop_info = detector(label)
            if loop_info:
                self._detected_loops[label] = loop_info
                return loop_info
        return None

    def get_loop_info(self, label: str) -> Optional[LoopInfo]:
        """
        Get information about a previously detected loop.

        Args:
            label: The loop header label

        Returns:
            LoopInfo if the loop was detected, None otherwise
        """
        return self._detected_loops.get(label)

    def is_loop_header(self, label: str) -> bool:
        """
        Check if a label is a loop header.

        Args:
            label: The label to check

        Returns:
            True if this label is a loop header
        """
        return label in self._detected_loops

    def is_loop_exit(self, label: str) -> bool:
        """
        Check if a label is a loop exit.

        Args:
            label: The label to check

        Returns:
            True if this label is a loop exit
        """
        for loop_info in self._detected_loops.values():
            if loop_info.exit_label == label:
                return True
        return False

    def get_all_loops(self) -> List[LoopInfo]:
        """
        Get all detected loops.

        Returns:
            List of all detected LoopInfo objects
        """
        return list(self._detected_loops.values())


class LoopOptimizer:
    """
    Applies loop-specific optimizations.

    Potential optimizations:
    - Loop unrolling (for small constant-iteration loops)
    - Strength reduction in loop bodies
    - Loop-invariant code motion detection
    - Branch optimization for loop conditions
    """

    def __init__(self):
        self.detector = LoopPatternDetector()

    def generate_loop_comment(self, loop_info: LoopInfo) -> str:
        """
        Generate a descriptive comment for a loop.

        Args:
            loop_info: Information about the loop

        Returns:
            A comment string describing the loop
        """
        loop_type = loop_info.loop_type.upper()
        return f"Begin {loop_type} loop: {loop_info.header_label}"

    def generate_exit_comment(self, loop_info: LoopInfo) -> str:
        """
        Generate a comment for a loop exit.

        Args:
            loop_info: Information about the loop

        Returns:
            A comment string for the loop exit
        """
        loop_type = loop_info.loop_type.upper()
        return f"End {loop_type} loop: {loop_info.exit_label}"

    def should_unroll_loop(self, loop_info: LoopInfo, iterations: int = -1) -> bool:
        """
        Determine if a loop should be unrolled.

        Args:
            loop_info: Information about the loop
            iterations: Number of iterations (if known at compile time)

        Returns:
            True if the loop should be unrolled
        """
        # Only unroll if we know the iteration count and it's small
        # This is a conservative heuristic - typically unroll for <= 4 iterations
        return 0 < iterations <= 4

    def detect_loop_invariants(
        self, loop_info: LoopInfo, instructions: List
    ) -> List[str]:
        """
        Detect loop-invariant computations.

        Loop-invariant code is code that:
        1. Produces the same result on every iteration
        2. Can be safely moved outside the loop

        Args:
            loop_info: Information about the loop
            instructions: List of instructions in the loop body

        Returns:
            List of variable names that are loop-invariant
        """
        # This is a placeholder for more sophisticated analysis
        # A full implementation would track:
        # - Which variables are modified in the loop
        # - Which computations depend only on non-modified variables
        # - Which computations can be safely hoisted
        invariants = []

        # TODO: Implement dataflow analysis for loop invariant detection
        # For now, we return an empty list as a conservative approach

        return invariants
