from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .address_descriptor import AddressDescriptor
from .register_descriptor import RegisterDescriptor

TEMP_REGISTERS: Tuple[str, ...] = tuple(f"$t{i}" for i in range(10))
SAVED_REGISTERS: Tuple[str, ...] = tuple(f"$s{i}" for i in range(8))
ARGUMENT_REGISTERS: Tuple[str, ...] = ("$a0", "$a1", "$a2", "$a3")
RETURN_REGISTERS: Tuple[str, ...] = ("$v0", "$v1")

WORD_SIZE = 4


class RegisterAllocationError(RuntimeError):
    """Raised when the allocator cannot supply a register."""


@dataclass(frozen=True)
class SpillAction:
    """
    Describes that the contents of `register` holding `variable` must be
    written back to memory before the register can be repurposed.

    When `memory_offset` is not None, the value should be stored at
    `offset($fp)`; otherwise it must be written to `offset($sp)` where `offset`
    corresponds to a spill slot reserved by the allocator.
    """

    variable: str
    register: str
    memory_offset: Optional[int] = None
    spill_offset: Optional[int] = None
    is_global: bool = False
    global_address: Optional[str] = None

    def requires_fp(self) -> bool:
        return self.memory_offset is not None and not self.is_global

    def requires_global_label(self) -> bool:
        return self.is_global


@dataclass(frozen=True)
class LoadAction:
    """
    Describes the need to load `variable` into `register`.
    Mirrors the structure of `SpillAction` to guide the translator in emitting
    the appropriate load instruction.
    """

    variable: str
    register: str
    memory_offset: Optional[int] = None
    spill_offset: Optional[int] = None
    is_global: bool = False
    global_address: Optional[str] = None

    def requires_fp(self) -> bool:
        return self.memory_offset is not None and not self.is_global

    def requires_global_label(self) -> bool:
        return self.is_global


RegisterAction = Tuple[str, SpillAction | LoadAction]


