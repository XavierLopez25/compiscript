from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Union

from tac.address_manager import AddressManager, MemoryLocation

from .address_descriptor import AddressDescriptor
from .instruction import MIPSComment, MIPSDirective, MIPSInstruction, MIPSLabel
from .register_allocator import (
    LoadAction,
    RegisterAllocator,
    RegisterAllocationError,
    SpillAction,
)

MIPSNode = Union[MIPSInstruction, MIPSLabel, MIPSDirective, MIPSComment]


class MIPSTranslatorBase:
    """
    Shared infrastructure for concrete TAC -> MIPS translators.

    The class keeps track of emitted instructions, orchestrates register
    allocation, and exposes helpers for turning the allocator actions into
    concrete MIPS instructions.
    """

    def __init__(
        self,
        *,
        address_manager: Optional[AddressManager] = None,
        allocatable_registers: Optional[Sequence[str]] = None,
    ) -> None:
        self.address_manager = address_manager
        self.address_descriptor = AddressDescriptor()
        self.register_allocator = RegisterAllocator(
            self.address_descriptor, allocatable_registers
        )

        self.text_section: List[MIPSNode] = []
        self.data_section: List[MIPSNode] = []

    # ------------------------------------------------------------------ #
    # Instruction emission helpers
    # ------------------------------------------------------------------ #

    def emit_text(self, node: MIPSNode) -> None:
        self.text_section.append(node)

    def emit_text_many(self, nodes: Iterable[MIPSNode]) -> None:
        for node in nodes:
            self.emit_text(node)

    def emit_data(self, node: MIPSNode) -> None:
        self.data_section.append(node)

    def emit_label(self, name: str) -> None:
        self.emit_text(MIPSLabel(name))

    def emit_comment(self, comment: str) -> None:
        self.emit_text(MIPSComment(comment))

    def emit_directive(self, directive: str, *operands: str, comment: Optional[str] = None) -> None:
        self.emit_data(MIPSDirective(directive, tuple(operands), comment))

    def clear(self) -> None:
        self.text_section.clear()
        self.data_section.clear()
        self.register_allocator.reset()

    # ------------------------------------------------------------------ #
    # Register allocation façade
    # ------------------------------------------------------------------ #

    def set_liveness(self, live_variables, next_use) -> None:
        self.register_allocator.set_liveness_context(live_variables, next_use)

    def acquire_register(
        self,
        variable: str,
        *,
        is_write: bool = False,
        preferred_registers: Optional[Sequence[str]] = None,
        forbidden_registers: Optional[Iterable[str]] = None,
    ) -> Tuple[str, List[SpillAction], List[LoadAction]]:
        return self.register_allocator.get_register(
            variable,
            is_write=is_write,
            preferred_registers=preferred_registers,
            forbidden_registers=forbidden_registers,
        )

    def release_register(self, register: str) -> None:
        self.register_allocator.release_register(register)

    def spill_everything(self) -> List[SpillAction]:
        return self.register_allocator.spill_all()

    # ------------------------------------------------------------------ #
    # Materialising allocator actions
    # ------------------------------------------------------------------ #

    def materialise_spills(self, actions: Iterable[SpillAction]) -> None:
        for action in actions:
            self.emit_text_many(self._spill_to_instructions(action))

    def materialise_loads(self, actions: Iterable[LoadAction]) -> None:
        for action in actions:
            self.emit_text_many(self._load_to_instructions(action))

    # ------------------------------------------------------------------ #
    # Translation helpers
    # ------------------------------------------------------------------ #

    @property
    def required_spill_space(self) -> int:
        """Return the number of bytes required in the stack frame for spills."""
        return self.address_descriptor.spill_area_size

    def bind_memory_location(self, name: str, location: MemoryLocation) -> None:
        self.address_descriptor.bind_memory(name, location)

    def program_as_string(self) -> str:
        """Render the generated program as a string (data + text)."""
        data = "\n".join(str(node) for node in self.data_section)
        text = "\n".join(str(node) for node in self.text_section)
        sections = []
        if data:
            sections.append(".data\n" + data)
        if text:
            sections.append(".text\n" + text)
        return "\n\n".join(sections)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _spill_to_instructions(self, action: SpillAction) -> List[MIPSInstruction]:
        if action.is_global:
            return self._spill_global(action)

        if action.memory_offset is not None:
            offset = action.memory_offset
            return [
                MIPSInstruction(
                    "sw",
                    (action.register, f"{offset}($fp)"),
                    comment=f"spill {action.variable}",
                )
            ]

        if action.spill_offset is not None:
            offset = action.spill_offset
            return [
                MIPSInstruction(
                    "sw",
                    (action.register, f"{offset}($sp)"),
                    comment=f"spill {action.variable}",
                )
            ]

        raise RegisterAllocationError(
            f"Unsupported spill action for variable {action.variable}"
        )

    def _load_to_instructions(self, action: LoadAction) -> List[MIPSInstruction]:
        if action.is_global:
            return self._load_global(action)

        if action.memory_offset is not None:
            offset = action.memory_offset
            return [
                MIPSInstruction(
                    "lw",
                    (action.register, f"{offset}($fp)"),
                    comment=f"load {action.variable}",
                )
            ]

        if action.spill_offset is not None:
            offset = action.spill_offset
            return [
                MIPSInstruction(
                    "lw",
                    (action.register, f"{offset}($sp)"),
                    comment=f"reload {action.variable}",
                )
            ]

        raise RegisterAllocationError(
            f"Unsupported load action for variable {action.variable}"
        )

    def _spill_global(self, action: SpillAction) -> List[MIPSInstruction]:
        if not action.global_address:
            raise RegisterAllocationError(
                f"Missing global address for variable {action.variable}"
            )
        addr = int(action.global_address, 16)
        upper = (addr >> 16) & 0xFFFF
        lower = addr & 0xFFFF
        return [
            MIPSInstruction("lui", ("$at", str(upper)), comment="spill global addr"),
            MIPSInstruction("ori", ("$at", "$at", str(lower))),
            MIPSInstruction("sw", (action.register, "0($at)"), comment=f"spill {action.variable}"),
        ]

    def _load_global(self, action: LoadAction) -> List[MIPSInstruction]:
        if not action.global_address:
            raise RegisterAllocationError(
                f"Missing global address for variable {action.variable}"
            )
        addr = int(action.global_address, 16)
        upper = (addr >> 16) & 0xFFFF
        lower = addr & 0xFFFF
        return [
            MIPSInstruction("lui", ("$at", str(upper)), comment="load global addr"),
            MIPSInstruction("ori", ("$at", "$at", str(lower))),
            MIPSInstruction("lw", (action.register, "0($at)"), comment=f"load {action.variable}"),
        ]
