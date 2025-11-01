from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set


@dataclass
class RegisterState:
    """Tracks the variables currently associated with a register."""

    name: str
    variables: Set[str] = field(default_factory=set)
    dirty: Set[str] = field(default_factory=set)
    pinned: bool = False  # Pinned registers cannot be spilled (e.g., $sp, $fp)
    last_used: int = 0  # Logical timestamp for LRU replacement

    def is_free(self) -> bool:
        return not self.variables

    def mark_dirty(self, variable: str) -> None:
        self.dirty.add(variable)

    def mark_clean(self, variable: str) -> None:
        self.dirty.discard(variable)


class RegisterDescriptor:
    """
    Maintains the mapping of registers to the variables they hold.

    This structure mirrors the classical compiler "register descriptor" and is
    consulted by the allocator to determine reuse opportunities and spill
    victims.
    """

    def __init__(self, allocatable_registers: Iterable[str]):
        self._states: Dict[str, RegisterState] = {
            name: RegisterState(name=name) for name in allocatable_registers
        }
        self._tick = 0

    def clone(self) -> "RegisterDescriptor":
        """Create a shallow copy (useful for testing or speculative state)."""
        copy = RegisterDescriptor(self._states.keys())
        for name, state in self._states.items():
            replica = copy._states[name]
            replica.variables = set(state.variables)
            replica.dirty = set(state.dirty)
            replica.pinned = state.pinned
            replica.last_used = state.last_used
        copy._tick = self._tick
        return copy

    def tick(self) -> int:
        """Advance the logical clock and return the new value."""
        self._tick += 1
        return self._tick

    def registers(self) -> Iterable[str]:
        return self._states.keys()

    def state(self, register: str) -> RegisterState:
        return self._states[register]

    def is_allocatable(self, register: str) -> bool:
        return register in self._states

    def is_free(self, register: str) -> bool:
        return self._states[register].is_free()

    def mark_used(self, register: str) -> None:
        self._states[register].last_used = self.tick()

    def pin(self, register: str) -> None:
        self._states[register].pinned = True

    def unpin(self, register: str) -> None:
        self._states[register].pinned = False

    def associate(self, register: str, variable: str, dirty: bool = False) -> None:
        state = self._states[register]
        state.variables.add(variable)
        if dirty:
            state.mark_dirty(variable)
        self.mark_used(register)

    def dissociate(self, register: str, variable: Optional[str] = None) -> None:
        state = self._states[register]
        if variable is None:
            state.variables.clear()
            state.dirty.clear()
        else:
            state.variables.discard(variable)
            state.dirty.discard(variable)
        self.mark_used(register)

    def mark_dirty(self, register: str, variable: str) -> None:
        self._states[register].mark_dirty(variable)

    def mark_clean(self, register: str, variable: str) -> None:
        self._states[register].mark_clean(variable)

    def variables_in(self, register: str) -> Set[str]:
        return set(self._states[register].variables)

    def contains(self, register: str, variable: str) -> bool:
        return variable in self._states[register].variables

    def find_register_with(self, variable: str) -> Optional[str]:
        for state in self._states.values():
            if variable in state.variables:
                return state.name
        return None

    def dirty_variables(self, register: str) -> Set[str]:
        return set(self._states[register].dirty)

    def least_recently_used(self, exclude: Optional[Set[str]] = None) -> Optional[str]:
        exclude = exclude or set()
        lru_reg = None
        lru_value = float("inf")
        for name, state in self._states.items():
            if name in exclude:
                continue
            if state.pinned:
                continue
            if state.last_used < lru_value:
                lru_value = state.last_used
                lru_reg = name
        return lru_reg
