from typing import Dict, Optional, List, Union
from dataclasses import dataclass

@dataclass
class ActivationRecord:
    """
    Represents an activation record structure for function calls.
    Contains information about local variables, parameters, and offsets.
    """
    function_name: str
    parameters: List[str]
    local_vars: Dict[str, int]  # var_name -> offset
    temp_vars: Dict[str, int]   # temp_name -> offset
    total_size: int = 0
    return_address_offset: int = 0
    frame_pointer_offset: int = 4  # Space for saved frame pointer

@dataclass
class MemoryLocation:
    """Represents a memory location with address and offset information."""
    address: Union[str, int]
    offset: int = 0
    size: int = 4  # Default size for integers/pointers
    is_temporary: bool = False

class AddressManager:
    """
    Manages memory addresses and offsets for variables, temporaries, and activation records.
    Handles variable placement within activation records and calculates memory offsets.
    """

    def __init__(self):
        self._global_vars: Dict[str, MemoryLocation] = {}
        self._activation_records: List[ActivationRecord] = []
        self._completed_records: Dict[str, ActivationRecord] = {}  # Store completed function records
        self._label_counter = 0
        self._current_offset = 0
        self._word_size = 4  # 4 bytes per word (typical for 32-bit systems)

    def allocate_global_var(self, var_name: str, size: int = 4) -> MemoryLocation:
        """
        Allocate memory for a global variable.

        Args:
            var_name: Name of the variable
            size: Size in bytes (default 4 for int/float)

        Returns:
            MemoryLocation: Memory location information
        """
        if var_name in self._global_vars:
            return self._global_vars[var_name]

        location = MemoryLocation(
            address=f"global_{var_name}",
            offset=0,
            size=size,
            is_temporary=False
        )
        self._global_vars[var_name] = location
        return location

    def create_activation_record(self, function_name: str, parameters: List[str]) -> ActivationRecord:
        """
        Create a new activation record for a function.

        Args:
            function_name: Name of the function
            parameters: List of parameter names

        Returns:
            ActivationRecord: New activation record
        """
        record = ActivationRecord(
            function_name=function_name,
            parameters=parameters,
            local_vars={},
            temp_vars={}
        )

        # Calculate parameter offsets (parameters are above the frame pointer)
        offset = 8  # Start after return address and saved frame pointer
        for param in parameters:
            record.local_vars[param] = offset
            offset += self._word_size

        record.total_size = offset
        self._activation_records.append(record)
        return record

    def allocate_local_var(self, var_name: str, size: int = 4) -> MemoryLocation:
        """
        Allocate memory for a local variable in the current activation record.

        Args:
            var_name: Name of the variable
            size: Size in bytes

        Returns:
            MemoryLocation: Memory location information
        """
        if not self._activation_records:
            return self.allocate_global_var(var_name, size)

        current_record = self._activation_records[-1]

        if var_name in current_record.local_vars:
            offset = current_record.local_vars[var_name]
        else:
            # Allocate new local variable (negative offset from frame pointer)
            offset = -(len(current_record.local_vars) - len(current_record.parameters) + 1) * self._word_size
            current_record.local_vars[var_name] = offset
            current_record.total_size = max(current_record.total_size, abs(offset) + size)

        return MemoryLocation(
            address=f"fp{offset:+d}" if offset < 0 else f"fp+{offset}",
            offset=offset,
            size=size,
            is_temporary=False
        )

    def allocate_temp_var(self, temp_name: str, size: int = 4) -> MemoryLocation:
        """
        Allocate memory for a temporary variable.

        Args:
            temp_name: Name of the temporary variable
            size: Size in bytes

        Returns:
            MemoryLocation: Memory location information
        """
        if not self._activation_records:
            # Global temporary (shouldn't happen normally)
            location = MemoryLocation(
                address=f"global_{temp_name}",
                offset=0,
                size=size,
                is_temporary=True
            )
            self._global_vars[temp_name] = location
            return location

        current_record = self._activation_records[-1]

        if temp_name in current_record.temp_vars:
            offset = current_record.temp_vars[temp_name]
        else:
            # Allocate new temporary variable
            total_locals = len(current_record.local_vars) - len(current_record.parameters)
            temp_count = len(current_record.temp_vars)
            offset = -(total_locals + temp_count + 1) * self._word_size
            current_record.temp_vars[temp_name] = offset
            current_record.total_size = max(current_record.total_size, abs(offset) + size)

        return MemoryLocation(
            address=f"fp{offset:+d}",
            offset=offset,
            size=size,
            is_temporary=True
        )

    def get_variable_location(self, var_name: str) -> Optional[MemoryLocation]:
        """
        Get the memory location for a variable.

        Args:
            var_name: Name of the variable

        Returns:
            Optional[MemoryLocation]: Memory location or None if not found
        """
        # Check current activation record first
        if self._activation_records:
            current_record = self._activation_records[-1]

            # Check local variables
            if var_name in current_record.local_vars:
                offset = current_record.local_vars[var_name]
                return MemoryLocation(
                    address=f"fp{offset:+d}" if offset < 0 else f"fp+{offset}",
                    offset=offset,
                    size=self._word_size,
                    is_temporary=False
                )

            # Check temporary variables
            if var_name in current_record.temp_vars:
                offset = current_record.temp_vars[var_name]
                return MemoryLocation(
                    address=f"fp{offset:+d}",
                    offset=offset,
                    size=self._word_size,
                    is_temporary=True
                )

        # Check global variables
        if var_name in self._global_vars:
            return self._global_vars[var_name]

        return None

    def enter_function(self, function_name: str, parameters: List[str]) -> ActivationRecord:
        """
        Enter a new function scope by creating an activation record.

        Args:
            function_name: Name of the function
            parameters: List of parameter names

        Returns:
            ActivationRecord: New activation record
        """
        return self.create_activation_record(function_name, parameters)

    def exit_function(self) -> Optional[ActivationRecord]:
        """
        Exit the current function scope by removing its activation record.
        Stores the completed record for later retrieval.

        Returns:
            Optional[ActivationRecord]: Removed activation record or None
        """
        if self._activation_records:
            record = self._activation_records.pop()
            # Store completed record for later queries
            self._completed_records[record.function_name] = record
            return record
        return None

    def generate_label(self, prefix: str = "L") -> str:
        """
        Generate a unique label for jumps and control flow.

        Args:
            prefix: Label prefix (default "L")

        Returns:
            str: Unique label name
        """
        self._label_counter += 1
        return f"{prefix}{self._label_counter}"

    def get_current_function(self) -> Optional[str]:
        """
        Get the name of the current function.

        Returns:
            Optional[str]: Current function name or None if in global scope
        """
        if self._activation_records:
            return self._activation_records[-1].function_name
        return None

    def get_activation_record_size(self, function_name: str = None) -> int:
        """
        Get the size of an activation record.

        Args:
            function_name: Function name (uses current if None)

        Returns:
            int: Size of activation record in bytes
        """
        if function_name:
            # Check active records first
            for record in self._activation_records:
                if record.function_name == function_name:
                    return record.total_size
            # Check completed records
            if function_name in self._completed_records:
                return self._completed_records[function_name].total_size
            return 0

        if self._activation_records:
            return self._activation_records[-1].total_size
        return 0

    def reset(self) -> None:
        """Reset the address manager to initial state."""
        self._global_vars.clear()
        self._activation_records.clear()
        self._completed_records.clear()
        self._label_counter = 0
        self._current_offset = 0

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about memory usage.

        Returns:
            Dict[str, int]: Memory usage statistics
        """
        total_global_size = sum(loc.size for loc in self._global_vars.values())
        current_stack_size = self.get_activation_record_size() if self._activation_records else 0

        return {
            'global_vars_count': len(self._global_vars),
            'global_memory_size': total_global_size,
            'active_functions': len(self._activation_records),
            'current_stack_size': current_stack_size,
            'labels_generated': self._label_counter
        }