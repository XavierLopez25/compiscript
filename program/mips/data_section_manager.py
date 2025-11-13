"""
Data Section Manager for MIPS Code Generation

Manages string literals, array declarations, and other data section elements.
Automatically generates labels and handles escaping for MIPS assembly.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from .instruction import MIPSDirective, MIPSLabel, MIPSComment


@dataclass
class StringLiteral:
    """Represents a string literal in the data section."""
    label: str
    value: str

    def to_directive(self) -> MIPSDirective:
        """Convert to MIPS .asciiz directive."""
        # Escape special characters for MIPS
        escaped = self._escape_string(self.value)
        return MIPSDirective(".asciiz", (f'"{escaped}"',))

    def _escape_string(self, s: str) -> str:
        """Escape special characters for MIPS assembly."""
        # Replace common escape sequences
        s = s.replace('\\', '\\\\')  # Backslash
        s = s.replace('"', '\\"')    # Quote
        s = s.replace('\n', '\\n')   # Newline
        s = s.replace('\t', '\\t')   # Tab
        s = s.replace('\r', '\\r')   # Carriage return
        return s


@dataclass
class ArrayDeclaration:
    """Represents an array declaration in the data section."""
    label: str
    size: int
    element_size: int = 4  # Default: 4 bytes (word)

    def to_directive(self) -> MIPSDirective:
        """Convert to MIPS .space directive."""
        total_bytes = self.size * self.element_size
        return MIPSDirective(".space", (str(total_bytes),))


class DataSectionManager:
    """
    Manages the .data section of MIPS assembly.

    Responsibilities:
    - Track string literals and generate unique labels
    - Handle array declarations
    - Generate .data section directives
    - Provide lookup for literals by value or label
    """

    def __init__(self):
        self.string_literals: Dict[str, StringLiteral] = {}  # value -> StringLiteral
        self.string_labels: Dict[str, str] = {}  # label -> value
        self.arrays: Dict[str, ArrayDeclaration] = {}
        self.string_counter = 0
        self.array_counter = 0

    def add_string_literal(self, value: str) -> str:
        """
        Add a string literal to the data section.
        Returns the label for this string.

        If the string already exists, returns its existing label.

        Args:
            value: The string value (may include quotes from TAC)

        Returns:
            Label name (e.g., "_str0", "_str1")
        """
        # Strip quotes if present (from TAC generator)
        clean_value = value
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            clean_value = value[1:-1]

        # Check if we already have this string
        if clean_value in self.string_literals:
            return self.string_literals[clean_value].label

        # Generate new label
        label = f"_str{self.string_counter}"
        self.string_counter += 1

        # Create literal with cleaned value
        literal = StringLiteral(label, clean_value)
        self.string_literals[clean_value] = literal
        self.string_labels[label] = clean_value

        return label

    def add_array(self, size: int, element_size: int = 4) -> str:
        """
        Add an array declaration to the data section.
        Returns the label for this array.

        Args:
            size: Number of elements
            element_size: Size of each element in bytes

        Returns:
            Label name (e.g., "_array0", "_array1")
        """
        label = f"_array{self.array_counter}"
        self.array_counter += 1

        array_decl = ArrayDeclaration(label, size, element_size)
        self.arrays[label] = array_decl

        return label

    def get_string_label(self, value: str) -> Optional[str]:
        """Get the label for a string value if it exists."""
        literal = self.string_literals.get(value)
        return literal.label if literal else None

    def generate_data_section(self) -> List:
        """
        Generate the complete .data section.

        Returns:
            List of MIPS nodes (directives, labels, comments)
        """
        nodes = []

        # Add .data directive and segment anchor
        nodes.append(MIPSDirective(".data", ()))
        nodes.append(MIPSLabel("_data_segment_start"))
        nodes.append(MIPSComment("String literals"))

        # Add string literals
        for literal in sorted(self.string_literals.values(), key=lambda x: x.label):
            nodes.append(MIPSLabel(literal.label))
            nodes.append(literal.to_directive())

        # Add arrays
        if self.arrays:
            nodes.append(MIPSComment(""))
            nodes.append(MIPSComment("Array declarations"))
            for label, array_decl in sorted(self.arrays.items()):
                nodes.append(MIPSLabel(label))
                nodes.append(array_decl.to_directive())

        # Add newline buffer for I/O
        nodes.append(MIPSComment(""))
        nodes.append(MIPSComment("Newline for output"))
        nodes.append(MIPSLabel("_newline"))
        nodes.append(MIPSDirective(".asciiz", ('"\\n"',)))

        # Add space for string concatenation buffer (1KB)
        nodes.append(MIPSComment(""))
        nodes.append(MIPSComment("Buffer for string concatenation"))
        nodes.append(MIPSLabel("_str_buffer"))
        nodes.append(MIPSDirective(".space", ("1024",)))

        # Add separate buffer for int_to_string (256 bytes - enough for any integer)
        nodes.append(MIPSComment(""))
        nodes.append(MIPSComment("Buffer for int to string conversion"))
        nodes.append(MIPSLabel("_int_buffer"))
        nodes.append(MIPSDirective(".space", ("256",)))

        return nodes

    def is_string_literal(self, value: str) -> bool:
        """Check if a value looks like a string literal (not a variable name)."""
        # String literals typically contain spaces, special chars, or are quoted
        if not value:
            return False

        # Already a label
        if value.startswith("_str"):
            return False

        # Check if it's quoted (from TAC generator)
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return True

        # Check if it's a simple variable name (alphanumeric + underscore)
        if value.replace("_", "").isalnum():
            # Could be variable, but check for common string patterns
            if any(c in value for c in [' ', ',', '.', '!', '?', ':', '-']):
                return True
            return False

        return True
