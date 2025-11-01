from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple


def _format_operands(operands: Iterable[str]) -> str:
    operands = tuple(str(op) for op in operands if op is not None)
    return ", ".join(operands)


@dataclass(frozen=True)
class MIPSInstruction:
    """
    Representation of a single MIPS instruction.

    The instruction stores the opcode and its operands in textual form so the
    translator can stay agnostic of specific instruction formats (R/I/J).  This
    mirrors how most educational MIPS assemblers accept input, while still
    giving us a structured object to introspect during optimisations.
    """

    opcode: str
    operands: Tuple[str, ...] = field(default_factory=tuple)
    comment: Optional[str] = None

    def with_comment(self, comment: Optional[str]) -> "MIPSInstruction":
        """Return a copy of the instruction with the supplied comment."""
        return MIPSInstruction(self.opcode, self.operands, comment)

    def __str__(self) -> str:
        operands_txt = _format_operands(self.operands)
        base = f"\t{self.opcode}"
        if operands_txt:
            base = f"{base} {operands_txt}"
        if self.comment:
            padding = " " * max(1, 24 - len(base))
            return f"{base}{padding}# {self.comment}"
        return base


@dataclass(frozen=True)
class MIPSLabel:
    """Represents a label definition."""

    name: str

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass(frozen=True)
class MIPSDirective:
    """Represents an assembler directive (e.g., `.data`, `.word 1`)."""

    directive: str
    operands: Tuple[str, ...] = field(default_factory=tuple)
    comment: Optional[str] = None

    def __str__(self) -> str:
        operands_txt = _format_operands(self.operands)
        base = f"\t{self.directive}"
        if operands_txt:
            base = f"{base} {operands_txt}"
        if self.comment:
            padding = " " * max(1, 24 - len(base))
            return f"{base}{padding}# {self.comment}"
        return base


@dataclass(frozen=True)
class MIPSComment:
    """Represents a standalone comment line."""

    text: str

    def __str__(self) -> str:
        return f"# {self.text}"
