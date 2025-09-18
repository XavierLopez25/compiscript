"""
TAC (Three Address Code) Generation Module

This module provides infrastructure for generating Three Address Code
as an intermediate representation for the CompilScript compiler.

Main components:
- instruction: TAC instruction classes
- temp_manager: Temporary variable management with recycling
- address_manager: Memory address and activation record management
- base_generator: Base classes for TAC generation using visitor pattern
"""

from .instruction import (
    TACInstruction,
    AssignInstruction,
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
    ArrayAccessInstruction,
    PropertyAccessInstruction,
    NewInstruction,
    CommentInstruction
)

from .temp_manager import (
    TemporaryManager,
    ScopedTemporaryManager
)

from .address_manager import (
    AddressManager,
    ActivationRecord,
    MemoryLocation
)

from .base_generator import (
    TACGenerator,
    BaseTACVisitor,
    TACGenerationError
)

__all__ = [
    'TACInstruction',
    'AssignInstruction',
    'GotoInstruction',
    'ConditionalGotoInstruction',
    'LabelInstruction',
    'BeginFuncInstruction',
    'EndFuncInstruction',
    'PushParamInstruction',
    'CallInstruction',
    'PopParamsInstruction',
    'ReturnInstruction',
    'ArrayAccessInstruction',
    'PropertyAccessInstruction',
    'NewInstruction',
    'CommentInstruction',
    'TemporaryManager',
    'ScopedTemporaryManager',
    'AddressManager',
    'ActivationRecord',
    'MemoryLocation',
    'TACGenerator',
    'BaseTACVisitor',
    'TACGenerationError'
]