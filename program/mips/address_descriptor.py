from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from tac.address_manager import MemoryLocation

WORD_SIZE = 4


@dataclass
class VariableLocation:
    """
    Tracks where a variable currently resides (registers and/or memory).

    The `memory` field stores the canonical memory home for the variable as
    provided by the TAC address manager, while `spill_slot` is used for values
    that must be written to the stack due to register pressure.
    """

    name: str
    registers: Set[str] = field(default_factory=set)
    memory: Optional[MemoryLocation] = None
    spill_slot: Optional[int] = None  # Offset from $sp reserved for spills
    dirty: bool = False

    def in_register(self) -> bool:
        return bool(self.registers)

    def is_in_memory(self) -> bool:
        return self.memory is not None or self.spill_slot is not None


class AddressDescriptor:
    """
    Maintains variable location metadata for register allocation.

    The descriptor mirrors the classic compiler design structure: for each
    variable we know which registers currently hold it as well as the memory
    location that should be considered authoritative.  This allows the register
    allocator to make informed spilling decisions and to avoid redundant loads.
    """

    def __init__(self) -> None:
        self._locations: Dict[str, VariableLocation] = {}
        self._spill_offsets: Dict[str, int] = {}
        self._next_spill_offset = 0
        self._max_spill_offset = 0

    def reset(self) -> None:
        """Reset all tracked state."""
        self._locations.clear()
        self._spill_offsets.clear()
        self._next_spill_offset = 0
        self._max_spill_offset = 0

    def get(self, name: str) -> VariableLocation:
        """Retrieve (and lazily create) the descriptor entry for a variable."""
        if name not in self._locations:
            self._locations[name] = VariableLocation(name=name)
        return self._locations[name]

    def bind_memory(self, name: str, location: MemoryLocation) -> None:
        """Associate a canonical memory location with the variable."""
        entry = self.get(name)
        entry.memory = location

    def bind_register(self, name: str, register: str) -> None:
        """Record that a variable resides in a given register."""
        entry = self.get(name)
        entry.registers.add(register)

    def unbind_register(self, name: str, register: str) -> None:
        """Remove register association from a variable."""
        if name not in self._locations:
            return
        entry = self._locations[name]
        entry.registers.discard(register)

    def mark_dirty(self, name: str) -> None:
        """Mark the variable value as dirty (needing a store to memory)."""
        self.get(name).dirty = True

    def mark_clean(self, name: str) -> None:
        """Mark the variable value as clean (synced with memory)."""
        if name in self._locations:
            self._locations[name].dirty = False

    def ensure_spill_slot(self, name: str) -> int:
        """
        Ensure there is a spill slot reserved for the variable.

        Returns:
            int: Offset (>= 0) from the stack pointer after frame allocation.
        """
        if name in self._spill_offsets:
            return self._spill_offsets[name]

        offset = self._next_spill_offset
        self._next_spill_offset += WORD_SIZE
        self._max_spill_offset = max(self._max_spill_offset, offset + WORD_SIZE)
        self._spill_offsets[name] = offset
        entry = self.get(name)
        entry.spill_slot = offset
        return offset

    def forget_register(self, register: str) -> None:
        """Remove any reference to a register across all variables."""
        for entry in self._locations.values():
            entry.registers.discard(register)

    def variables(self) -> Dict[str, VariableLocation]:
        """Expose the internal mapping (copy) for inspection/testing."""
        return dict(self._locations)

    @property
    def spill_area_size(self) -> int:
        """Maximum number of bytes currently required for spills."""
        return self._max_spill_offset
