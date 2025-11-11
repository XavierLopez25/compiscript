"""
Class and Object Translation for MIPS

This module handles translation of class-related operations:
- Object instantiation (new ClassName)
- Property access (obj.property)
- Method calls (obj.method(...))

Object Memory Model:
Objects are allocated on the heap with the following structure:
┌─────────────────────────┐
│ Class ID / VTable ptr   │  ← 4 bytes
├─────────────────────────┤
│ Property 1              │  ← 4 bytes each
│ Property 2              │
│ ...                      │
│ Property N              │
└─────────────────────────┘

For simplicity, we use a flat object model without virtual dispatch.
Method calls are translated to regular function calls with 'this' as first parameter.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from tac.instruction import (
    NewInstruction,
    PropertyAccessInstruction,
)

from .translator_base import MIPSTranslatorBase
from .instruction import MIPSInstruction, MIPSComment
from .calling_convention import CallingConvention


@dataclass
class ClassLayout:
    """
    Describes the memory layout of a class.

    Attributes:
        class_name: Name of the class
        properties: List of property names in order
        property_offsets: Map from property name to byte offset
        total_size: Total size of object in bytes
    """

    class_name: str
    properties: List[str]
    property_offsets: Dict[str, int]
    total_size: int

    def get_property_offset(self, prop_name: str) -> Optional[int]:
        """Get the byte offset of a property."""
        return self.property_offsets.get(prop_name)


class ClassTranslator(MIPSTranslatorBase):
    """
    Translates class-related TAC instructions to MIPS.

    Handles:
    - Object allocation (new)
    - Property access and assignment
    - Method calls
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.class_layouts: Dict[str, ClassLayout] = {}
        self.heap_pointer_offset = 0  # Track heap allocations

    def register_class(self, class_name: str, properties: List[str]) -> None:
        """
        Register a class layout.

        Args:
            class_name: Name of the class
            properties: List of property names
        """
        # Calculate offsets
        # Reserve 4 bytes for class metadata (vtable pointer or class ID)
        property_offsets = {}
        current_offset = 4  # Start after metadata

        for prop in properties:
            property_offsets[prop] = current_offset
            current_offset += 4  # Assume all properties are 4 bytes (int/pointer)

        total_size = current_offset

        layout = ClassLayout(
            class_name=class_name,
            properties=properties,
            property_offsets=property_offsets,
            total_size=total_size,
        )

        self.class_layouts[class_name] = layout

    def translate_new_object(self, instr: NewInstruction) -> None:
        """
        Translate 'new ClassName' to MIPS heap allocation.

        TAC: target = new ClassName

        MIPS:
        1. Get object size
        2. Allocate on heap (using syscall or global heap pointer)
        3. Initialize object (optional)
        4. Store pointer in target

        Args:
            instr: NewInstruction
        """
        self.emit_comment(f"Allocate object: {instr.class_name}")

        layout = self.class_layouts.get(instr.class_name)
        if not layout:
            # Unknown class - use default size
            object_size = 8  # Metadata + one word
            self.emit_comment(f"Warning: Unknown class {instr.class_name}, using size {object_size}")
        else:
            object_size = layout.total_size

        # Allocate memory using syscall (sbrk)
        # syscall 9: sbrk (allocate heap memory)
        # $a0 = number of bytes to allocate
        # Returns: $v0 = address of allocated memory
        self.emit_text(
            MIPSInstruction("li", ("$a0", str(object_size)), comment="object size")
        )
        self.emit_text(
            MIPSInstruction("li", ("$v0", "9"), comment="syscall: sbrk")
        )
        self.emit_text(MIPSInstruction("syscall", (), comment="allocate"))

        # $v0 now contains pointer to object
        # Store class ID at offset 0 (optional - for type checking)
        # For simplicity, we'll skip this or use a constant

        # Store object pointer in target variable
        target = instr.target
        if target.startswith("$"):
            # Target is register
            self.emit_text(MIPSInstruction("move", (target, "$v0")))
        else:
            # Target is variable
            self.emit_text(
                MIPSInstruction("sw", ("$v0", target), comment=f"store object pointer")
            )

    def translate_property_access(self, instr: PropertyAccessInstruction) -> None:
        """
        Translate property access to MIPS.

        TAC: target = obj.property  (read)
        MIPS:
        1. Load object pointer
        2. Calculate property offset
        3. Load from object[offset]
        4. Store in target

        TAC: obj.property = value  (write)
        MIPS:
        1. Load object pointer
        2. Calculate property offset
        3. Load value
        4. Store to object[offset]

        Args:
            instr: PropertyAccessInstruction
        """
        obj_ref = instr.object_ref
        prop_name = instr.property_name
        target = instr.target

        # Get class layout
        # We need to know the class type - in a real implementation,
        # this would come from type analysis
        # For now, we'll try to infer or use a default offset
        prop_offset = 4  # Default: assume property at offset 4

        # Try to find the layout
        # This is a simplification - in reality, we'd need type information
        for layout in self.class_layouts.values():
            if prop_name in layout.properties:
                prop_offset = layout.get_property_offset(prop_name) or 4
                break

        if not instr.is_assignment:
            # Read: target = obj.property
            self.emit_comment(f"Read property: {obj_ref}.{prop_name}")

            # Load object pointer into $t0
            if obj_ref.startswith("$"):
                obj_ptr_reg = obj_ref
            else:
                self.emit_text(MIPSInstruction("lw", ("$t0", obj_ref), comment="load object ptr"))
                obj_ptr_reg = "$t0"

            # Load property from object[offset]
            self.emit_text(
                MIPSInstruction(
                    "lw",
                    ("$t1", f"{prop_offset}({obj_ptr_reg})"),
                    comment=f"load {prop_name}",
                )
            )

            # Store in target
            if target.startswith("$"):
                if target != "$t1":
                    self.emit_text(MIPSInstruction("move", (target, "$t1")))
            else:
                self.emit_text(MIPSInstruction("sw", ("$t1", target), comment=f"store {prop_name}"))

        else:
            # Write: obj.property = target
            self.emit_comment(f"Write property: {obj_ref}.{prop_name} = {target}")

            # Load object pointer into $t0
            if obj_ref.startswith("$"):
                obj_ptr_reg = obj_ref
            else:
                self.emit_text(MIPSInstruction("lw", ("$t0", obj_ref), comment="load object ptr"))
                obj_ptr_reg = "$t0"

            # Load value into $t1
            if target.startswith("$"):
                value_reg = target
            elif target.isdigit() or (target.startswith("-") and target[1:].isdigit()):
                self.emit_text(MIPSInstruction("li", ("$t1", target)))
                value_reg = "$t1"
            else:
                self.emit_text(MIPSInstruction("lw", ("$t1", target), comment="load value"))
                value_reg = "$t1"

            # Store to object[offset]
            self.emit_text(
                MIPSInstruction(
                    "sw",
                    (value_reg, f"{prop_offset}({obj_ptr_reg})"),
                    comment=f"store {prop_name}",
                )
            )

    def translate_method_call(
        self,
        obj_ref: str,
        method_name: str,
        params: List[str],
        return_target: Optional[str] = None,
    ) -> None:
        """
        Translate method call to MIPS.

        Methods are translated as regular functions with 'this' as first parameter.

        TAC pattern:
        PushParam obj_ref    # 'this'
        PushParam param1
        PushParam param2
        result = call ClassName_method, 3

        Args:
            obj_ref: Reference to the object
            method_name: Name of the method
            params: Method parameters (excluding 'this')
            return_target: Where to store return value
        """
        self.emit_comment(f"Method call: {obj_ref}.{method_name}")

        # In CompilScript, methods are typically called as regular functions
        # with a mangled name like "ClassName_methodName"
        # The 'this' pointer is passed as the first argument

        # This is typically handled at the TAC generation level,
        # so we just need to ensure proper parameter passing

        # This method is mainly a placeholder for future enhancements
        # The actual work is done by the function_translator when it sees
        # the PushParam and call instructions
        pass

    def get_class_layout(self, class_name: str) -> Optional[ClassLayout]:
        """Get the layout for a class."""
        return self.class_layouts.get(class_name)
