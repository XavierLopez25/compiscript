"""
Core infrastructure for translating CompilScript TAC into MIPS assembly.

This package provides the foundational building blocks required by the MIPS
backend, including instruction representations, register and address tracking,
and the base translator that orchestrates code emission.
"""

from .instruction import (
    MIPSInstruction,
    MIPSLabel,
    MIPSComment,
    MIPSDirective,
)
from .address_descriptor import AddressDescriptor, VariableLocation
from .register_descriptor import RegisterDescriptor
from .register_allocator import RegisterAllocator, RegisterAllocationError
from .translator_base import MIPSTranslatorBase
from .expression_translator import ExpressionTranslator
from .control_flow_translator import ControlFlowTranslator
from .label_manager import LabelManager, LabelResolutionError
from .loop_translator import LoopPatternDetector, LoopOptimizer, LoopInfo

__all__ = [
    "MIPSInstruction",
    "MIPSLabel",
    "MIPSComment",
    "MIPSDirective",
    "AddressDescriptor",
    "VariableLocation",
    "RegisterDescriptor",
    "RegisterAllocator",
    "RegisterAllocationError",
    "MIPSTranslatorBase",
    "ExpressionTranslator",
    "ControlFlowTranslator",
    "LabelManager",
    "LabelResolutionError",
    "LoopPatternDetector",
    "LoopOptimizer",
    "LoopInfo",
]