class RegisterAllocator:
    """
    Implements a simple register allocation strategy for the MIPS backend.

    The allocator supports the classic getReg behaviour:
      1. Reuse an existing register if the variable is already loaded.
      2. Prefer free temporary registers.
      3. Recycle registers whose contents are dead.
      4. Spill using an LRU heuristic when no better option exists.

    The allocator does not emit instructions directly.  Instead it returns
    structured actions describing the required loads and stores so callers can
    translate them into concrete MIPS instructions while having full control
    over comments, ordering, and additional bookkeeping.
    """

    def __init__(
        self,
        address_descriptor: Optional[AddressDescriptor] = None,
        allocatable_registers: Optional[Sequence[str]] = None,
    ) -> None:
        self.address_descriptor = address_descriptor or AddressDescriptor()

        if allocatable_registers is None:
            allocatable_registers = TEMP_REGISTERS + SAVED_REGISTERS

        self.register_descriptor = RegisterDescriptor(allocatable_registers)
        self._allocatable_registers: Tuple[str, ...] = tuple(allocatable_registers)
        self._live_variables: Set[str] = set()
        self._next_use: Dict[str, Optional[int]] = {}

    def reset(self) -> None:
        self.address_descriptor.reset()
        self.register_descriptor = RegisterDescriptor(self._allocatable_registers)
        self._live_variables.clear()
        self._next_use.clear()

    def force_stack_location(self, name: str, offset: int) -> None:
        """
        Force a variable to be at a specific stack location.
        Used for function parameters that must be at known offsets.

        Args:
            name: Variable name
            offset: Stack offset from $sp
        """
        self.address_descriptor.force_spill_slot(name, offset)

    def force_register_location(self, name: str, register: str) -> None:
        """
        Force a variable to be in a specific register.
        Used for leaf function parameters that stay in $a0-$a3.

        Args:
            name: Variable name
            register: Register name (e.g., "$a0")
        """
        # Mark the variable as being in this register
        self.address_descriptor.bind_register(name, register)

        # Only update register descriptor if this is an allocatable register
        # $a0-$a3 are not allocatable (they're argument registers)
        if self.register_descriptor.is_allocatable(register):
            self.register_descriptor.associate(register, name, dirty=False)
            # Mark the register as occupied
            if register in self.available_registers:
                self.available_registers.remove(register)

    def set_liveness_context(
        self,
        live_variables: Optional[Iterable[str]] = None,
        next_use: Optional[Dict[str, Optional[int]]] = None,
    ) -> None:
        """
        Provide liveness information for the upcoming allocation.

        Args:
            live_variables: Variables that remain live after the current TAC
                instruction.  Used to prioritise spilling dead values.
            next_use: Mapping variable -> next instruction index where used.
                Lower numbers are considered "sooner" and will be preferred
                when selecting spill victims.
        """
        self._live_variables = set(live_variables or [])
        self._next_use = dict(next_use or {})

    def get_register(
        self,
        variable: str,
        *,
        is_write: bool = False,
        preferred_registers: Optional[Sequence[str]] = None,
        forbidden_registers: Optional[Iterable[str]] = None,
    ) -> Tuple[str, List[SpillAction], List[LoadAction]]:
        """
        Obtain a register that can hold `variable`.

        Returns:
            Tuple of (register name, spills to perform, loads to perform).
        """
        forbidden = set(forbidden_registers or [])
        if variable is None:
            raise RegisterAllocationError("Cannot allocate register for None variable.")

        existing_register = self.register_descriptor.find_register_with(variable)
        if existing_register and existing_register not in forbidden:
            # Variable already resides in a register.
            # However, if the variable has been spilled to memory and the register
            # is not marked as dirty (meaning the value might be stale), we need to
            # verify that the register truly contains the current value.
            entry = self.address_descriptor.get(variable)
            state = self.register_descriptor.state(existing_register)

            # Check if register value is trustworthy:
            # - If variable is dirty in the register, the register has the latest value
            # - If variable is NOT in memory (no spill), register is the only copy
            # - Otherwise, we need to reload from memory to be safe
            is_register_trustworthy = (
                variable in state.dirty or  # Register has been written to
                not entry.is_in_memory()     # No memory copy exists
            )

            if is_register_trustworthy:
                # Register value is valid, use it directly
                self.register_descriptor.mark_used(existing_register)
                if is_write:
                    self.register_descriptor.mark_dirty(existing_register, variable)
                    self.address_descriptor.mark_dirty(variable)
                return existing_register, [], []

            # Register value is stale, we need to reload from memory
            # Clear the stale association and fall through to acquire a fresh register
            self.register_descriptor.dissociate(existing_register, variable)
            self.address_descriptor.unbind_register(variable, existing_register)

        candidate_registers = self._candidate_registers(preferred_registers, forbidden)
        register, spills = self._acquire_register(candidate_registers)

        for spill in spills:
            # Forget spilled variables from descriptors.
            self.address_descriptor.unbind_register(spill.variable, spill.register)
            self.address_descriptor.mark_clean(spill.variable)
            self.register_descriptor.dissociate(spill.register, spill.variable)

        # Associate the newly selected register with the requested variable.
        self.register_descriptor.dissociate(register)
        self.register_descriptor.associate(register, variable, dirty=is_write)
        self.address_descriptor.bind_register(variable, register)
        if is_write:
            self.address_descriptor.mark_dirty(variable)

        loads: List[LoadAction] = []
        entry = self.address_descriptor.get(variable)
        if not is_write:
            # When reading the variable we must ensure it is loaded.
            load_action = self._build_load_action(variable, register, entry)
            if load_action:
                loads.append(load_action)
        else:
            # For pure writes, ensure we have a spill slot in case we need it later.
            if entry.memory is None and entry.spill_slot is None:
                entry.spill_slot = self.address_descriptor.ensure_spill_slot(variable)

        return register, spills, loads

    def release_register(self, register: str) -> None:
        """Explicitly mark a register as available (without spilling)."""
        if not self.register_descriptor.is_allocatable(register):
            return
        occupants = self.register_descriptor.variables_in(register)
        for variable in occupants:
            self.address_descriptor.unbind_register(variable, register)
        self.register_descriptor.dissociate(register)

    def spill_all(self) -> List[SpillAction]:
        """Spill every dirty register (typically used at block boundaries)."""
        actions: List[SpillAction] = []
        for register in self._allocatable_registers:
            state = self.register_descriptor.state(register)
            if state.is_free():
                continue
            for variable in list(state.variables):
                spill = self._build_spill_action(variable, register)
                if spill:
                    actions.append(spill)
                self.address_descriptor.unbind_register(variable, register)
            self.register_descriptor.dissociate(register)
        return actions

    def spill_caller_saved_registers(
        self,
        preserve_registers: Optional[Iterable[str]] = None,
    ) -> List[SpillAction]:
        """
        Spill all variables in caller-saved registers ($t0-$t9).

        This should be called before function calls to preserve live variables
        that are in temporary registers, since MIPS calling convention allows
        callees to freely modify $t registers.

        Returns:
            List of SpillActions for variables in $t registers
        """
        actions: List[SpillAction] = []
        temp_registers = [f"$t{i}" for i in range(10)]
        preserved = set(preserve_registers or [])

        for register in temp_registers:
            if register in preserved:
                continue
            if register not in self._allocatable_registers:
                continue

            state = self.register_descriptor.state(register)
            if state.is_free():
                continue

            # Spill all variables in this temp register
            for variable in list(state.variables):
                # Skip constants and labels - they don't need preservation
                if variable.startswith("_const_") or variable.startswith("_label_"):
                    continue

                # Build spill action (will spill if dirty or ensure it's in memory)
                spill = self._build_spill_action(variable, register)
                if spill:
                    actions.append(spill)

                # After spilling, clear the register association
                # This forces a reload next time the variable is needed
                self.address_descriptor.unbind_register(variable, register)

            # Clear the register entirely
            self.register_descriptor.dissociate(register)

        return actions

    def invalidate_caller_saved_registers(
        self,
        preserve_registers: Optional[Iterable[str]] = None,
    ) -> None:
        """
        Invalidate allocator metadata for caller-saved registers.

        After a function (or runtime) call, the contents of $t registers are
        undefined.  This method detaches any variables that were believed to
        live in those registers so future uses reload from memory.

        Args:
            preserve_registers: Registers that should be left untouched. This is
                useful for registers that are immediately rewritten after the
                call (e.g., the destination of the result).
        """
        preserved = set(preserve_registers or [])
        temp_registers = [f"$t{i}" for i in range(10)]

        for register in temp_registers:
            if register in preserved:
                continue
            if register not in self._allocatable_registers:
                continue

            state = self.register_descriptor.state(register)
            if state.is_free():
                continue

            for variable in list(state.variables):
                if variable.startswith("_const_") or variable.startswith("_label_"):
                    continue

                entry = self.address_descriptor.get(variable)

                # Ensure there is always a spill slot so the value can be
                # reloaded later.  This should already be true for regular
                # variables, but we defensively allocate one if needed.
                if entry.memory is None and entry.spill_slot is None:
                    entry.spill_slot = self.address_descriptor.ensure_spill_slot(variable)

                self.address_descriptor.unbind_register(variable, register)

            if not state.pinned:
                self.register_descriptor.dissociate(register)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _candidate_registers(
        self,
        preferred_registers: Optional[Sequence[str]],
        forbidden: Set[str],
    ) -> Tuple[str, ...]:
        if preferred_registers:
            candidates = tuple(reg for reg in preferred_registers if reg not in forbidden)
            if candidates:
                return candidates

        return tuple(reg for reg in self._allocatable_registers if reg not in forbidden)

    def _acquire_register(
        self,
        candidates: Sequence[str],
    ) -> Tuple[str, List[SpillAction]]:
        """
        Select a register from the candidate set, spilling as required.
        Returns the chosen register and spill actions that must be honoured.
        """
        # Prefer empty registers.
        for register in candidates:
            if self.register_descriptor.is_allocatable(register) and self.register_descriptor.is_free(register):
                return register, []

        # Try to reuse registers whose occupants are dead.
        dead_candidate = self._find_dead_register(candidates)
        if dead_candidate:
            spills = self._build_spill_actions_for_register(dead_candidate)
            return dead_candidate, spills

        # Fall back to LRU when no dead registers exist.
        victim = self._select_spill_victim(candidates)
        if victim is None:
            raise RegisterAllocationError("No spillable registers available.")
        spills = self._build_spill_actions_for_register(victim)
        return victim, spills

    def _find_dead_register(self, candidates: Sequence[str]) -> Optional[str]:
        for register in candidates:
            state = self.register_descriptor.state(register)
            if state.pinned:
                continue
            live = any(variable in self._live_variables for variable in state.variables)
            if not live:
                return register
        return None

    def _select_spill_victim(self, candidates: Sequence[str]) -> Optional[str]:
        best_register = None
        farthest_use = -1
        for register in candidates:
            state = self.register_descriptor.state(register)
            if state.pinned:
                continue
            # Evaluate the "next use" of all variables currently in the register.
            next_use = max(
                (
                    self._next_use.get(variable, None) or -1
                    for variable in state.variables
                ),
                default=-1,
            )
            if next_use > farthest_use:
                farthest_use = next_use
                best_register = register
        if best_register is not None:
            return best_register
        return self.register_descriptor.least_recently_used(set(candidates))

    def _build_spill_actions_for_register(self, register: str) -> List[SpillAction]:
        actions: List[SpillAction] = []
        for variable in list(self.register_descriptor.variables_in(register)):
            action = self._build_spill_action(variable, register)
            if action:
                actions.append(action)
        return actions

    def _build_spill_action(self, variable: str, register: str) -> Optional[SpillAction]:
        entry = self.address_descriptor.get(variable)
        state = self.register_descriptor.state(register)
        if variable not in state.dirty:
            return None

        memory = entry.memory
        if memory:
            is_global = isinstance(memory.address, str) and memory.address.startswith("0x")
            return SpillAction(
                variable=variable,
                register=register,
                memory_offset=None if is_global else memory.offset,
                spill_offset=None,
                is_global=is_global,
                global_address=memory.address if is_global else None,
            )

        spill_offset = entry.spill_slot
        if spill_offset is None:
            spill_offset = self.address_descriptor.ensure_spill_slot(variable)
        return SpillAction(
            variable=variable,
            register=register,
            memory_offset=None,
            spill_offset=spill_offset,
            is_global=False,
        )

    def _build_load_action(self, variable: str, register: str, entry) -> Optional[LoadAction]:
        memory = entry.memory
        if memory:
            is_global = isinstance(memory.address, str) and memory.address.startswith("0x")
            return LoadAction(
                variable=variable,
                register=register,
                memory_offset=None if is_global else memory.offset,
                spill_offset=None,
                is_global=is_global,
                global_address=memory.address if is_global else None,
            )

        if entry.spill_slot is not None:
            return LoadAction(
                variable=variable,
                register=register,
                memory_offset=None,
                spill_offset=entry.spill_slot,
                is_global=False,
            )

        return None
