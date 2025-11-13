from abc import ABC, abstractmethod
from typing import Optional

class TACInstruction(ABC):
    """Base class for Three Address Code instructions."""

    @abstractmethod
    def __str__(self) -> str:
        """Return string representation of the instruction."""
        pass

class AssignInstruction(TACInstruction):
    """Assignment instruction: x = y op z, x = op y, x = y"""

    def __init__(self, target: str, operand1: Optional[str] = None,
                 operator: Optional[str] = None, operand2: Optional[str] = None):
        self.target = target
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2

    def __str__(self) -> str:
        if self.operator and self.operand2:
            # Binary operation: x = y op z
            return f"{self.target} = {self.operand1} {self.operator} {self.operand2}"
        elif self.operator:
            # Unary operation: x = op y
            return f"{self.target} = {self.operator} {self.operand1}"
        else:
            # Simple assignment: x = y
            return f"{self.target} = {self.operand1}"

class GotoInstruction(TACInstruction):
    """Unconditional jump: goto L"""

    def __init__(self, label: str):
        self.label = label

    def __str__(self) -> str:
        return f"goto {self.label}"

class ConditionalGotoInstruction(TACInstruction):
    """Conditional jump: if x goto L, if x relop y goto L"""

    def __init__(self, condition: str, label: str, operand2: Optional[str] = None,
                 operator: Optional[str] = None):
        self.condition = condition
        self.label = label
        self.operand2 = operand2
        self.operator = operator

    def __str__(self) -> str:
        if self.operator and self.operand2:
            # Relational: if x relop y goto L
            return f"if {self.condition} {self.operator} {self.operand2} goto {self.label}"
        else:
            # Simple: if x goto L
            return f"if {self.condition} goto {self.label}"

class LabelInstruction(TACInstruction):
    """Label: L:"""

    def __init__(self, label: str):
        self.label = label

    def __str__(self) -> str:
        return f"{self.label}:"

class BeginFuncInstruction(TACInstruction):
    """Function prologue: BeginFunc n"""

    def __init__(self, name: str, param_count: int, frame_size: int = 0, param_names: list = None):
        self.name = name
        self.param_count = param_count
        self.frame_size = frame_size
        self.param_names = param_names if param_names is not None else []

    def __str__(self) -> str:
        params_str = f", params=[{','.join(self.param_names)}]" if self.param_names else ""
        if self.frame_size > 0:
            return f"BeginFunc {self.name}, {self.param_count}, frame_size={self.frame_size}{params_str}"
        return f"BeginFunc {self.name}, {self.param_count}{params_str}"

class EndFuncInstruction(TACInstruction):
    """Function epilogue: EndFunc"""

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"EndFunc {self.name}"

class PushParamInstruction(TACInstruction):
    """Push parameter: PushParam x"""

    def __init__(self, param: str):
        self.param = param

    def __str__(self) -> str:
        return f"PushParam {self.param}"

class CallInstruction(TACInstruction):
    """Function call: call f, n or x = call f, n"""

    def __init__(self, function: str, param_count: int, target: Optional[str] = None):
        self.function = function
        self.param_count = param_count
        self.target = target

    def __str__(self) -> str:
        call_str = f"call {self.function}, {self.param_count}"
        if self.target:
            return f"{self.target} = {call_str}"
        return call_str

class PopParamsInstruction(TACInstruction):
    """Pop parameters: PopParams n"""

    def __init__(self, param_count: int):
        self.param_count = param_count

    def __str__(self) -> str:
        return f"PopParams {self.param_count}"

class ReturnInstruction(TACInstruction):
    """Return statement: return x or return"""

    def __init__(self, value: Optional[str] = None):
        self.value = value

    def __str__(self) -> str:
        if self.value:
            return f"return {self.value}"
        return "return"

class ArrayAccessInstruction(TACInstruction):
    """Array access: x = y[z] or x[y] = z"""

    def __init__(self, target: str, array: str, index: str, is_assignment: bool = False):
        self.target = target
        self.array = array
        self.index = index
        self.is_assignment = is_assignment

    def __str__(self) -> str:
        if self.is_assignment:
            # Array assignment: array[index] = target
            return f"{self.array}[{self.index}] = {self.target}"
        else:
            # Array access: target = array[index]
            return f"{self.target} = {self.array}[{self.index}]"

class PropertyAccessInstruction(TACInstruction):
    """Property access: x = y.prop or x.prop = y"""

    def __init__(self, target: str, object_ref: str, property_name: str, is_assignment: bool = False):
        self.target = target
        self.object_ref = object_ref
        self.property_name = property_name
        self.is_assignment = is_assignment

    def __str__(self) -> str:
        if self.is_assignment:
            # Property assignment: object.property = target
            return f"{self.object_ref}.{self.property_name} = {self.target}"
        else:
            # Property access: target = object.property
            return f"{self.target} = {self.object_ref}.{self.property_name}"

class NewInstruction(TACInstruction):
    """Object creation: x = new ClassName"""

    def __init__(self, target: str, class_name: str):
        self.target = target
        self.class_name = class_name

    def __str__(self) -> str:
        return f"{self.target} = new {self.class_name}"

class CommentInstruction(TACInstruction):
    """Comment for debugging: # comment"""

    def __init__(self, comment: str):
        self.comment = comment

    def __str__(self) -> str:
        return f"# {self.comment}"

class AllocateArrayInstruction(TACInstruction):
    """Array allocation: x = allocate_array size, elem_size"""

    def __init__(self, target: str, size: str, elem_size: int = 4):
        self.target = target
        self.size = size
        self.elem_size = elem_size

    def __str__(self) -> str:
        return f"{self.target} = allocate_array {self.size}, {self.elem_size}"