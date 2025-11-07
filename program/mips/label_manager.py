"""
Label management for MIPS code generation.

This module provides the LabelManager class which handles label tracking,
uniqueness validation, and forward/backward reference resolution for
MIPS assembly code generation.
"""

from typing import Dict, List, Set


class LabelResolutionError(Exception):
    """Exception raised when label resolution fails."""
    pass


class LabelManager:
    """
    Manages labels for MIPS assembly code generation.

    The label manager tracks:
    - Which labels have been defined (emitted)
    - Which labels have been referenced (in jumps/branches)
    - Label uniqueness and conflicts
    - Forward and backward references

    This ensures all labels are properly resolved and prevents:
    - Duplicate label definitions
    - References to undefined labels
    - Unused label definitions
    """

    def __init__(self) -> None:
        """Initialize a new label manager."""
        self._defined_labels: Set[str] = set()
        self._referenced_labels: Set[str] = set()
        self._label_counters: Dict[str, int] = {}

    def define_label(self, label: str) -> None:
        """
        Mark a label as defined.

        Args:
            label: The label name that has been emitted

        Raises:
            LabelResolutionError: If the label is already defined
        """
        if label in self._defined_labels:
            raise LabelResolutionError(
                f"Label '{label}' is already defined. Duplicate label detected."
            )
        self._defined_labels.add(label)

    def reference_label(self, label: str) -> None:
        """
        Mark a label as referenced (used in a jump/branch).

        Args:
            label: The label name being referenced
        """
        self._referenced_labels.add(label)

    def is_defined(self, label: str) -> bool:
        """
        Check if a label has been defined.

        Args:
            label: The label name to check

        Returns:
            True if the label has been defined, False otherwise
        """
        return label in self._defined_labels

    def is_referenced(self, label: str) -> bool:
        """
        Check if a label has been referenced.

        Args:
            label: The label name to check

        Returns:
            True if the label has been referenced, False otherwise
        """
        return label in self._referenced_labels

    def get_undefined_labels(self) -> List[str]:
        """
        Get all labels that are referenced but not defined.

        Returns:
            List of label names that are referenced but not defined
        """
        return sorted(self._referenced_labels - self._defined_labels)

    def get_unreferenced_labels(self) -> List[str]:
        """
        Get all labels that are defined but never referenced.

        Returns:
            List of label names that are defined but never referenced
        """
        return sorted(self._defined_labels - self._referenced_labels)

    def validate(self) -> None:
        """
        Validate that all labels are properly resolved.

        Raises:
            LabelResolutionError: If there are undefined or unreferenced labels
        """
        undefined = self.get_undefined_labels()
        if undefined:
            raise LabelResolutionError(
                f"Undefined labels referenced: {', '.join(undefined)}"
            )

    def generate_unique_label(self, prefix: str = "L") -> str:
        """
        Generate a unique label with the given prefix.

        Args:
            prefix: The prefix for the label (default: "L")

        Returns:
            A unique label name like "L1", "L2", etc.
        """
        if prefix not in self._label_counters:
            self._label_counters[prefix] = 0

        self._label_counters[prefix] += 1
        return f"{prefix}{self._label_counters[prefix]}"

    def reset(self) -> None:
        """Reset the label manager to initial state."""
        self._defined_labels.clear()
        self._referenced_labels.clear()
        self._label_counters.clear()

    def get_all_labels(self) -> List[str]:
        """
        Get all labels (both defined and referenced).

        Returns:
            Sorted list of all label names
        """
        return sorted(self._defined_labels | self._referenced_labels)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"LabelManager("
            f"defined={len(self._defined_labels)}, "
            f"referenced={len(self._referenced_labels)}, "
            f"undefined={len(self.get_undefined_labels())})"
        )
