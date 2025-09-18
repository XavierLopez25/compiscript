from typing import Set, Optional, Dict, List

class TemporaryManager:
    """
    Manages temporary variable allocation and recycling for TAC generation.
    Implements an algorithm for efficient temporary variable reuse.
    """

    def __init__(self):
        self._temp_counter = 0
        self._available_temps: Set[str] = set()
        self._active_temps: Set[str] = set()
        self._temp_scopes: List[Set[str]] = []

    def new_temp(self) -> str:
        """
        Allocate a new temporary variable.
        First tries to reuse available temporaries, otherwise creates new ones.

        Returns:
            str: Temporary variable name (e.g., 't1', 't2', etc.)
        """
        if self._available_temps:
            temp = self._available_temps.pop()
            self._active_temps.add(temp)
            return temp

        self._temp_counter += 1
        temp = f"t{self._temp_counter}"
        self._active_temps.add(temp)
        return temp

    def release_temp(self, temp: str) -> None:
        """
        Release a temporary variable for reuse.

        Args:
            temp: Temporary variable name to release
        """
        if temp in self._active_temps:
            self._active_temps.remove(temp)
            self._available_temps.add(temp)

    def release_temps(self, temps: List[str]) -> None:
        """
        Release multiple temporary variables at once.

        Args:
            temps: List of temporary variable names to release
        """
        for temp in temps:
            self.release_temp(temp)

    def enter_scope(self) -> None:
        """
        Enter a new scope for temporary variable management.
        Saves current state to restore later when exiting scope.
        """
        # Save current active temps for this scope
        current_scope_temps = self._active_temps.copy()
        self._temp_scopes.append(current_scope_temps)

    def exit_scope(self) -> None:
        """
        Exit current scope and release all temporaries allocated in this scope.
        Restores the previous scope's temporary state.
        """
        if not self._temp_scopes:
            return

        # Get temporaries from previous scope
        prev_scope_temps = self._temp_scopes.pop()

        # Release temporaries that were created in the current scope
        current_only_temps = self._active_temps - prev_scope_temps
        for temp in current_only_temps:
            self.release_temp(temp)

    def is_temporary(self, var_name: str) -> bool:
        """
        Check if a variable name is a temporary variable.

        Args:
            var_name: Variable name to check

        Returns:
            bool: True if the variable is a temporary
        """
        return var_name.startswith('t') and var_name[1:].isdigit()

    def get_active_temps(self) -> Set[str]:
        """
        Get all currently active temporary variables.

        Returns:
            Set[str]: Set of active temporary variable names
        """
        return self._active_temps.copy()

    def get_available_temps(self) -> Set[str]:
        """
        Get all available (recyclable) temporary variables.

        Returns:
            Set[str]: Set of available temporary variable names
        """
        return self._available_temps.copy()

    def get_temp_count(self) -> int:
        """
        Get the total number of temporary variables created so far.

        Returns:
            int: Total temporary variable count
        """
        return self._temp_counter

    def reset(self) -> None:
        """
        Reset the temporary manager to initial state.
        Useful for starting fresh between compilation units.
        """
        self._temp_counter = 0
        self._available_temps.clear()
        self._active_temps.clear()
        self._temp_scopes.clear()

    def optimize_usage(self) -> Dict[str, int]:
        """
        Provide statistics about temporary variable usage for optimization analysis.

        Returns:
            Dict[str, int]: Statistics including total created, active, available
        """
        return {
            'total_created': self._temp_counter,
            'active_count': len(self._active_temps),
            'available_count': len(self._available_temps),
            'scope_depth': len(self._temp_scopes),
            'recycling_efficiency': (
                len(self._available_temps) / max(self._temp_counter, 1) * 100
            )
        }

class ScopedTemporaryManager(TemporaryManager):
    """
    Extended temporary manager with automatic scope-based temporary management.
    Provides context manager support for automatic scope entry/exit.
    """

    def __enter__(self):
        """Context manager entry - enter new scope."""
        self.enter_scope()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - exit current scope."""
        self.exit_scope()

    def with_scope(self, func, *args, **kwargs):
        """
        Execute a function within a temporary variable scope.

        Args:
            func: Function to execute
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result of function execution
        """
        with self:
            return func(*args, **kwargs)